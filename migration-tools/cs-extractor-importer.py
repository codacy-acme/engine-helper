import requests
import json
import argparse
import os
import traceback
import time

# Codacy API endpoints
SELF_HOSTED_API_URL = os.environ.get("SELF_HOSTED_API_URL", "https://codacy.mycompany.com/api/v3")
CLOUD_API_URL = "https://app.codacy.com/api/v3"

# API Tokens
SELF_HOSTED_API_TOKEN = os.environ.get("SELF_HOSTED_API_TOKEN")
CLOUD_API_TOKEN = os.environ.get("CLOUD_API_TOKEN")

def make_api_request(url, method="GET", headers=None, data=None, params=None):
    if headers is None:
        headers = {}
    headers["Accept"] = "application/json"
    headers["Content-Type"] = "application/json"
    headers["api-token"] = CLOUD_API_TOKEN if url.startswith(CLOUD_API_URL) else SELF_HOSTED_API_TOKEN

    try:
        response = requests.request(method, url, headers=headers, json=data, params=params)
        response.raise_for_status()
        
        if response.status_code == 204:  # No Content
            return True
        elif response.text:
            return response.json()
        else:
            return None
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred while making the request: {req_err}")
        return None

def get_self_hosted_tools():
    url = f"{SELF_HOSTED_API_URL}/tools"
    tools = make_api_request(url)
    if not tools or not tools.get("data"):
        print("Failed to fetch tools from self-hosted Codacy")
        return {}
    return {tool["uuid"]: tool["name"] for tool in tools["data"]}

def get_cloud_tools():
    url = f"{CLOUD_API_URL}/tools"
    tools = make_api_request(url)
    if not tools or not tools.get("data"):
        print("Failed to fetch tools from Codacy Cloud")
        return {}
    return {tool["name"]: tool["uuid"] for tool in tools["data"]}

def map_sh_to_cloud_tool(sh_uuid, sh_tools, cloud_tools):
    sh_name = sh_tools.get(sh_uuid)
    if not sh_name:
        return None, None

    # Handle special cases and deprecated tools
    if sh_name == "JSHint":
        sh_name = "JSHint (deprecated)"
    elif sh_name == "Pylint (Python 3)":
        sh_name = "Pylint"
    elif sh_name == "Sonar C#":
        sh_name = "SonarC#"
    elif sh_name == "Sonar Visual Basic":
        sh_name = "SonarVB"
    elif sh_name == "ESLint (deprecated)":
        sh_name = "ESLint"

    # Find matching cloud tool
    for cloud_name, cloud_uuid in cloud_tools.items():
        if cloud_name == sh_name:
            return cloud_uuid, cloud_name

    # If no match found, try without "(deprecated)" suffix
    if "(deprecated)" in sh_name:
        non_deprecated_name = sh_name.replace(" (deprecated)", "")
        for cloud_name, cloud_uuid in cloud_tools.items():
            if cloud_name == non_deprecated_name:
                return cloud_uuid, cloud_name

    return None, None

