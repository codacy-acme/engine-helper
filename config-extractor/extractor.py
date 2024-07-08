import requests
import yaml
import json
import os
import argparse
import time
from typing import List, Dict, Optional
from collections import Counter
from tqdm import tqdm

# Codacy API configuration
CODACY_API_TOKEN = os.environ.get("CODACY_API_TOKEN")
CODACY_API_BASE_URL = "https://api.codacy.com/api/v3"
PROVIDER = "gh"  # Assuming GitHub, change if different

# Semgrep UUID
SEMGREP_UUID = "6792c561-236d-41b7-ba5e-9d6bee0d548b"

def get_codacy_headers() -> Dict[str, str]:
    return {
        "api-token": CODACY_API_TOKEN,
        "Accept": "application/json"
    }

def spinner(message):
    """Display a spinner while a task is in progress."""
    symbols = ['|', '/', '-', '\\']
    i = 0
    while True:
        i = (i + 1) % len(symbols)
        yield f"\r{message} {symbols[i]}"

def get_coding_standards(organization: str) -> List[Dict]:
    spin = spinner("Fetching coding standards")
    url = f"{CODACY_API_BASE_URL}/organizations/{PROVIDER}/{organization}/coding-standards"
    response = requests.get(url, headers=get_codacy_headers())
    response.raise_for_status()
    coding_standards = response.json()['data']
    print("\rFetched coding standards  ")
    return coding_standards

def select_coding_standard(coding_standards: List[Dict]) -> Dict:
    print("\nAvailable coding standards:")
    for i, standard in enumerate(coding_standards, 1):
        print(f"{i}. {standard['name']}")
    
    while True:
        try:
            selection = int(input("\nEnter the number of the coding standard you want to use: "))
            if 1 <= selection <= len(coding_standards):
                return coding_standards[selection - 1]
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a valid number.")

def get_tools_for_coding_standard(organization: str, coding_standard_id: str) -> List[Dict]:
    spin = spinner("Fetching tools for coding standard")
    url = f"{CODACY_API_BASE_URL}/organizations/{PROVIDER}/{organization}/coding-standards/{coding_standard_id}/tools"
    response = requests.get(url, headers=get_codacy_headers())
    response.raise_for_status()
    tools = response.json()["data"]
    print("\rFetched tools for coding standard  ")
    return tools

def get_tool_by_uuid(tools: List[Dict], tool_uuid: str) -> Optional[Dict]:
    for tool in tools:
        if tool.get('uuid') == tool_uuid:
            return tool
    return None

def get_code_patterns_for_tool(organization: str, coding_standard_id: str, tool_uuid: str) -> List[Dict]:
    patterns = []
    cursor = None
    pbar = tqdm(desc="Fetching patterns", unit=" pages")
    
    while True:
        url = f"{CODACY_API_BASE_URL}/organizations/{PROVIDER}/{organization}/coding-standards/{coding_standard_id}/tools/{tool_uuid}/patterns?limit=1000"
        if cursor:
            url += f"&cursor={cursor}"
        
        response = requests.get(url, headers=get_codacy_headers())
        response.raise_for_status()
        data = response.json()
        patterns.extend(data["data"])
        
        pbar.update(1)
        
        cursor = data.get("pagination", {}).get("cursor")
        if not cursor:
            break
    
    pbar.close()
    return patterns

def filter_enabled_patterns(patterns: List[Dict]) -> List[Dict]:
    return [pattern for pattern in patterns if pattern.get("enabled", False)]

def get_available_languages(patterns: List[Dict]) -> List[str]:
    languages = set()
    for pattern in tqdm(patterns, desc="Processing patterns", unit=" patterns"):
        pattern_languages = pattern.get("patternDefinition", {}).get("languages", [])
        languages.update(lang.lower() for lang in pattern_languages)
    return sorted(list(languages))

def get_user_selected_languages(available_languages: List[str]) -> List[str]:
    print("\nAvailable languages:")
    for i, lang in enumerate(available_languages, 1):
        print(f"{i}. {lang.capitalize()}")
    
    selected_indices = input("\nEnter the numbers of the languages you want to include (comma-separated): ")
    selected_indices = [int(idx.strip()) for idx in selected_indices.split(',') if idx.strip().isdigit()]
    
    return [available_languages[idx - 1] for idx in selected_indices if 1 <= idx <= len(available_languages)]

