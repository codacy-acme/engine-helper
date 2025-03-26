#!/usr/bin/env python3
import argparse
import requests
import json
import yaml
import xml.etree.ElementTree as ET
from xml.dom import minidom
import sys

def get_repositories(baseurl, provider, organization, token):
    headers = {
        'Accept': 'application/json',
        'api-token': token
    }
    url = f'{baseurl}/api/v3/organizations/{provider}/{organization}/repositories'
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    repositories = r.json()
    if len(repositories['data']) == 0:
        raise Exception(f'No repositories found for org {organization}')
    return repositories['data']

def select_repository(repositories):
    print("\nAvailable repositories:")
    for i, repo in enumerate(repositories, 1):
        print(f"{i}. {repo['name']}")
    
    while True:
        try:
            choice = int(input("\nEnter the number of the repository you want to use: "))
            if 1 <= choice <= len(repositories):
                return repositories[choice - 1]
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a valid number.")

def list_tools(baseurl, token):
    headers = {
        'Accept': 'application/json',
        'api-token': token
    }
    url = f'{baseurl}/api/v3/tools'
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()

def getCodePatternsForTool(baseurl, provider, organization, repository, toolUuid, token):
    headers = {
        'Accept': 'application/json',
        'api-token': token
    }
    url = f'{baseurl}/api/v3/analysis/organizations/{provider}/{organization}/repositories/{repository}/tools/{toolUuid}/patterns'
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()

def generateFileForPMD(patterns):
    rules = []
    for p in patterns:
        if p['enabled']:
            pattern = p['patternDefinition']
            patternIdSplitted = pattern['id'].split('_')
            properties = ''
            if len(p["parameters"]) > 0:
                propertiesList = map(lambda param: f'<property name="{param["name"]}"><value>{param["value"]}</value></property>' , p["parameters"])
                properties = '''
                    <properties>
                        {propertiesList}
                    </properties>'''.format(propertiesList=''.join(list(propertiesList)))
            
            rule = f'<rule message="{pattern["description"]}" ref="{patternIdSplitted[1]}/{patternIdSplitted[2]}/{patternIdSplitted[3]}.xml/{"_".join(patternIdSplitted[slice(4,len(patternIdSplitted))]) }">{properties}</rule>'
            rules.append(rule)
    document = '''
    <?xml version="1.0"?>
    <ruleset name="Codacy Generated Rules File"
        xmlns="http://pmd.sourceforge.net/ruleset/2.0.0"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://pmd.sourceforge.net/ruleset/2.0.0 https://pmd.sourceforge.io/ruleset_2_0_0.xsd">
        <description>
        Codacy Generated Rules File
        </description>
        {rules}
    </ruleset>'''.format(rules=''.join(rules))
    with open("pmd_ruleset.xml", "w") as f:
        f.write(document)
    print("PMD configuration has been saved to pmd_ruleset.xml")

def generateFileForSemgrep(patterns):
    rules = []
    for p in patterns:
        if p['enabled']:
            pattern = p['patternDefinition']
            rule = {
                "id": f"Semgrep_codacy.{pattern['id']}",
                "pattern": pattern.get('pattern', ''),
                "message": pattern.get('description', ''),
                "severity": p.get('severity', 'WARNING').lower(),
                "languages": pattern.get('languages', []),
            }
            if p["parameters"]:
                rule["parameters"] = p["parameters"]
            rules.append(rule)
    
    config = {"rules": rules}
    with open("semgrep_config.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    print("Semgrep configuration has been saved to semgrep_config.yaml")

def generateFileForCheckstyle(patterns):
    root = ET.Element("module", name="Checker")
    tree_walker = ET.SubElement(root, "module", name="TreeWalker")

    for p in patterns:
        if p['enabled']:
            pattern = p['patternDefinition']
            module = ET.SubElement(tree_walker, "module", name=pattern['id'].replace('Checkstyle_', ''))
            ET.SubElement(module, "property", name="severity", value=p.get('severity', 'warning'))
            for param in p["parameters"]:
                ET.SubElement(module, "property", name=param["name"], value=str(param["value"]))

    xml_declaration = '<?xml version="1.0"?>'
    doctype = '<!DOCTYPE module PUBLIC "-//Checkstyle//DTD Checkstyle Configuration 1.3//EN" "https://checkstyle.org/dtds/configuration_1_3.dtd">'
    
    rough_string = ET.tostring(root, 'unicode')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="    ")
    
    # Remove the XML declaration from the pretty-printed XML
    pretty_xml_lines = pretty_xml.splitlines(True)
    pretty_xml_without_declaration = ''.join(pretty_xml_lines[1:])
    
    with open("checkstyle_config.xml", "w", encoding="utf-8") as f:
        f.write(f"{xml_declaration}{doctype}\n{pretty_xml_without_declaration}")
    
    print("Checkstyle configuration has been saved to checkstyle_config.xml")

def main():
    print('Welcome to Codacy Config File Generator')
    parser = argparse.ArgumentParser(description='Codacy Engine Helper')
    parser.add_argument('--token', dest='token', required=True,
                        help='the api-token to be used on the REST API')
    parser.add_argument('--provider', dest='provider', required=True,
                        help='git provider')
    parser.add_argument('--organization', dest='organization', required=True,
                        help='organization id')
    parser.add_argument('--baseurl', dest='baseurl', default='https://app.codacy.com',
                        help='codacy server address (ignore if cloud)')
    args = parser.parse_args()

    try:
        repositories = get_repositories(args.baseurl, args.provider, args.organization, args.token)
        selected_repo = select_repository(repositories)
        print(f"Selected repository: {selected_repo['name']}")

        tools = list_tools(args.baseurl, args.token)
        tool_uuids = {tool['name'].lower(): tool['uuid'] for tool in tools['data']}

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

    print("\nSelect an option:")
    print("1. Generate PMD Config")
    print("2. Generate Semgrep Config")
    print("3. Generate Checkstyle Config")
    print("4. Generate all config files")
    print("5. Exit")

    choice = input("Enter your choice (1-5): ")

    try:
        if choice == '1':
            patterns = getCodePatternsForTool(args.baseurl, args.provider, args.organization, selected_repo['name'], tool_uuids['pmd'], args.token)
            generateFileForPMD(patterns['data'])
        elif choice == '2':
            patterns = getCodePatternsForTool(args.baseurl, args.provider, args.organization, selected_repo['name'], tool_uuids['semgrep'], args.token)
            generateFileForSemgrep(patterns['data'])
        elif choice == '3':
            patterns = getCodePatternsForTool(args.baseurl, args.provider, args.organization, selected_repo['name'], tool_uuids['checkstyle'], args.token)
            generateFileForCheckstyle(patterns['data'])
        elif choice == '4':
            for tool, uuid in tool_uuids.items():
                if tool in ['pmd', 'semgrep', 'checkstyle']:
                    patterns = getCodePatternsForTool(args.baseurl, args.provider, args.organization, selected_repo['name'], uuid, args.token)
                    if tool == "pmd":
                        generateFileForPMD(patterns['data'])
                    elif tool == "semgrep":
                        generateFileForSemgrep(patterns['data'])
                    elif tool == "checkstyle":
                        generateFileForCheckstyle(patterns['data'])
        elif choice == '5':
            print("Exiting the program.")
            sys.exit(0)
        else:
            print("Invalid choice. Exiting the program.")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching patterns: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

    print("Config file(s) generated successfully. Exiting the program.")

if __name__ == "__main__":
    main()