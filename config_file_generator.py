#!/usr/bin/env python3
import argparse
import requests
import json
import re
from pprint import pprint



#TODO: only returns the first one
def getCodingStandards(baseurl, provider, organization, token):
    headers = {
        'Accept': 'application/json',
        'api-token': token
    }
    url = f'{baseurl}/api/v3/organizations/{provider}/{organization}/coding-standards'
    r = requests.get(url, headers=headers)
    codingStandards = json.loads(r.text)
    if len(codingStandards['data']) == 0:
        raise Exception(f'No Coding Standards for org {organization}')
    return codingStandards['data'][0]

def getCodePatternsForTool(baseurl, provider, organization,codingStandardId, toolUuid, token):
    headers = {
        'Accept': 'application/json',
        'api-token': token
    }
    url = f'{baseurl}/api/v3/organizations/{provider}/{organization}/coding-standards/{codingStandardId}/tools/{toolUuid}/patterns?limit=1000'
    r = requests.get(url, headers=headers)
    patterns = json.loads(r.text)["data"]
    return patterns

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
    f = open("ruleset.xml", "a")
    f.write(document)
    f.close()


def main():
    print('Welcome to Codacy Config File Generator - A temporary solution')
    print('!!!!!! CURRENTLY ONLY WORKS FOR PMD !!!!!!')
    parser = argparse.ArgumentParser(description='Codacy Engine Helper')
    parser.add_argument('--token', dest='token', default=None,
                        help='the api-token to be used on the REST API')
    parser.add_argument('--provider', dest='provider',
                        default=None, help='git provider')
    parser.add_argument('--organization', dest='organization',
                        default=None, help='organization id')
    parser.add_argument('--tooluuid', dest='toolUuid',
                        default=None, help='Tool Uuid')
    parser.add_argument('--baseurl', dest='baseurl', default='https://app.codacy.com',
                        help='codacy server address (ignore if cloud)')
    args = parser.parse_args()
    cs = getCodingStandards(args.baseurl, args.provider, args.organization, args.token)
    patterns = getCodePatternsForTool(args.baseurl, args.provider, args.organization, cs["id"], args.toolUuid, args.token)

    #TODO: decide what's the tool, currently only pmd
    generateFileForPMD(patterns)
main()