import argparse
import requests
import json
import time

def fetchRepositories(baseurl, provider, organization, token):
    """Fetch a list of all repositories in the organization that can be followed.
    
    Args:
        baseurl (str): The base URL for the Codacy API.
        provider (str): The git provider (e.g., 'gh' for GitHub, 'gl' for GitLab).
        organization (str): The organization name.
        token (str): The API token for Codacy.
        
    Returns:
        list: A list of repository names.
    """
    headers = {
        'Accept': 'application/json',
        'api-token': token
    }
    url = f'{baseurl}/api/v3/organizations/{provider}/{organization}/repositories'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        repositories = response.json()
        # Assuming each repository info is contained in a dict with a 'name' key
        return [repo['name'] for repo in repositories['data']]  # Adjust based on actual response structure
    else:
        print(f'Failed to fetch repositories: {response.status_code}, Response: {response.text}')
        return []

def followAddedRepository(baseurl, provider, organization, repo, token):
    """Follow a repository that was already added to Codacy.
    
    Args:
        baseurl (str): The base URL for the Codacy API.
        provider (str): The git provider (e.g., 'gh' for GitHub, 'gl' for GitLab).
        organization (str): The organization name.
        repo (str): The repository name to be followed.
        token (str): The API token for Codacy.
    """
    headers = {
        'Accept': 'application/json',
        'api-token': token
    }
    url = f'{baseurl}/api/v3/organizations/{provider}/{organization}/repositories/{repo}/follow'
    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        print(f'Successfully followed {repo}')
    else:
        print(f'Failed to follow {repo}: {response.status_code}, Response: {response.text}')

def main():
    parser = argparse.ArgumentParser(description='Codacy Repository Auto-Follow')
    parser.add_argument('--token', required=True, help='The API token to be used on the REST API')
    parser.add_argument('--provider', required=True, help='Git provider (gh for GitHub, gl for GitLab, etc.)')
    parser.add_argument('--organization', required=True, help='Organization name')
    parser.add_argument('--baseurl', default='https://app.codacy.com', help='Codacy server address (ignore if cloud)')

    args = parser.parse_args()

    start_time = time.time()
    
    repositories = fetchRepositories(args.baseurl, args.provider, args.organization, args.token)
    for repo in repositories:
        followAddedRepository(args.baseurl, args.provider, args.organization, repo, args.token)

    end_time = time.time()
    print(f"\nThe script took {round(end_time - start_time, 2)} seconds")

if __name__ == "__main__":
    main()
