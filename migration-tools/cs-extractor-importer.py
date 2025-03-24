#!/usr/bin/env python3
import requests
import json
import os
import sys
import traceback
import time
import logging
import argparse
from logging.handlers import RotatingFileHandler
from typing import List, Dict, Any, Optional, Tuple
from halo import Halo

# Codacy API endpoints
SELF_HOSTED_API_URL = os.environ.get("SELF_HOSTED_API_URL", "https://codacy.mycompany.com/api/v3")
CLOUD_API_URL = "https://app.codacy.com/api/v3"

# API Tokens
SELF_HOSTED_API_TOKEN = os.environ.get("SELF_HOSTED_API_TOKEN")
CLOUD_API_TOKEN = os.environ.get("CLOUD_API_TOKEN")

# Setup logging
def setup_logging(log_file="codacy_migration.log", log_level=logging.DEBUG):
    """Set up logging to file and console."""
    logger = logging.getLogger("codacy_migration")
    logger.setLevel(log_level)
    
    # File handler
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
    file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_format = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_format)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Initialize logger with DEBUG level for more detailed logging
logger = setup_logging()

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
                    data: Dict = None, params: Dict = None, max_retries: int = 3) -> Optional[Dict]:
    """Make an API request to Codacy with retry logic."""
    if headers is None:
        headers = {}
    headers["Accept"] = "application/json"
    headers["Content-Type"] = "application/json"
    headers["api-token"] = CLOUD_API_TOKEN if url.startswith(CLOUD_API_URL) else SELF_HOSTED_API_TOKEN

    retry_count = 0
    while retry_count <= max_retries:
        try:
            logger.debug(f"Making {method} request to {url}")
            if data:
                logger.debug(f"Request data: {json.dumps(data)[:1000]}...")
            if params:
                logger.debug(f"Request params: {params}")
                
            response = requests.request(method, url, headers=headers, json=data, params=params, timeout=1000)
            response.raise_for_status()
            
            if response.status_code == 204:  # No Content
                logger.debug(f"Request successful: {response.status_code} No Content")
                return True
            elif response.text:
                logger.debug(f"Request successful: {response.status_code}")
                if len(response.text) < 1000:
                    logger.debug(f"Response: {response.text}")
                else:
                    logger.debug(f"Response (truncated): {response.text[:1000]}...")
                return response.json()
            else:
                logger.debug(f"Request successful but no content: {response.status_code}")
                return None
        except requests.exceptions.RequestException as req_err:
            retry_count += 1
            if retry_count <= max_retries:
                wait_time = 2 ** retry_count  # Exponential backoff
                logger.warning(f"Request failed: {req_err}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Request failed after {max_retries} retries: {req_err}")
                if hasattr(req_err, 'response') and req_err.response:
                    logger.error(f"Response status: {req_err.response.status_code}")
                    logger.error(f"Response text: {req_err.response.text[:1000]}...")
                return None

def get_self_hosted_tools() -> Dict[str, str]:
    """Fetch tools from self-hosted Codacy."""
    with spinner("Fetching self-hosted tools") as spin:
        url = f"{SELF_HOSTED_API_URL}/tools"
        tools = make_api_request(url)
        if not tools or not tools.get("data"):
            spin.fail("Failed to fetch tools from self-hosted Codacy")
            logger.error("Failed to fetch tools from self-hosted Codacy")
            return {}
        spin.succeed("Successfully fetched self-hosted tools")
        logger.info(f"Successfully fetched {len(tools['data'])} self-hosted tools")
        return {tool["uuid"]: tool["name"] for tool in tools["data"]}

def get_cloud_tools() -> Dict[str, str]:
    """Fetch tools from Codacy Cloud."""
    with spinner("Fetching cloud tools") as spin:
        url = f"{CLOUD_API_URL}/tools"
        tools = make_api_request(url)
        if not tools or not tools.get("data"):
            spin.fail("Failed to fetch tools from Codacy Cloud")
            logger.error("Failed to fetch tools from Codacy Cloud")
            return {}
        spin.succeed("Successfully fetched cloud tools")
        logger.info(f"Successfully fetched {len(tools['data'])} cloud tools")
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
    env_type = "self-hosted" if is_self_hosted else "cloud"
    with spinner(f"Fetching coding standards from {env_type}") as spin:
        try:
            url = f"{base_url}/organizations/{provider}/{organization}/coding-standards"
            logger.info(f"Fetching coding standards from {env_type} for {provider}/{organization}")
            response = make_api_request(url)
            if not response or not response.get('data'):
                error_msg = f"Failed to fetch coding standards from {env_type}"
                spin.fail(error_msg)
                logger.error(error_msg)
                return []
                
            all_standards = response['data']
            coding_standards = [standard for standard in all_standards 
                              if not standard.get('isDraft', False)]
            
            spin.succeed(f"Fetched {len(coding_standards)} active coding standards")
            logger.info(f"Fetched {len(coding_standards)} active coding standards from {env_type}")
            return coding_standards
        except Exception as e:
            error_msg = f"Error fetching coding standards from {env_type}: {str(e)}"
            spin.fail(error_msg)
            logger.error(error_msg)
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

