import requests
import json
import os
import traceback
import time
from typing import List, Dict, Any, Optional, Tuple
from halo import Halo

# Codacy API endpoints
SELF_HOSTED_API_URL = os.environ.get("SELF_HOSTED_API_URL", "https://codacy.mycompany.com/api/v3")
CLOUD_API_URL = "https://app.codacy.com/api/v3"

# API Tokens
SELF_HOSTED_API_TOKEN = os.environ.get("SELF_HOSTED_API_TOKEN")
CLOUD_API_TOKEN = os.environ.get("CLOUD_API_TOKEN")

def spinner(text: str) -> Halo:
    """Create a spinner with the given text."""
    return Halo(text=text, spinner='dots')

def get_user_input(prompt: str, valid_options: List[str] = None) -> str:
    """Get user input with validation."""
    while True:
        value = input(prompt).strip()
        if not valid_options or value in valid_options:
            return value
        print(f"Please enter one of: {', '.join(valid_options)}")

def make_api_request(url: str, method: str = "GET", headers: Dict = None, 
                    data: Dict = None, params: Dict = None) -> Optional[Dict]:
    """Make an API request to Codacy."""
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

def get_self_hosted_tools() -> Dict[str, str]:
    """Fetch tools from self-hosted Codacy."""
    with spinner("Fetching self-hosted tools") as spin:
        url = f"{SELF_HOSTED_API_URL}/tools"
        tools = make_api_request(url)
        if not tools or not tools.get("data"):
            spin.fail("Failed to fetch tools from self-hosted Codacy")
            return {}
        spin.succeed("Successfully fetched self-hosted tools")
        return {tool["uuid"]: tool["name"] for tool in tools["data"]}

def get_cloud_tools() -> Dict[str, str]:
    """Fetch tools from Codacy Cloud."""
    with spinner("Fetching cloud tools") as spin:
        url = f"{CLOUD_API_URL}/tools"
        tools = make_api_request(url)
        if not tools or not tools.get("data"):
            spin.fail("Failed to fetch tools from Codacy Cloud")
            return {}
        spin.succeed("Successfully fetched cloud tools")
        return {tool["name"]: tool["uuid"] for tool in tools["data"]}

