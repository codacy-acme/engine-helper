import argparse
import requests
import json
import time
import base64

def test_bitbucket_auth(workspace, bitbucketUsername, bitbucketAppPassword):
    credentials = f"{bitbucketUsername}:{bitbucketAppPassword}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Accept': 'application/json'
    }
    
    url = f'https://api.bitbucket.org/2.0/workspaces/{workspace}'
    response = requests.get(url, headers=headers)
    
    print(f"Authentication test URL: {url}")
    print(f"Authentication test response status code: {response.status_code}")
    print(f"Authentication test response body: {response.text}")
    
    if response.status_code == 200:
        print("Authentication successful!")
        return True
    else:
        print(f"Authentication failed. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def listRepositoriesFromBitbucket(workspace, bitbucketUsername, bitbucketAppPassword):
    page = 1
    listRepos = []
    hasNextPage = True
    
    credentials = f"{bitbucketUsername}:{bitbucketAppPassword}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Accept': 'application/json'
    }
    
    while hasNextPage:
        url = f'https://api.bitbucket.org/2.0/repositories/{workspace}?page={page}'
        response = requests.get(url, headers=headers)
        
        print(f"Repository list URL: {url}")
        print(f"Repository list response status code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error fetching repositories: {response.status_code}")
            print(f"Response: {response.text}")
            return []
        
        repos = response.json()
        
        if 'values' in repos and len(repos['values']) > 0:
            for repo in repos['values']:
                listRepos.append(repo['slug'])
            page += 1
            hasNextPage = 'next' in repos
        else:
            hasNextPage = False
    
    return listRepos

def addAllRepositories(baseurl, provider, organization, token, bitbucketUsername, bitbucketAppPassword, reponame):
    repositories = listRepositoriesFromBitbucket(organization, bitbucketUsername, bitbucketAppPassword)
    allAboard = (reponame == None)
    targetRepos = []
    if not allAboard:
        targetRepos = reponame.split(',')
    for repo in repositories:
        if allAboard or repo in targetRepos:
            addRepository(baseurl, provider, organization, repo, token)

def addRepository(baseurl, provider, organization, repo, token):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'api-token': token
    }
    data = {
        "repositoryFullPath": f'{organization}/{repo}',
        "provider": provider
    }
    url = f'{baseurl}/api/v3/repositories'
    response = requests.post(url, headers=headers, data=json.dumps(data))
    print(repo, response.status_code)

def main():
    print('\nWelcome to Codacy Integration Helper - A temporary solution to Add All repositories from Bitbucket Cloud\n')
    parser = argparse.ArgumentParser(description='Codacy Integration Helper')
    parser.add_argument('--token', dest='token', default=None,
                        help='the api-token to be used on the Codacy REST API')
    parser.add_argument('--bitbucketUsername', dest='bitbucketUsername', default=None,
                        help='the Bitbucket username')
    parser.add_argument('--bitbucketAppPassword', dest='bitbucketAppPassword', default=None,
                        help='the Bitbucket app password')
    parser.add_argument('--reponame', dest='reponame', default=None,
                        help='comma separated list of the repositories to be added, none means all')
    parser.add_argument('--provider', dest='provider',
                        default='bb', help='git provider (should be bb for Bitbucket Cloud)')
    parser.add_argument('--organization', dest='organization',
                        default=None, help='Bitbucket workspace name')
    parser.add_argument('--baseurl', dest='baseurl', default='https://app.codacy.com',
                        help='codacy server address (ignore if cloud)')
    args = parser.parse_args()

    if not args.token or not args.bitbucketUsername or not args.bitbucketAppPassword or not args.organization:
        print("Error: Codacy API token, Bitbucket username, Bitbucket app password, and organization (workspace) are required.")
        parser.print_help()
        return

    print("Testing Bitbucket authentication...")
    if not test_bitbucket_auth(args.organization, args.bitbucketUsername, args.bitbucketAppPassword):
        print("Authentication test failed. Please check your credentials and try again.")
        return

    startdate = time.time()
    
    addAllRepositories(args.baseurl, args.provider, args.organization, args.token,
                       args.bitbucketUsername, args.bitbucketAppPassword, args.reponame)

    enddate = time.time()
    print("\nThe script took", round(enddate-startdate, 2), "seconds")

if __name__ == "__main__":
    main()