def get_self_hosted_data(provider, remote_org_name, self_hosted_tools, cloud_tools):
    if not SELF_HOSTED_API_TOKEN:
        raise ValueError("SELF_HOSTED_API_TOKEN is not set in the environment variables")

    comprehensive_data = {}

    try:
        # Get coding standards
        url = f"{SELF_HOSTED_API_URL}/organizations/{provider}/{remote_org_name}/coding-standards"
        coding_standards = make_api_request(url)
        if not coding_standards or not coding_standards.get("data"):
            print(f"Failed to fetch coding standards. Response: {coding_standards}")
            return None
        
        coding_standard = coding_standards["data"][0]
        coding_standard_id = coding_standard["id"]
        comprehensive_data["coding_standard"] = coding_standard
        print(f"Found coding standard with ID: {coding_standard_id}")

        # Get enabled tools
        url = f"{SELF_HOSTED_API_URL}/organizations/{provider}/{remote_org_name}/coding-standards/{coding_standard_id}/tools"
        tools = make_api_request(url)
        if not tools or not tools.get("data"):
            print(f"Failed to fetch tools. Response: {tools}")
            return None
        
        enabled_tools = [tool for tool in tools["data"] if tool.get("isEnabled", False)]
        comprehensive_data["tools"] = enabled_tools
        print(f"Found {len(enabled_tools)} enabled tools")

        # Get patterns for each enabled tool
        comprehensive_data["tool_patterns"] = {}
        for tool in enabled_tools:
            sh_tool_uuid = tool.get("uuid")
            sh_tool_name = self_hosted_tools.get(sh_tool_uuid, f"Unknown Tool {sh_tool_uuid}")
            if not sh_tool_uuid:
                print(f"Skipping tool due to missing UUID: {tool}")
                continue
            
            cloud_tool_uuid, cloud_tool_name = map_sh_to_cloud_tool(sh_tool_uuid, self_hosted_tools, cloud_tools)
            if not cloud_tool_uuid:
                print(f"Warning: No matching cloud tool found for {sh_tool_name} (UUID: {sh_tool_uuid}). Skipping.")
                continue

            url = f"{SELF_HOSTED_API_URL}/organizations/{provider}/{remote_org_name}/coding-standards/{coding_standard_id}/tools/{sh_tool_uuid}/patterns"
            patterns_response = make_api_request(url)
            if patterns_response and patterns_response.get("data"):
                enabled_patterns = [
                    pattern for pattern in patterns_response["data"]
                    if pattern.get("enabled", False)
                ]
                if enabled_patterns:
                    comprehensive_data["tool_patterns"][cloud_tool_uuid] = {"name": cloud_tool_name, "patterns": enabled_patterns}
                    print(f"Found {len(enabled_patterns)} enabled patterns for tool {cloud_tool_name}")
                else:
                    print(f"No enabled patterns found for tool {cloud_tool_name}")
            else:
                print(f"Failed to fetch patterns for tool {cloud_tool_name}")

        print("Self-hosted data fetching completed.")
        return comprehensive_data

    except Exception as e:
        print(f"An error occurred while fetching self-hosted data: {str(e)}")
        traceback.print_exc()
        return None

def get_cloud_coding_standard(provider, cloud_org_name):
    url = f"{CLOUD_API_URL}/organizations/{provider}/{cloud_org_name}/coding-standards"
    standards = make_api_request(url)
    if not standards or not standards.get("data"):
        print("No coding standards found in Codacy Cloud")
        return None
    
    # Prefer the default standard, otherwise use the first one
    default_standard = next((s for s in standards["data"] if s.get("isDefault")), None)
    if default_standard:
        print(f"Using default coding standard: {default_standard['name']} (ID: {default_standard['id']})")
        return default_standard
    else:
        print(f"Using first available coding standard: {standards['data'][0]['name']} (ID: {standards['data'][0]['id']})")
        return standards["data"][0]

def create_cloud_coding_standard(provider, cloud_org_name, self_hosted_data):
    url = f"{CLOUD_API_URL}/organizations/{provider}/{cloud_org_name}/coding-standards"
    
    # Extract languages from self-hosted coding standard
    languages = self_hosted_data['coding_standard'].get('languages', [])
    if not languages:
        print("No languages found in self-hosted coding standard. Defaulting to Java.")
        languages = ["Java"]

    new_standard_data = {
        "name": f"Migrated: {self_hosted_data['coding_standard'].get('name', 'Unknown')}",
        "languages": languages
    }

    new_standard = make_api_request(url, method="POST", data=new_standard_data)
    if not new_standard or not new_standard.get("data"):
        print(f"Failed to create new coding standard. API response: {new_standard}")
        raise Exception("Failed to create new coding standard in Codacy Cloud")
    
    print(f"Created new coding standard: {new_standard['data']['name']} (ID: {new_standard['data']['id']}) with languages: {', '.join(languages)}")
    return new_standard["data"]