def extract_coding_standard(provider: str, org_name: str, is_self_hosted: bool = False, 
                          output_file: str = None) -> Dict[str, Any]:
    """Extract coding standard configuration from Codacy."""
    base_url = SELF_HOSTED_API_URL if is_self_hosted else CLOUD_API_URL
    env_type = "self-hosted" if is_self_hosted else "cloud"
    
    print(f"\nExtracting coding standard from {env_type} organization: {org_name}")
    logger.info(f"Extracting coding standard from {env_type} organization: {org_name}")
    
    comprehensive_data = {}
    
    try:
        # Get coding standards
        standards = get_coding_standards(org_name, provider, is_self_hosted)
        if not standards:
            logger.error(f"No coding standards found in {env_type} organization {org_name}")
            raise Exception("No coding standards found")
        
        # Let user select the standard
        coding_standard = select_coding_standard(standards)
        comprehensive_data["coding_standard"] = coding_standard
        logger.info(f"Selected coding standard: {coding_standard.get('name', 'Unknown')}")
        print(f"Using coding standard: {coding_standard.get('name', 'Unknown')}")
        
        # Get tools
        url = f"{base_url}/organizations/{provider}/{org_name}/coding-standards/{coding_standard['id']}/tools"
        logger.info(f"Fetching tools for coding standard {coding_standard.get('name', 'Unknown')}")
        tools_response = make_api_request(url)
        
        if not tools_response or not tools_response.get("data"):
            logger.error(f"Failed to fetch tools from {env_type} organization")
            raise Exception("Failed to fetch tools")
        
        enabled_tools = [tool for tool in tools_response["data"] if tool.get("isEnabled", False)]
        logger.info(f"Found {len(enabled_tools)} enabled tools in {env_type} organization")
        print(f"Found {len(enabled_tools)} enabled tools")
        
        # Get patterns for each enabled tool
        comprehensive_data["tools"] = []
        
        for tool in enabled_tools:
            tool_uuid = tool["uuid"]
            tool_name = tool.get("name", f"Tool_{tool_uuid}")
            
            with spinner(f"Processing tool: {tool_name}") as spin:
                # Get patterns
                patterns_url = f"{url}/{tool_uuid}/patterns"
                all_patterns = []
                cursor = None
                
                while True:
                    params = {"cursor": cursor} if cursor else None
                    patterns_response = make_api_request(patterns_url, params=params)
                    
                    if not patterns_response or not patterns_response.get("data"):
                        break
                    
                    # Add patterns from this page
                    enabled_patterns = [p for p in patterns_response["data"] if p.get("enabled", False)]
                    all_patterns.extend(enabled_patterns)
                    
                    # Check for more pages
                    pagination = patterns_response.get("pagination", {})
                    cursor = pagination.get("cursor")
                    if not cursor or cursor == "0":
                        break
                    
                    time.sleep(1)  # Rate limiting
                
                if all_patterns:
                    tool_data = {
                        "uuid": tool_uuid,
                        "name": tool_name,
                        "patterns": all_patterns
                    }
                    comprehensive_data["tools"].append(tool_data)
                    spin.succeed(f"Found {len(all_patterns)} enabled patterns")
                    logger.info(f"Found {len(all_patterns)} enabled patterns for tool {tool_name}")
                else:
                    spin.info("No enabled patterns found")
                    logger.info(f"No enabled patterns found for tool {tool_name}")
        
        # Save to file if output_file is provided
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(comprehensive_data, f, indent=2)
            print(f"\nCoding standard configuration saved to {output_file}")
            logger.info(f"Coding standard configuration saved to {output_file}")
        
        return comprehensive_data
    
    except Exception as e:
        error_msg = f"An error occurred while extracting coding standard: {str(e)}"
        logger.error(error_msg)
        print(error_msg)
        traceback.print_exc()
        return None

