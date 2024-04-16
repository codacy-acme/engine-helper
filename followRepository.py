import argparse
import requests
import json
import time

def listRepositories(baseurl, provider, organization, token):
    hasNextPage = True
    cursor = ''
    result = []
    headers = {
        'Accept': 'application/json',
        'api-token': token
    }
    while hasNextPage:
        url = f"{baseurl}/api/v3/organizations/{provider}/{organization}/repositories?limit=100&{cursor}"
        response = requests.get(url, headers=headers)
        repositories = response.json()
        for repository in repositories['data']:
            result.append({'name': repository['name']})
        hasNextPage = 'cursor' in repositories['pagination']
        if hasNextPage:
            cursor = f"cursor={repositories['pagination']['cursor']}"
    return result

def followAddedRepository(baseurl, provider, organization, repo, token):
    headers = {
        'Accept': 'application/json',
        'api-token': token
    }
    url = f"{baseurl}/api/v3/organizations/{provider}/{organization}/repositories/{repo}/follow"
    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        print(f"Successfully followed {repo}")
    else:
        print(f"Failed to follow {repo}: {response.status_code}, Response: {response.text}")

def main():
    parser = argparse.ArgumentParser(description='Codacy Repository Auto-Follow')
    parser.add_argument('--token', required=True, help='The API token to be used on the REST API')
    parser.add_argument('--provider', required=True, help='Git provider (gh for GitHub, gl for GitLab, etc.)')
    parser.add_argument('--organization', required=True, help='Organization name')
    parser.add_argument('--baseurl', default='https://app.codacy.com', help='Codacy server address (ignore if cloud)')

    args = parser.parse_args()

    start_time = time.time()
    
    repositories = listRepositories(args.baseurl, args.provider, args.organization, args.token)
    for repo in repositories:
        followAddedRepository(args.baseurl, args.provider, args.organization, repo['name'], args.token)

    end_time = time.time()
    print(f"\nThe script took {round(end_time - start_time, 2)} seconds")

if __name__ == "__main__":
    main()
