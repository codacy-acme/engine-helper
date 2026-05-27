import requests
import json
import time
import argparse

def createWebhookAllRepositories(provider, organization, token):
    hasNextPage = True
    cursor = ''
    headers = {
        'Accept': 'application/json',
        'api-token': token
    }
    
    while hasNextPage:
        url = f'https://app.codacy.com/api/v3/organizations/{provider}/{organization}/repositories?{cursor}'
        r = requests.get(url, headers=headers, timeout=10)
        repositories = json.loads(r.text)
        
        for repository in repositories['data']:
            createWebhook(provider, organization, repository['name'], token)
        
        hasNextPage = 'cursor' in repositories['pagination']
        if hasNextPage:
            cursor = 'cursor=%s' % repositories['pagination']['cursor']

def createWebhook(provider, organization, repositoryName, token):
    headers = {
        'Accept': 'application/json',
        'api-token': token
    }
    url = f'https://app.codacy.com/api/v3/organizations/{provider}/{organization}/repositories/{repositoryName}/integrations/postCommitHook'
    r = requests.get(url, headers = headers, timeout=10)

    print(repositoryName, r.status_code)

def main():
    print('Welcome to Codacy Integration Helper - A temporary solution')
    parser = argparse.ArgumentParser(description='Codacy Integration Helper')
    parser.add_argument('--apiToken', dest='apiToken', required=True,
                        help='the api-token to be used on the REST API')
    parser.add_argument('--provider', dest='provider', required=True,
                        help='provider (gh,bb,gl)')
    parser.add_argument('--organization', dest='organization', required=True,
                        help='organization name')
    parser.add_argument(
        '--which',
        dest='which',
        default=None,
        help='Comma-separated list of repositories to reintegrate (default: all)')

    args = parser.parse_args()

    startdate = time.time()

    target_repositories = None
    if args.which:
        target_repositories = [repo.strip() for repo in args.which.split(',')]
        for repository in target_repositories:
            createWebhook(args.provider, args.organization, repository, args.apiToken)
    else:
        createWebhookAllRepositories(args.provider, args.organization, args.apiToken)

    enddate = time.time()
    print("\nThe script took ",round(enddate-startdate,2)," seconds")

if __name__ == "__main__":
    main()