def map_sh_to_cloud_tool(sh_uuid: str, sh_tools: Dict[str, str], 
                        cloud_tools: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
    """Map self-hosted tool to cloud tool."""
    sh_name = sh_tools.get(sh_uuid)
    if not sh_name:
        return None, None

    # Handle special cases and deprecated tools
    tool_mappings = {
        "JSHint": "JSHint (deprecated)",
        "Pylint (Python 3)": "Pylint",
        "Sonar C#": "SonarC#",
        "Sonar Visual Basic": "SonarVB",
        "ESLint (deprecated)": "ESLint"
    }
    
    sh_name = tool_mappings.get(sh_name, sh_name)

    # Find matching cloud tool
    for cloud_name, cloud_uuid in cloud_tools.items():
        if cloud_name == sh_name:
            return cloud_uuid, cloud_name

    # Try without "(deprecated)" suffix
    if "(deprecated)" in sh_name:
        non_deprecated_name = sh_name.replace(" (deprecated)", "")
        for cloud_name, cloud_uuid in cloud_tools.items():
            if cloud_name == non_deprecated_name:
                return cloud_uuid, cloud_name

    return None, None

def get_coding_standards(organization: str, provider: str, is_self_hosted: bool = False) -> List[Dict[str, Any]]:
    """Fetch non-draft coding standards from Codacy API."""
    base_url = SELF_HOSTED_API_URL if is_self_hosted else CLOUD_API_URL
    with spinner("Fetching coding standards") as spin:
        try:
            url = f"{base_url}/organizations/{provider}/{organization}/coding-standards"
            response = make_api_request(url)
            if not response or not response.get('data'):
                spin.fail("Failed to fetch coding standards")
                return []
                
            all_standards = response['data']
            coding_standards = [standard for standard in all_standards 
                              if not standard.get('isDraft', False)]
            
            spin.succeed(f"Fetched {len(coding_standards)} active coding standards")
            return coding_standards
        except Exception as e:
            spin.fail(f"Error fetching coding standards: {str(e)}")
            return []

def display_coding_standards(standards: List[Dict[str, Any]]) -> None:
    """Display coding standards in a formatted way."""
    print("\nAvailable Coding Standards:")
    print("-" * 80)
    for idx, standard in enumerate(standards, 1):
        print(f"{idx}. Name: {standard.get('name', 'Unknown')}")
        print(f"   ID: {standard.get('id', 'Unknown')}")
        print(f"   Default: {'Yes' if standard.get('isDefault', False) else 'No'}")
        print(f"   Languages: {', '.join(standard.get('languages', []))}")
        print("-" * 80)

def select_coding_standard(standards: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Let user select a coding standard."""
    display_coding_standards(standards)
    while True:
        try:
            choice = int(get_user_input(f"Select a coding standard (1-{len(standards)}): "))
            if 1 <= choice <= len(standards):
                return standards[choice - 1]
            print(f"Please enter a number between 1 and {len(standards)}")
        except ValueError:
            print("Please enter a valid number")

def get_self_hosted_data(provider: str, remote_org_name: str, self_hosted_tools: Dict[str, str], 
                        cloud_tools: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Fetch data from self-hosted Codacy."""
    if not SELF_HOSTED_API_TOKEN:
        raise ValueError("SELF_HOSTED_API_TOKEN is not set")

    comprehensive_data = {}

    try:
        # Get coding standards
        standards = get_coding_standards(remote_org_name, provider, is_self_hosted=True)
        if not standards:
            raise Exception("No coding standards found")
        
        # Let user select the standard
        coding_standard = select_coding_standard(standards)
        comprehensive_data["coding_standard"] = coding_standard
        print(f"Using coding standard: {coding_standard.get('name', 'Unknown')}")

        # Get enabled tools
        with spinner("Fetching enabled tools") as spin:
            url = f"{SELF_HOSTED_API_URL}/organizations/{provider}/{remote_org_name}/coding-standards/{coding_standard['id']}/tools"
            tools = make_api_request(url)
            if not tools or not tools.get("data"):
                spin.fail("Failed to fetch tools")
                return None
            
            enabled_tools = [tool for tool in tools["data"] if tool.get("isEnabled", False)]
            comprehensive_data["tools"] = enabled_tools
            spin.succeed(f"Found {len(enabled_tools)} enabled tools")

        # Get patterns for each enabled tool
        comprehensive_data["tool_patterns"] = {}
        for tool in enabled_tools:
            with spinner(f"Processing tool: {tool.get('name', 'Unknown')}") as spin:
                sh_tool_uuid = tool.get("uuid")
                if not sh_tool_uuid:
                    spin.warn("Skipping tool with missing UUID")
                    continue
                
                sh_tool_name = self_hosted_tools.get(sh_tool_uuid, f"Unknown Tool {sh_tool_uuid}")
                
                cloud_tool_uuid, cloud_tool_name = map_sh_to_cloud_tool(sh_tool_uuid, 
                                                                      self_hosted_tools, 
                                                                      cloud_tools)
                if not cloud_tool_uuid:
                    spin.warn(f"No matching cloud tool found for {sh_tool_name}")
                    continue

                url = f"{SELF_HOSTED_API_URL}/organizations/{provider}/{remote_org_name}/coding-standards/{coding_standard['id']}/tools/{sh_tool_uuid}/patterns"
                patterns_response = make_api_request(url)
                
                if patterns_response and patterns_response.get("data"):
                    enabled_patterns = [p for p in patterns_response["data"] 
                                     if p.get("enabled", False)]
                    if enabled_patterns:
                        comprehensive_data["tool_patterns"][cloud_tool_uuid] = {
                            "name": cloud_tool_name,
                            "patterns": enabled_patterns
                        }
                        spin.succeed(f"Found {len(enabled_patterns)} enabled patterns")
                    else:
                        spin.info("No enabled patterns found")
                else:
                    spin.fail("Failed to fetch patterns")

        return comprehensive_data

    except Exception as e:
        print(f"An error occurred while fetching self-hosted data: {str(e)}")
        traceback.print_exc()
        return None

def get_source_cloud_data(provider: str, source_org_name: str) -> Optional[Dict[str, Any]]:
    """Fetch configuration data from source Cloud organization."""
    comprehensive_data = {}
    
    try:
        # Get coding standards
        standards = get_coding_standards(source_org_name, provider)
        if not standards:
            raise Exception("No coding standards found")
        
        # Let user select the standard
        coding_standard = select_coding_standard(standards)
        comprehensive_data["coding_standard"] = coding_standard
        print(f"Using coding standard: {coding_standard['name']}")
        
        # Get tools
        url = f"{CLOUD_API_URL}/organizations/{provider}/{source_org_name}/coding-standards/{coding_standard['id']}/tools"
        tools = make_api_request(url)
        if not tools or not tools.get("data"):
            raise Exception("Failed to fetch tools")
            
        enabled_tools = [tool for tool in tools["data"] if tool.get("isEnabled", False)]
        print(f"Found {len(enabled_tools)} enabled tools")
        
        # Get patterns for each enabled tool
        comprehensive_data["tool_patterns"] = {}
        for tool in enabled_tools:
            tool_uuid = tool["uuid"]
            all_patterns = []
            cursor = None
            
            while True:
                params = {"cursor": cursor} if cursor else None
                patterns_url = f"{url}/{tool_uuid}/patterns"
                patterns_response = make_api_request(patterns_url, params=params)
                
                if not patterns_response or not patterns_response.get("data"):
                    break
                    
                # Add patterns from this page
                new_patterns = []
                for pattern in patterns_response["data"]:
                    pattern_def = pattern.get("patternDefinition", {})
                    if pattern_def and pattern.get("enabled", False):
                        pattern_entry = {
                            "patternDefinition": {
                                "id": pattern_def.get("id")
                            },
                            "enabled": True,
                            "parameters": pattern.get("parameters", [])
                        }
                        new_patterns.append(pattern_entry)
                
                all_patterns.extend(new_patterns)
                
                # Check if there are more pages
                pagination = patterns_response.get("pagination", {})
                cursor = pagination.get("cursor")
                if not cursor or cursor == "0":
                    break
                    
                time.sleep(1)  # Rate limiting
            
            if all_patterns:
                comprehensive_data["tool_patterns"][tool_uuid] = {
                    "name": tool.get("name", f"Tool_{tool_uuid}"),
                    "patterns": all_patterns
                }
                print(f"Found {len(all_patterns)} patterns for tool {tool.get('name', tool_uuid)}")
            
        return comprehensive_data
        
    except Exception as e:
        print(f"An error occurred while fetching cloud data: {str(e)}")
        traceback.print_exc()
        return None

def create_cloud_coding_standard(provider: str, cloud_org_name: str, 
                               source_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a new coding standard in Codacy Cloud."""
    with spinner("Creating new coding standard") as spin:
        url = f"{CLOUD_API_URL}/organizations/{provider}/{cloud_org_name}/coding-standards"
        
        languages = source_data['coding_standard'].get('languages', [])
        if not languages:
            spin.warn("No languages found. Defaulting to Java.")
            languages = ["Java"]

        new_standard_data = {
            "name": f"Migrated: {source_data['coding_standard'].get('name', 'Unknown')}",
            "languages": languages
        }

        new_standard = make_api_request(url, method="POST", data=new_standard_data)
        if not new_standard or not new_standard.get("data"):
            spin.fail("Failed to create new coding standard")
            return None
        
        spin.succeed(f"Created new coding standard: {new_standard['data']['name']}")
        return new_standard["data"]

def disable_default_cloud_tools(provider: str, cloud_org_name: str, standard_id: str) -> None:
    """Disable default tools in the coding standard."""
    print("\nDisabling default tools...")
    url = f"{CLOUD_API_URL}/organizations/{provider}/{cloud_org_name}/coding-standards/{standard_id}/tools"
    tools = make_api_request(url)
    
    if not tools or not tools.get("data"):
        print("Failed to fetch tools")
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

def update_cloud_coding_standard(provider: str, cloud_org_name: str, standard_id: str, source_data: Dict[str, Any]) -> None:
    """Update cloud coding standard with source configuration."""
    for cloud_tool_uuid, tool_data in source_data["tool_patterns"].items():
        cloud_tool_name = tool_data["name"]
        desired_patterns = tool_data["patterns"]
        print(f"\nProcessing tool: {cloud_tool_name}")
        
        base_url = f"{CLOUD_API_URL}/organizations/{provider}/{cloud_org_name}/coding-standards/{standard_id}/tools/{cloud_tool_uuid}"
        
        # Step 1: Enable the tool
        print("Enabling tool...")
        enable_data = {
            "enabled": True,
            "patterns": []
        }
        result = make_api_request(base_url, method="PATCH", data=enable_data)
        if not result:
            print(f"Failed to enable tool {cloud_tool_name}")
            continue
        
        time.sleep(1)  # Rate limiting
        
        # Step 2: Get all currently enabled patterns
        print("Getting current patterns...")
        current_patterns = []
        cursor = None
        
        while True:
            params = {"cursor": cursor} if cursor else None
            patterns_response = make_api_request(f"{base_url}/patterns", params=params)
            
            if not patterns_response or not patterns_response.get("data"):
                break
                
            # Add patterns from this page
            current_patterns.extend([
                {"id": pattern["patternDefinition"]["id"], "enabled": False}
                for pattern in patterns_response["data"]
                if pattern.get("enabled", False)
            ])
            
            # Check for more pages
            pagination = patterns_response.get("pagination", {})
            cursor = pagination.get("cursor")
            if not cursor or cursor == "0":
                break
                
            time.sleep(1)  # Rate limiting
        
        print(f"Found {len(current_patterns)} currently enabled patterns")
        
        # Step 3: Disable all current patterns
        if current_patterns:
            print("Disabling all current patterns...")
            disable_data = {
                "enabled": True,
                "patterns": current_patterns  # All patterns with enabled: False
            }
            
            result = make_api_request(base_url, method="PATCH", data=disable_data)
            if not result:
                print(f"Failed to disable existing patterns for {cloud_tool_name}")
                continue
                
            time.sleep(1)  # Rate limiting
        
        # Step 4: Enable our desired patterns
        print(f"Updating with {len(desired_patterns)} specific patterns...")
        update_data = {
            "enabled": True,
            "patterns": [
                {
                    "id": p["patternDefinition"]["id"],
                    "enabled": True,
                    "parameters": p.get("parameters", [])
                } for p in desired_patterns
            ]
        }

        result = make_api_request(base_url, method="PATCH", data=update_data)
        
        if result is True or result is not None:
            print(f"Successfully updated configuration and patterns for tool {cloud_tool_name}")
        else:
            print(f"Failed to update configuration and patterns for tool {cloud_tool_name}")
        
        time.sleep(1)

def promote_coding_standard(provider: str, cloud_org_name: str, standard_id: str) -> bool:
    """Promote the coding standard to make it the default."""
    with spinner("Promoting coding standard") as spin:
        url = f"{CLOUD_API_URL}/organizations/{provider}/{cloud_org_name}/coding-standards/{standard_id}/promote"
        result = make_api_request(url, method="POST")
        if result is not None:
            spin.succeed("Successfully promoted coding standard")
            return True
        else:
            spin.fail("Failed to promote coding standard")
            return False

def migrate_to_destinations(provider: str, source_data: Dict[str, Any], 
                          destination_orgs: List[str], is_cloud_to_cloud: bool = False) -> None:
    """Migrate configuration to multiple destination organizations."""
    for dest_org in destination_orgs:
        try:
            print(f"\nMigrating to organization: {dest_org}")
            
            # Create new coding standard
            print("Creating new coding standard...")
            cloud_standard = create_cloud_coding_standard(provider, dest_org, source_data)
            if not cloud_standard:
                print(f"Failed to create coding standard for {dest_org}")
                continue
                
            # First disable default tools
            print("Disabling default tools...")
            disable_default_cloud_tools(provider, dest_org, cloud_standard["id"])
            
            time.sleep(1)  # Give API time to process
            
            # Then update with source configuration
            print("Updating coding standard with source configuration...")
            update_cloud_coding_standard(provider, dest_org, cloud_standard["id"], source_data)
            
            # Finally promote the standard
            promote_coding_standard(provider, dest_org, cloud_standard["id"])
            
            print(f"Successfully migrated to {dest_org}")
            
        except Exception as e:
            print(f"Failed to migrate to {dest_org}: {str(e)}")
            continue

def get_migration_details() -> Dict[str, Any]:
    """Get migration details through interactive prompts."""
    print("\nCodacy Configuration Migration Tool")
    print("=" * 40)
    
    # Get migration mode
    print("\nMigration Modes:")
    print("1. Self-Hosted to Cloud Migration")
    print("2. Cloud to Cloud Migration")
    mode = get_user_input("Select migration mode (1 or 2): ", ["1", "2"])
    
    # Get provider
    print("\nSupported Providers:")
    print("gh - GitHub")
    print("gl - GitLab")
    print("bb - Bitbucket")
    provider = get_user_input("Enter provider (gh/gl/bb): ", ["gh", "gl", "bb"])
    
    # Get source organization
    source_org = get_user_input("\nEnter source organization name: ")
    
    # Get destination organizations
    print("\nEnter destination organization(s)")
    print("Enter one organization per line. Press Enter twice when done.")
    destinations = []
    while True:
        dest = get_user_input("Enter destination organization (or press Enter to finish): ")
        if not dest and destinations:
            break
        if dest:
            destinations.append(dest)
    
    return {
        "mode": mode,
        "provider": provider,
        "source_org": source_org,
        "destinations": destinations
    }

def main():
    try:
        # Get migration details
        details = get_migration_details()
        
        # Validate environment variables
        if details["mode"] == "1" and not SELF_HOSTED_API_TOKEN:
            raise ValueError("SELF_HOSTED_API_TOKEN is not set in the environment variables")
        if not CLOUD_API_TOKEN:
            raise ValueError("CLOUD_API_TOKEN is not set in the environment variables")
        
        # Get source data based on migration mode
        is_cloud_to_cloud = details["mode"] == "2"
        if not is_cloud_to_cloud:
            print("\nFetching data from self-hosted Codacy...")
            self_hosted_tools = get_self_hosted_tools()
            cloud_tools = get_cloud_tools()
            source_data = get_self_hosted_data(details["provider"], details["source_org"], 
                                             self_hosted_tools, cloud_tools)
        else:
            print("\nFetching data from source Cloud organization...")
            source_data = get_source_cloud_data(details["provider"], details["source_org"])
        
        if not source_data:
            raise Exception("Failed to fetch source data")
        
        # Perform migration
        migrate_to_destinations(details["provider"], source_data, details["destinations"], 
                             is_cloud_to_cloud=is_cloud_to_cloud)
        
        print("\nMigration completed successfully!")
        
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()