def get_self_hosted_data(provider: str, remote_org_name: str, self_hosted_tools: Dict[str, str], 
                        cloud_tools: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Fetch data from self-hosted Codacy."""
    if not SELF_HOSTED_API_TOKEN:
        logger.error("SELF_HOSTED_API_TOKEN is not set")
        raise ValueError("SELF_HOSTED_API_TOKEN is not set")

    comprehensive_data = {}

    try:
        # Get coding standards
        standards = get_coding_standards(remote_org_name, provider, is_self_hosted=True)
        if not standards:
            logger.error("No coding standards found in self-hosted environment")
            raise Exception("No coding standards found")
        
        # Let user select the standard
        coding_standard = select_coding_standard(standards)
        comprehensive_data["coding_standard"] = coding_standard
        logger.info(f"Selected coding standard: {coding_standard.get('name', 'Unknown')}")
        print(f"Using coding standard: {coding_standard.get('name', 'Unknown')}")

        # Get enabled tools
        with spinner("Fetching enabled tools") as spin:
            url = f"{SELF_HOSTED_API_URL}/organizations/{provider}/{remote_org_name}/coding-standards/{coding_standard['id']}/tools"
            tools = make_api_request(url)
            if not tools or not tools.get("data"):
                error_msg = "Failed to fetch tools from self-hosted environment"
                spin.fail(error_msg)
                logger.error(error_msg)
                return None
            
            enabled_tools = [tool for tool in tools["data"] if tool.get("isEnabled", False)]
            comprehensive_data["tools"] = enabled_tools
            spin.succeed(f"Found {len(enabled_tools)} enabled tools")
            logger.info(f"Found {len(enabled_tools)} enabled tools in self-hosted environment")

        # Get patterns for each enabled tool
        comprehensive_data["tool_patterns"] = {}
        for tool in enabled_tools:
            tool_name = tool.get('name', 'Unknown')
            with spinner(f"Processing tool: {tool_name}") as spin:
                sh_tool_uuid = tool.get("uuid")
                if not sh_tool_uuid:
                    spin.warn("Skipping tool with missing UUID")
                    logger.warning(f"Skipping tool {tool_name} with missing UUID")
                    continue
                
                sh_tool_name = self_hosted_tools.get(sh_tool_uuid, f"Unknown Tool {sh_tool_uuid}")
                
                cloud_tool_uuid, cloud_tool_name = map_sh_to_cloud_tool(sh_tool_uuid, 
                                                                      self_hosted_tools, 
                                                                      cloud_tools)
                if not cloud_tool_uuid:
                    spin.warn(f"No matching cloud tool found for {sh_tool_name}")
                    logger.warning(f"No matching cloud tool found for {sh_tool_name}")
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
                        logger.info(f"Found {len(enabled_patterns)} enabled patterns for tool {cloud_tool_name}")
                    else:
                        spin.info("No enabled patterns found")
                        logger.info(f"No enabled patterns found for tool {cloud_tool_name}")
                else:
                    spin.fail("Failed to fetch patterns")
                    logger.error(f"Failed to fetch patterns for tool {cloud_tool_name}")

        return comprehensive_data

    except Exception as e:
        error_msg = f"An error occurred while fetching self-hosted data: {str(e)}"
        logger.error(error_msg)
        print(error_msg)
        traceback.print_exc()
        return None

def get_source_cloud_data(provider: str, source_org_name: str) -> Optional[Dict[str, Any]]:
    """Fetch configuration data from source Cloud organization."""
    comprehensive_data = {}
    
    try:
        # Get coding standards
        standards = get_coding_standards(source_org_name, provider)
        if not standards:
            logger.error(f"No coding standards found in cloud organization {source_org_name}")
            raise Exception("No coding standards found")
        
        # Let user select the standard
        coding_standard = select_coding_standard(standards)
        comprehensive_data["coding_standard"] = coding_standard
        logger.info(f"Selected coding standard: {coding_standard['name']}")
        print(f"Using coding standard: {coding_standard['name']}")
        
        # Get tools
        url = f"{CLOUD_API_URL}/organizations/{provider}/{source_org_name}/coding-standards/{coding_standard['id']}/tools"
        logger.info(f"Fetching tools for coding standard {coding_standard['name']}")
        tools = make_api_request(url)
        if not tools or not tools.get("data"):
            logger.error("Failed to fetch tools from cloud organization")
            raise Exception("Failed to fetch tools")
            
        enabled_tools = [tool for tool in tools["data"] if tool.get("isEnabled", False)]
        logger.info(f"Found {len(enabled_tools)} enabled tools in cloud organization")
        print(f"Found {len(enabled_tools)} enabled tools")
        
        # Get patterns for each enabled tool
        comprehensive_data["tool_patterns"] = {}
        for tool in enabled_tools:
            tool_uuid = tool["uuid"]
            tool_name = tool.get("name", f"Tool_{tool_uuid}")
            logger.info(f"Fetching patterns for tool {tool_name}")
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
                
                # Check for more pages
                pagination = patterns_response.get("pagination", {})
                cursor = pagination.get("cursor")
                if not cursor or cursor == "0":
                    break
                    
                time.sleep(1)  # Rate limiting
            
            if all_patterns:
                comprehensive_data["tool_patterns"][tool_uuid] = {
                    "name": tool_name,
                    "patterns": all_patterns
                }
                logger.info(f"Found {len(all_patterns)} patterns for tool {tool_name}")
                print(f"Found {len(all_patterns)} patterns for tool {tool_name}")
            else:
                comprehensive_data["tool_patterns"][tool_uuid] = {
                    "name": tool_name,
                    "patterns": []
                }
                logger.info(f"No patterns found for tool {tool_name}")
                print(f"No patterns found for tool {tool_name}")
            
        return comprehensive_data
        
    except Exception as e:
        error_msg = f"An error occurred while fetching cloud data: {str(e)}"
        logger.error(error_msg)
        print(error_msg)
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
            logger.warning("No languages found in source coding standard. Defaulting to Java.")
            languages = ["Java"]

        standard_name = f"Migrated: {source_data['coding_standard'].get('name', 'Unknown')}_{int(time.time())}"
        new_standard_data = {
            "name": standard_name,
            "languages": languages
        }

        logger.info(f"Creating new coding standard '{standard_name}' with languages: {', '.join(languages)}")
        new_standard = make_api_request(url, method="POST", data=new_standard_data)
        if not new_standard or not new_standard.get("data"):
            error_msg = f"Failed to create new coding standard in {cloud_org_name}"
            spin.fail(error_msg)
            logger.error(error_msg)
            return None
        
        spin.succeed(f"Created new coding standard: {new_standard['data']['name']}")
        logger.info(f"Successfully created new coding standard: {new_standard['data']['name']}")
        return new_standard["data"]

def promote_coding_standard(provider: str, cloud_org_name: str, standard_id: str) -> bool:
    """Promote the coding standard to make it the default."""
    logger.info(f"Promoting coding standard for {cloud_org_name}")
    with spinner("Promoting coding standard") as spin:
        url = f"{CLOUD_API_URL}/organizations/{provider}/{cloud_org_name}/coding-standards/{standard_id}/promote"
        result = make_api_request(url, method="POST")
        if result is not None:
            spin.succeed("Successfully promoted coding standard")
            logger.info("Successfully promoted coding standard")
            return True
        else:
            spin.fail("Failed to promote coding standard")
            logger.error("Failed to promote coding standard")
            return False

def validate_migration(provider: str, dest_org: str, standard_id: str, source_data: Dict[str, Any], 
                     attempt: int = 1, max_attempts: int = 3) -> bool:
    """Validate that the migration was successful by comparing source and destination."""
    logger.info(f"Validating migration for {dest_org} (attempt {attempt}/{max_attempts})")
    print(f"\nValidating migration for {dest_org} (attempt {attempt}/{max_attempts})...")
    
    # Get destination tools
    url = f"{CLOUD_API_URL}/organizations/{provider}/{dest_org}/coding-standards/{standard_id}/tools"
    dest_tools_response = make_api_request(url)
    
    if not dest_tools_response or not dest_tools_response.get("data"):
        logger.error("Failed to fetch destination tools for validation")
        print("Failed to fetch destination tools for validation")
        return False
        
    dest_tools = [tool for tool in dest_tools_response["data"] if tool.get("isEnabled", False)]
    
    # Compare tool counts
    source_tool_count = len(source_data["tool_patterns"])
    dest_tool_count = len(dest_tools)
    
    logger.info(f"Source tools: {source_tool_count}, Destination tools: {dest_tool_count}")
    
    if source_tool_count != dest_tool_count:
        logger.warning(f"Tool count mismatch: Source has {source_tool_count}, Destination has {dest_tool_count}")
        # Log the tools that are missing
        source_tool_uuids = set(source_data["tool_patterns"].keys())
        dest_tool_uuids = {tool["uuid"] for tool in dest_tools}
        
        missing_in_dest = source_tool_uuids - dest_tool_uuids
        missing_in_source = dest_tool_uuids - source_tool_uuids
        
        if missing_in_dest:
            logger.warning(f"Tools in source but missing in destination: {missing_in_dest}")
        if missing_in_source:
            logger.warning(f"Tools in destination but missing in source: {missing_in_source}")
    
    # Compare patterns for each tool
    validation_results = []
    tools_to_fix = []
    
    # Limit the number of tools to check to avoid excessive API calls
    max_tools_to_check = 10
    if len(dest_tools) > max_tools_to_check:
        logger.info(f"Limiting validation to {max_tools_to_check} tools to avoid excessive API calls")
        dest_tools = dest_tools[:max_tools_to_check]
    
    for dest_tool in dest_tools:
        tool_uuid = dest_tool["uuid"]
        tool_name = dest_tool.get("name", tool_uuid)
        
        # Skip if tool not in source
        if tool_uuid not in source_data["tool_patterns"]:
            logger.warning(f"Tool {tool_name} not found in source data")
            continue
            
        # Get destination patterns
        patterns_url = f"{url}/{tool_uuid}/patterns"
        dest_patterns = []
        cursor = None
        
        # Limit the number of pages to fetch to avoid excessive API calls
        max_pages = 10
        page_count = 0
        
        while page_count < max_pages:
            page_count += 1
            params = {"cursor": cursor} if cursor else None
            patterns_response = make_api_request(patterns_url, params=params)
            
            if not patterns_response or not patterns_response.get("data"):
                break
                
            dest_patterns.extend([p for p in patterns_response["data"] if p.get("enabled", False)])
            
            # Check for more pages
            pagination = patterns_response.get("pagination", {})
            cursor = pagination.get("cursor")
            if not cursor or cursor == "0":
                break
                
            time.sleep(1)  # Rate limiting
        
        # Compare pattern counts
        source_patterns = source_data["tool_patterns"][tool_uuid]["patterns"]
        source_pattern_count = len(source_patterns)
        dest_pattern_count = len(dest_patterns)
        
        logger.info(f"Tool {tool_name}: Source patterns: {source_pattern_count}, Destination patterns: {dest_pattern_count}")
        
        # If pattern counts don't match, log detailed information
        if source_pattern_count != dest_pattern_count:
            logger.warning(f"Pattern count mismatch for tool {tool_name}")
            
            # Get pattern IDs for comparison
            source_pattern_ids = {p["patternDefinition"]["id"] for p in source_patterns}
            dest_pattern_ids = {p["patternDefinition"]["id"] for p in dest_patterns}
            
            missing_in_dest = source_pattern_ids - dest_pattern_ids
            missing_in_source = dest_pattern_ids - source_pattern_ids
            
            if missing_in_dest:
                logger.warning(f"Patterns in source but missing in destination for {tool_name}: {list(missing_in_dest)[:10]}")
                if len(missing_in_dest) > 10:
                    logger.warning(f"... and {len(missing_in_dest) - 10} more")
                
                # Add to list of tools to fix
                missing_patterns = [p for p in source_patterns if p["patternDefinition"]["id"] in missing_in_dest]
                # Limit the number of patterns to fix to avoid excessive API calls
                if len(missing_patterns) > 20:
                    logger.info(f"Limiting fix to 20 patterns for {tool_name}")
                    missing_patterns = missing_patterns[:20]
                
                tools_to_fix.append({
                    "tool_uuid": tool_uuid,
                    "tool_name": tool_name,
                    "missing_patterns": missing_patterns
                })
            
            if missing_in_source:
                logger.warning(f"Patterns in destination but missing in source for {tool_name}: {list(missing_in_source)[:10]}")
                if len(missing_in_source) > 10:
                    logger.warning(f"... and {len(missing_in_source) - 10} more")
        
        validation_results.append({
            "tool_name": tool_name,
            "tool_uuid": tool_uuid,
            "source_patterns": source_pattern_count,
            "dest_patterns": dest_pattern_count,
            "match": source_pattern_count == dest_pattern_count
        })
    
    # Print validation summary
    print("\nValidation Summary:")
    print("-" * 80)
    all_match = True
    
    for result in validation_results:
        match_status = "✓" if result["match"] else "✗"
        print(f"{match_status} {result['tool_name']}: {result['source_patterns']} patterns -> {result['dest_patterns']} patterns")
        if not result["match"]:
            all_match = False
    
    print("-" * 80)
    print(f"Overall validation: {'Passed' if all_match else 'Failed'}")
    
    # Try to fix missing patterns if validation failed and we haven't exceeded max attempts
    if not all_match and tools_to_fix and attempt < max_attempts:
        print(f"\nAttempting to fix missing patterns (attempt {attempt}/{max_attempts})...")
        fix_missing_patterns(provider, dest_org, standard_id, tools_to_fix)
        
        # Re-validate after fixing with incremented attempt counter
        print(f"\nRe-validating after fixes...")
        return validate_migration(provider, dest_org, standard_id, source_data, attempt + 1, max_attempts)
    
    if all_match:
        logger.info(f"Validation passed for {dest_org}")
    else:
        logger.warning(f"Validation failed for {dest_org}")
        # Log detailed information about failed validations
        failed_validations = [r for r in validation_results if not r["match"]]
        logger.warning(f"Failed validations: {json.dumps(failed_validations, indent=2)}")
        
        if attempt >= max_attempts:
            logger.warning(f"Maximum validation attempts ({max_attempts}) reached. Some patterns may not have been migrated successfully.")
            print(f"\nMaximum validation attempts ({max_attempts}) reached. Some patterns may not have been migrated successfully.")
            print("The migration will be considered partially successful.")
    
    return all_match

def fix_missing_patterns(provider: str, dest_org: str, standard_id: str, tools_to_fix: List[Dict[str, Any]]) -> None:
    """Fix missing patterns by adding them individually."""
    for tool_info in tools_to_fix:
        tool_uuid = tool_info["tool_uuid"]
        tool_name = tool_info["tool_name"]
        missing_patterns = tool_info["missing_patterns"]
        
        print(f"Fixing {len(missing_patterns)} missing patterns for {tool_name}...")
        logger.info(f"Fixing {len(missing_patterns)} missing patterns for {tool_name}")
        
        base_url = f"{CLOUD_API_URL}/organizations/{provider}/{dest_org}/coding-standards/{standard_id}/tools/{tool_uuid}"
        
        # Process each pattern individually for maximum reliability
        for i, pattern in enumerate(missing_patterns):
            pattern_id = pattern["patternDefinition"]["id"]
            print(f"Adding pattern {i+1}/{len(missing_patterns)}: {pattern_id}")
            
            pattern_entry = {
                "id": pattern_id,
                "enabled": True
            }
            
            # Add parameters if present
            if "parameters" in pattern and pattern["parameters"]:
                pattern_entry["parameters"] = pattern["parameters"]
            
            update_data = {
                "enabled": True,
                "patterns": [pattern_entry]
            }
            
            # Try up to 3 times
            success = False
            for attempt in range(1, 4):
                if attempt > 1:
                    print(f"Retry attempt {attempt} for pattern {pattern_id}...")
                
                result = make_api_request(base_url, method="PATCH", data=update_data)
                if result:
                    logger.info(f"Successfully added pattern {pattern_id}")
                    success = True
                    break
                else:
                    logger.warning(f"Failed to add pattern {pattern_id} (attempt {attempt})")
                    time.sleep(3)
            
            if not success:
                logger.error(f"Failed to add pattern {pattern_id} after all attempts")
            
            # Small delay between patterns
            time.sleep(1)

def verify_patterns_enabled(base_url: str, expected_pattern_ids: List[str]) -> bool:
    """Verify that all expected patterns are enabled."""
    enabled_pattern_ids = set()
    cursor = None
    
    while True:
        params = {"cursor": cursor} if cursor else None
        patterns_response = make_api_request(f"{base_url}/patterns", params=params)
        
        if not patterns_response or not patterns_response.get("data"):
            break
            
        # Add enabled pattern IDs from this page
        for pattern in patterns_response["data"]:
            if pattern.get("enabled", False) and pattern.get("patternDefinition", {}).get("id"):
                enabled_pattern_ids.add(pattern["patternDefinition"]["id"])
        
        # Check for more pages
        pagination = patterns_response.get("pagination", {})
        cursor = pagination.get("cursor")
        if not cursor or cursor == "0":
            break
            
        time.sleep(1)  # Rate limiting
    
    # Check if all expected patterns are enabled
    expected_set = set(expected_pattern_ids)
    missing_patterns = expected_set - enabled_pattern_ids
    
    if missing_patterns:
        logger.warning(f"Missing {len(missing_patterns)} patterns after update")
        logger.warning(f"First few missing patterns: {list(missing_patterns)[:5]}")
        return False
    
    return True

def disable_default_cloud_tools(provider: str, cloud_org_name: str, standard_id: str) -> None:
    """Disable default tools in the coding standard."""
    logger.info(f"Disabling default tools for {cloud_org_name}")
    print("\nDisabling default tools...")
    url = f"{CLOUD_API_URL}/organizations/{provider}/{cloud_org_name}/coding-standards/{standard_id}/tools"
    tools = make_api_request(url)
    
    if not tools or not tools.get("data"):
        logger.error("Failed to fetch tools for disabling")
        print("Failed to fetch tools")
        return

    for tool in tools["data"]:
        if tool.get("isEnabled", False):
            tool_uuid = tool["uuid"]
            tool_name = tool.get("name", tool_uuid)
            update_url = f"{url}/{tool_uuid}"
            update_data = {
                "enabled": False,
                "patterns": []
            }
            
            result = make_api_request(update_url, method="PATCH", data=update_data)
            if result is True or result is not None:
                logger.info(f"Successfully disabled tool: {tool_name}")
                print(f"Successfully disabled tool: {tool_name}")
            else:
                logger.error(f"Failed to disable tool: {tool_name}")
                print(f"Failed to disable tool: {tool_name}")
            
            time.sleep(1)

def update_cloud_coding_standard(provider: str, cloud_org_name: str, standard_id: str, source_data: Dict[str, Any]) -> None:
    """Update cloud coding standard with source configuration."""
    logger.info(f"Updating coding standard for {cloud_org_name}")
    
    for cloud_tool_uuid, tool_data in source_data["tool_patterns"].items():
        cloud_tool_name = tool_data["name"]
        desired_patterns = tool_data["patterns"]
        logger.info(f"Processing tool: {cloud_tool_name} with {len(desired_patterns)} patterns")
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
            logger.error(f"Failed to enable tool {cloud_tool_name}")
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
        
        logger.info(f"Found {len(current_patterns)} currently enabled patterns for {cloud_tool_name}")
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
                logger.error(f"Failed to disable existing patterns for {cloud_tool_name}")
                print(f"Failed to disable existing patterns for {cloud_tool_name}")
                continue
                
            time.sleep(3)  # Rate limiting
        
        # Step 4: Enable our desired patterns
        print(f"Updating with {len(desired_patterns)} specific patterns...")
        
        # Log pattern IDs for debugging
        pattern_ids = [p["patternDefinition"]["id"] for p in desired_patterns]
        logger.debug(f"Pattern IDs to enable: {pattern_ids[:10]}")
        if len(pattern_ids) > 10:
            logger.debug(f"... and {len(pattern_ids) - 10} more")
        
        # Prepare patterns for update
        patterns_to_enable = []
        for pattern in desired_patterns:
            pattern_entry = {
                "id": pattern["patternDefinition"]["id"],
                "enabled": True
            }
            
            # Add parameters if present
            if "parameters" in pattern and pattern["parameters"]:
                pattern_entry["parameters"] = pattern["parameters"]
                
            patterns_to_enable.append(pattern_entry)
        
        # Update in batches to avoid request size limits
        batch_size = 50  # Reduced batch size for better reliability
        failed_batches = []
        
        for i in range(0, len(patterns_to_enable), batch_size):
            batch = patterns_to_enable[i:i+batch_size]
            batch_num = i//batch_size + 1
            total_batches = (len(patterns_to_enable) + batch_size - 1)//batch_size
            print(f"Updating batch {batch_num}/{total_batches}...")
            
            update_data = {
                "enabled": True,
                "patterns": batch
            }
            
            # Try up to 3 times for each batch
            success = False
            for attempt in range(1, 4):
                if attempt > 1:
                    print(f"Retry attempt {attempt} for batch {batch_num}...")
                
                result = make_api_request(base_url, method="PATCH", data=update_data)
                if result:
                    logger.info(f"Successfully updated {len(batch)} patterns for {cloud_tool_name} (batch {batch_num})")
                    print(f"Successfully updated {len(batch)} patterns (batch {batch_num})")
                    success = True
                    break
                else:
                    logger.warning(f"Failed to update patterns for {cloud_tool_name} (batch {batch_num}, attempt {attempt})")
                    print(f"Failed to update patterns (batch {batch_num}, attempt {attempt})")
                    time.sleep(5)  # Longer wait between retries
            
            if not success:
                logger.error(f"All attempts failed for batch {batch_num}")
                failed_batches.append((i, batch))
            
            time.sleep(3)  # Rate limiting between batches
        
        # Retry failed batches with even smaller batch size
        if failed_batches:
            print(f"\nRetrying {len(failed_batches)} failed batches with smaller batch size...")
            smaller_batch_size = 10
            
            for batch_start, original_batch in failed_batches:
                for j in range(0, len(original_batch), smaller_batch_size):
                    mini_batch = original_batch[j:j+smaller_batch_size]
                    mini_batch_num = f"{batch_start//batch_size + 1}.{j//smaller_batch_size + 1}"
                    print(f"Retrying mini-batch {mini_batch_num}...")
                    
                    update_data = {
                        "enabled": True,
                        "patterns": mini_batch
                    }
                    
                    result = make_api_request(base_url, method="PATCH", data=update_data)
                    if result:
                        logger.info(f"Successfully updated {len(mini_batch)} patterns in retry (mini-batch {mini_batch_num})")
                        print(f"Successfully updated {len(mini_batch)} patterns in retry (mini-batch {mini_batch_num})")
                    else:
                        logger.error(f"Failed to update patterns in retry (mini-batch {mini_batch_num})")
                        print(f"Failed to update patterns in retry (mini-batch {mini_batch_num})")
                    
                    time.sleep(3)  # Rate limiting
        
        # Verify all patterns were enabled
        print("Verifying pattern updates...")
        verification_success = verify_patterns_enabled(base_url, pattern_ids)
        if verification_success:
            print(f"✓ All {len(pattern_ids)} patterns verified for {cloud_tool_name}")
            logger.info(f"All {len(pattern_ids)} patterns verified for {cloud_tool_name}")
        else:
            print(f"✗ Pattern verification failed for {cloud_tool_name}")
            logger.warning(f"Pattern verification failed for {cloud_tool_name}")
        
        print(f"Completed processing for {cloud_tool_name}")
        logger.info(f"Completed processing for {cloud_tool_name}")

def migrate_to_destinations(provider: str, source_data: Dict[str, Any], dest_orgs: List[str], 
                          make_default: bool = False) -> Dict[str, bool]:
    """Migrate coding standard to multiple destination organizations."""
    results = {}
    
    for dest_org in dest_orgs:
        print(f"\n{'='*80}\nMigrating to {dest_org}\n{'='*80}")
        logger.info(f"Starting migration to {dest_org}")
        
        try:
            # Step 1: Create new coding standard
            new_standard = create_cloud_coding_standard(provider, dest_org, source_data)
            if not new_standard:
                logger.error(f"Failed to create coding standard for {dest_org}")
                results[dest_org] = False
                continue
                
            standard_id = new_standard["id"]
            logger.info(f"Created coding standard with ID: {standard_id}")
            
            # Step 2: Disable default tools
            disable_default_cloud_tools(provider, dest_org, standard_id)
            
            # Step 3: Update with source configuration
            update_cloud_coding_standard(provider, dest_org, standard_id, source_data)
            
            # Step 4: Validate migration
            validation_result = validate_migration(provider, dest_org, standard_id, source_data)
            
            # Step 5: Promote if requested and validation passed
            if make_default and validation_result:
                logger.info(f"Promoting coding standard for {dest_org}")
                promote_result = promote_coding_standard(provider, dest_org, standard_id)
                if not promote_result:
                    logger.warning(f"Failed to promote coding standard for {dest_org}")
                    print(f"Failed to promote coding standard for {dest_org}")
            
            results[dest_org] = validation_result
            
        except Exception as e:
            error_msg = f"An error occurred during migration to {dest_org}: {str(e)}"
            logger.error(error_msg)
            print(error_msg)
            traceback.print_exc()
            results[dest_org] = False
    
    return results

def import_coding_standard(input_file: str, provider: str, dest_orgs: List[str], 
                         make_default: bool = False) -> Dict[str, bool]:
    """Import coding standard from a file to destination organizations."""
    print(f"\nImporting coding standard from file: {input_file}")
    logger.info(f"Importing coding standard from file: {input_file}")
    
    try:
        with open(input_file, 'r') as f:
            source_data = json.load(f)
        
        # Convert from extract format to import format if needed
        if "tools" in source_data and "tool_patterns" not in source_data:
            print("Converting from extract format to import format...")
            logger.info("Converting from extract format to import format")
            
            tool_patterns = {}
            for tool in source_data["tools"]:
                tool_uuid = tool["uuid"]
                tool_name = tool["name"]
                patterns = tool.get("patterns", [])
                
                if patterns:
                    tool_patterns[tool_uuid] = {
                        "name": tool_name,
                        "patterns": patterns
                    }
            
            source_data["tool_patterns"] = tool_patterns
        
        # Migrate to destinations
        return migrate_to_destinations(provider, source_data, dest_orgs, make_default)
        
    except Exception as e:
        error_msg = f"An error occurred during import: {str(e)}"
        logger.error(error_msg)
        print(error_msg)
        traceback.print_exc()
        return {dest_org: False for dest_org in dest_orgs}

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description="Codacy Coding Standard Extractor and Importer")
    
    # Common arguments
    parser.add_argument("--provider", help="Provider (e.g., gh, bb, gl)", default=None)
    
    # Create subparsers for extract and import commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract coding standard")
    extract_parser.add_argument("--org", help="Organization name", required=True)
    extract_parser.add_argument("--self-hosted", action="store_true", help="Extract from self-hosted Codacy")
    extract_parser.add_argument("--output", help="Output file path", default="coding_standard.json")
    
    # Import command
    import_parser = subparsers.add_parser("import", help="Import coding standard")
    import_parser.add_argument("--input", help="Input file path", required=True)
    import_parser.add_argument("--dest-orgs", help="Destination organizations (comma-separated)", required=True)
    import_parser.add_argument("--make-default", action="store_true", help="Make the coding standard default")
    
    args = parser.parse_args()
    
    # Check for required environment variables
    if args.command == "extract" and args.self_hosted and not SELF_HOSTED_API_TOKEN:
        print("Error: SELF_HOSTED_API_TOKEN environment variable is not set.")
        logger.error("SELF_HOSTED_API_TOKEN environment variable is not set")
        return 1
    
    if not CLOUD_API_TOKEN:
        print("Error: CLOUD_API_TOKEN environment variable is not set.")
        logger.error("CLOUD_API_TOKEN environment variable is not set")
        return 1
    
    # Get provider if not provided
    provider = args.provider
    if not provider:
        provider = get_user_input("Enter provider (e.g., gh, bb, gl): ")
    
    # Execute command
    if args.command == "extract":
        # Extract coding standard
        extract_coding_standard(provider, args.org, args.self_hosted, args.output)
        print(f"\nExtraction completed. Coding standard saved to {args.output}")
        
    elif args.command == "import":
        # Import coding standard
        dest_orgs = [org.strip() for org in args.dest_orgs.split(",")]
        results = import_coding_standard(args.input, provider, dest_orgs, args.make_default)
        
        # Print summary
        print("\nImport Summary:")
        print("=" * 80)
        for org, success in results.items():
            status = "✓ Success" if success else "✗ Failed"
            print(f"{status}: {org}")
        
        success_count = sum(1 for success in results.values() if success)
        print(f"\nSuccessfully imported to {success_count} out of {len(results)} organizations.")
        
    else:
        # Interactive mode
        print("\nCodacy Coding Standard Migration Tool")
        print("=" * 80)
        
        # Choose operation
        operation = get_user_input(
            "Select operation (1 for extract, 2 for import, 3 for extract and import): ", 
            ["1", "2", "3"]
        )
        
        if operation in ["1", "3"]:
            # Extract operation
            extract_type = get_user_input(
                "Select extract source (1 for self-hosted, 2 for cloud): ", 
                ["1", "2"]
            )
            
            is_self_hosted = (extract_type == "1")
            if is_self_hosted and not SELF_HOSTED_API_TOKEN:
                print("Error: SELF_HOSTED_API_TOKEN environment variable is not set.")
                logger.error("SELF_HOSTED_API_TOKEN environment variable is not set")
                return 1
                
            source_org_name = get_user_input("Enter source organization name: ")
            output_file = get_user_input("Enter output file path [coding_standard.json]: ") or "coding_standard.json"
            
            # Extract coding standard
            source_data = extract_coding_standard(provider, source_org_name, is_self_hosted, output_file)
            if not source_data:
                print("Failed to extract coding standard.")
                return 1
                
            print(f"\nExtraction completed. Coding standard saved to {output_file}")
            
            # If operation is extract only, we're done
            if operation == "1":
                return 0
        
        if operation in ["2", "3"]:
            # Import operation
            if operation == "2":
                # If we're only importing, we need to get the input file
                input_file = get_user_input("Enter input file path: ")
            else:
                # If we extracted and are now importing, use the output file from extraction
                input_file = output_file
            
            # Get destination organizations
            dest_orgs_input = get_user_input("Enter destination organization names (comma-separated): ")
            dest_orgs = [org.strip() for org in dest_orgs_input.split(",")]
            
            # Ask if the coding standard should be made default
            make_default = get_user_input("Make the coding standard default? (y/n): ", ["y", "n"]) == "y"
            
            # Import coding standard
            results = import_coding_standard(input_file, provider, dest_orgs, make_default)
            
            # Print summary
            print("\nImport Summary:")
            print("=" * 80)
            for org, success in results.items():
                status = "✓ Success" if success else "✗ Failed"
                print(f"{status}: {org}")
            
            success_count = sum(1 for success in results.values() if success)
            print(f"\nSuccessfully imported to {success_count} out of {len(results)} organizations.")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
