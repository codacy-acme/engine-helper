import argparse
import os
import requests
import json
from typing import List, Dict
from urllib.parse import urljoin, quote
from tqdm import tqdm

CLOUD_API_URL = "https://app.codacy.com"

def get_env_variable(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"{var_name} environment variable is not set")
    return value

def get_repositories(api_url: str, api_token: str, provider: str, organization: str) -> List[Dict]:
    url = urljoin(api_url, f"api/v3/organizations/{quote(provider)}/{quote(organization)}/repositories")
    headers = {"Accept": "application/json", "api-token": api_token}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json().get('data', [])

def get_quality_settings(api_url: str, api_token: str, provider: str, organization: str, repository: str, settings_type: str) -> Dict:
    url = urljoin(api_url, f"api/v3/organizations/{quote(provider)}/{quote(organization)}/repositories/{quote(repository)}/settings/quality/{settings_type}")
    headers = {"Accept": "application/json", "api-token": api_token}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json().get('data', {})

def update_cloud_quality_settings(api_token: str, provider: str, organization: str, repository: str, settings: Dict, settings_type: str) -> Dict:
    url = urljoin(CLOUD_API_URL, f"api/v3/organizations/{quote(provider)}/{quote(organization)}/repositories/{quote(repository)}/settings/quality/{settings_type}")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "api-token": api_token
    }
    response = requests.put(url, headers=headers, json=settings)
    response.raise_for_status()
    return response.json()

def select_repository(repositories: List[Dict]) -> Dict:
    print("\nAvailable repositories:")
    for i, repo in enumerate(repositories, 1):
        print(f"{i}. {repo['name']}")
    
    while True:
        try:
            choice = int(input("\nEnter the number of the repository you want to migrate: "))
            if 1 <= choice <= len(repositories):
                return repositories[choice - 1]
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def main():
    parser = argparse.ArgumentParser(description="Migrate Codacy repository quality settings from self-hosted to cloud.")
    parser.add_argument("-p", "--provider", required=True, help="The provider (e.g., gh for GitHub, gl for GitLab)")
    parser.add_argument("-o", "--organization", required=True, help="The remote organization name for self-hosted")
    parser.add_argument("-c", "--cloud-organization", required=True, help="The organization name in Codacy Cloud")
    args = parser.parse_args()

    self_hosted_api_url = get_env_variable('SELF_HOSTED_API_URL')
    self_hosted_api_token = get_env_variable('SELF_HOSTED_API_TOKEN')
    cloud_api_token = get_env_variable('CLOUD_API_TOKEN')

    migration_results = {}

    try:
        repositories = get_repositories(self_hosted_api_url, self_hosted_api_token, args.provider, args.organization)
        print(f"Retrieved {len(repositories)} repositories")

        selected_repo = select_repository(repositories)
        repo_name = selected_repo['name']
        
        print(f"\nMigrating settings for repository: {repo_name}")
        migration_results[repo_name] = {}

        with tqdm(total=3, desc="Migrating Settings", unit="setting") as pbar:
            for settings_type in ['repository', 'commits', 'pull-requests']:
                try:
                    # Get settings from self-hosted
                    self_hosted_settings = get_quality_settings(self_hosted_api_url, self_hosted_api_token, args.provider, args.organization, repo_name, settings_type)
                    
                    # Update settings in cloud
                    cloud_update_result = update_cloud_quality_settings(cloud_api_token, args.provider, args.cloud_organization, repo_name, self_hosted_settings, settings_type)
                    
                    # Verify the update
                    verified_settings = get_quality_settings(CLOUD_API_URL, cloud_api_token, args.provider, args.cloud_organization, repo_name, settings_type)
                    
                    migration_results[repo_name][settings_type] = {
                        "status": "success",
                        "self_hosted_settings": self_hosted_settings,
                        "cloud_update_result": cloud_update_result,
                        "verified_cloud_settings": verified_settings
                    }
                except requests.exceptions.RequestException as e:
                    migration_results[repo_name][settings_type] = {
                        "status": "error",
                        "error_message": str(e)
                    }
                
                pbar.update(1)

    except requests.exceptions.RequestException as e:
        print(f"Error retrieving repositories: {str(e)}")

    output_file = f"{repo_name}_migration_results.json"
    with open(output_file, 'w') as f:
        json.dump(migration_results, f, indent=2)
    
    print(f"\nMigration results have been written to {output_file}")

    # Print summary
    successful_settings = sum(1 for setting in migration_results[repo_name].values() if setting['status'] == 'success')
    print(f"\nMigration Summary for {repo_name}:")
    print(f"Total settings processed: 3")
    print(f"Successful migrations: {successful_settings}")
    print(f"Settings with issues: {3 - successful_settings}")

if __name__ == "__main__":
    main()