def disable_default_cloud_tools(provider, cloud_org_name, standard_id):
    url = f"{CLOUD_API_URL}/organizations/{provider}/{cloud_org_name}/coding-standards/{standard_id}/tools"
    tools = make_api_request(url)
    if not tools or not tools.get("data"):
        print(f"Failed to fetch tools for the new coding standard. Response: {tools}")
        return

    for tool in tools["data"]:
        if tool.get("isEnabled", False):
            tool_uuid = tool["uuid"]
            update_url = f"{url}/{tool_uuid}"
            update_data = {
                "enabled": False,
                "patterns": []
            }
            result = make_api_request(update_url, method="PATCH", data=update_data)
            if result is True or result is not None:
                print(f"Successfully disabled tool: {tool.get('name', tool_uuid)}")
            else:
                print(f"Failed to disable tool: {tool.get('name', tool_uuid)}")
        time.sleep(1)

def update_cloud_coding_standard(provider, cloud_org_name, standard_id, self_hosted_data):
    for cloud_tool_uuid, tool_data in self_hosted_data["tool_patterns"].items():
        cloud_tool_name = tool_data["name"]
        patterns = tool_data["patterns"]
        print(f"Processing tool: {cloud_tool_name}")
        
        update_data = {
            "enabled": True,
            "patterns": [
                {
                    "id": p["patternDefinition"]["id"],
                    "enabled": True,
                    "parameters": [
                        {"name": param["name"], "value": param["value"]}
                        for param in p.get("parameters", [])
                    ]
                } for p in patterns
            ]
        }

        url = f"{CLOUD_API_URL}/organizations/{provider}/{cloud_org_name}/coding-standards/{standard_id}/tools/{cloud_tool_uuid}"
        result = make_api_request(url, method="PATCH", data=update_data)
        
        if result is True or result is not None:
            print(f"Successfully updated configuration and {len(patterns)} patterns for tool {cloud_tool_name}")
        else:
            print(f"Failed to update configuration and patterns for tool {cloud_tool_name}")
        
        time.sleep(1)

def promote_coding_standard(provider, cloud_org_name, standard_id):
    url = f"{CLOUD_API_URL}/organizations/{provider}/{cloud_org_name}/coding-standards/{standard_id}/promote"
    result = make_api_request(url, method="POST")
    if result is not None:
        print(f"Successfully promoted coding standard.")
    else:
        print(f"Failed to promote coding standard with ID: {standard_id}")

def main():
    parser = argparse.ArgumentParser(description="Migrate Codacy coding standard from self-hosted to cloud.")
    parser.add_argument("-p", "--provider", required=True, help="The provider (e.g., gh for GitHub, gl for GitLab)")
    parser.add_argument("-o", "--organization", required=True, help="The remote organization name for self-hosted")
    parser.add_argument("-c", "--cloud-organization", required=True, help="The organization name in Codacy Cloud")
    args = parser.parse_args()

    try:
        print("Fetching tool information...")
        self_hosted_tools = get_self_hosted_tools()
        cloud_tools = get_cloud_tools()

        print("Fetching data from self-hosted Codacy...")
        self_hosted_data = get_self_hosted_data(args.provider, args.organization, self_hosted_tools, cloud_tools)
        if not self_hosted_data:
            raise Exception("Failed to fetch self-hosted data. Check the logs above for more details.")

        print("Fetching existing coding standard from Codacy Cloud...")
        cloud_standard = get_cloud_coding_standard(args.provider, args.cloud_organization)
        
        if not cloud_standard:
            print("No existing coding standard found. Creating a new one...")
            cloud_standard = create_cloud_coding_standard(args.provider, args.cloud_organization, self_hosted_data)
        
        print("Disabling default tools in the new coding standard...")
        disable_default_cloud_tools(args.provider, args.cloud_organization, cloud_standard["id"])

        print("Updating coding standard in Codacy Cloud...")
        update_cloud_coding_standard(args.provider, args.cloud_organization, cloud_standard["id"], self_hosted_data)
        
        print("Promoting coding standard...")
        promote_coding_standard(args.provider, args.cloud_organization, cloud_standard["id"])
        
        print(f"Migration completed successfully. Updated and promoted coding standard ID in Codacy Cloud: {cloud_standard['id']}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()