def create_semgrep_config(patterns: List[Dict], selected_languages: List[str]) -> Dict:
    rules = []
    language_rule_count = Counter()

    for pattern in tqdm(patterns, desc="Creating Semgrep config", unit=" patterns"):
        pattern_def = pattern.get("patternDefinition", {})
        pattern_languages = set(lang.lower() for lang in pattern_def.get("languages", []))
        
        if not pattern_languages.intersection(selected_languages):
            continue
        
        rule = {
            "id": pattern_def.get("id", "unknown_id"),
            "message": f"{pattern_def.get('title', '')}\n{pattern_def.get('description', '')}",
            "severity": pattern_def.get("level", "").lower(),
            "metadata": {
                "category": pattern_def.get("category", ""),
                "subcategory": pattern_def.get("subCategory", ""),
                "explanation": pattern_def.get("explanation", ""),
            },
            "languages": list(pattern_languages.intersection(selected_languages)),
        }
        
        parameters = pattern_def.get("parameters", [])
        if parameters:
            rule["parameters"] = parameters
        
        rules.append(rule)
        
        for lang in rule["languages"]:
            language_rule_count[lang] += 1
    
    return {"rules": rules}, language_rule_count

def save_semgrep_config(config: Dict, filename: str = "semgrep_config.yaml"):
    with open(filename, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

def main():
    parser = argparse.ArgumentParser(description="Generate Semgrep configuration from Codacy API")
    parser.add_argument("--organization", help="Specify the Codacy organization")
    parser.add_argument("--tool", help="Specify a different tool UUID (default is Semgrep)", default=SEMGREP_UUID)
    args = parser.parse_args()

    if not CODACY_API_TOKEN:
        raise ValueError("CODACY_API_TOKEN environment variable is not set")

    try:
        # 1. Get organization
        if args.organization:
            selected_organization = args.organization
        else:
            selected_organization = input("Enter the Codacy organization name: ")
        print(f"\nUsing organization: {selected_organization}")

        # 2. Get and select coding standards
        coding_standards = get_coding_standards(selected_organization)
        if not coding_standards:
            raise Exception(f'No Coding Standards for org {selected_organization}')
        
        selected_standard = select_coding_standard(coding_standards)
        coding_standard_id = selected_standard["id"]
        print(f"\nSelected coding standard: {selected_standard['name']} (ID: {coding_standard_id})")

        # 3. Get tools for the coding standard
        tools = get_tools_for_coding_standard(selected_organization, coding_standard_id)
        print(f"Found {len(tools)} tools for the coding standard")

        # 4. Select the tool (Semgrep by default or user-specified)
        selected_tool = get_tool_by_uuid(tools, args.tool)
        if not selected_tool:
            print(f"Tool with UUID '{args.tool}' not found. Available tools:")
            for tool in tools:
                print(f"- UUID: {tool.get('uuid', 'Unknown UUID')}")
            return

        print(f"\nSelected tool UUID: {selected_tool['uuid']}")

        # 5. Get patterns for the selected tool
        tool_patterns = get_code_patterns_for_tool(selected_organization, coding_standard_id, selected_tool['uuid'])
        print(f"Found {len(tool_patterns)} patterns in total")

        # 6. Filter enabled patterns
        enabled_patterns = filter_enabled_patterns(tool_patterns)
        print(f"Found {len(enabled_patterns)} enabled patterns")

        # 7. Get available languages and let user select
        available_languages = get_available_languages(enabled_patterns)
        selected_languages = get_user_selected_languages(available_languages)
        print(f"Selected languages: {', '.join(selected_languages)}")

        # 8. Create the Semgrep YAML
        semgrep_config, language_rule_count = create_semgrep_config(enabled_patterns, selected_languages)
        save_semgrep_config(semgrep_config)
        print(f"Semgrep configuration has been saved to semgrep_config.yaml")
        
        # 9. Print rule count per language
        print("\nRules added to config file per language:")
        for lang, count in language_rule_count.items():
            print(f"{lang.capitalize()} - {count} rules")

    except requests.RequestException as e:
        print(f"Error accessing Codacy API: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()