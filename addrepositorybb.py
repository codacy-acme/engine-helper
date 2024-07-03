import argparse
import requests
import json
import time

def listRepositoriesFromBitbucket(workspace, bitbucketToken):
    page = 1
    listRepos = []
    hasNextPage = True
    
    headers = {
        'Authorization': f'Bearer {bitbucketToken}',
        'Accept': 'application/json'
    }
    
    while hasNextPage:
        url = f'https://api.bitbucket.org/2.0/repositories/{workspace}?page={page}'
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Error fetching repositories: {response.status_code}")
            print(response.text)
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

def addAllRepositories(baseurl, provider, organization, token, bitbucketToken, reponame):
    repositories = listRepositoriesFromBitbucket(organization, bitbucketToken)
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
    parser.add_argument('--bitbucketToken', dest='bitbucketToken', default=None,
                        help='the Bitbucket OAuth token')
    parser.add_argument('--reponame', dest='reponame', default=None,
                        help='comma separated list of the repositories to be added, none means all')
    parser.add_argument('--provider', dest='provider',
                        default='bb', help='git provider (should be bb for Bitbucket Cloud)')
    parser.add_argument('--organization', dest='organization',
                        default=None, help='Bitbucket workspace name')
    parser.add_argument('--baseurl', dest='baseurl', default='https://app.codacy.com',
                        help='codacy server address (ignore if cloud)')
    args = parser.parse_args()

    if not args.token or not args.bitbucketToken or not args.organization:
        print("Error: Codacy API token, Bitbucket OAuth token, and organization (workspace) are required.")
        parser.print_help()
        return

    startdate = time.time()
    
    addAllRepositories(args.baseurl, args.provider, args.organization, args.token,
                       args.bitbucketToken, args.reponame)

    enddate = time.time()
    print("\nThe script took", round(enddate-startdate, 2), "seconds")

if __name__ == "__main__":
    main()
