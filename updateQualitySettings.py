import requests
import json
import time
import argparse

def listRepositories(baseurl, provider, organization, token):
    hasNextPage = True
    cursor = ''
    result = []
    headers = {
        'Accept': 'application/json',
        'api-token': token
    }
    while hasNextPage:
        url = '%s/api/v3/organizations/%s/%s/repositories?limit=100&%s' % (
            baseurl, provider, organization,cursor)
        r = requests.get(url, headers=headers)
        repositories = json.loads(r.text)
        for repository in repositories['data']:
            result.append(
                        {
                            'name': repository['name']
                        }
                )
        hasNextPage = 'cursor' in repositories['pagination']
        if hasNextPage:
            cursor = 'cursor=%s' % repositories['pagination']['cursor']
    return result

def updateQualitySettings(provider,orgname,reponame,gitAction,apiToken):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'api-token': apiToken
    }
    data = {
        "issueThreshold": {
        "threshold": 0,
        "minimumSeverity": "Warning"
        },
        "securityIssueThreshold": 0
    }

    response = requests.put(f'https://app.codacy.com/api/v3/organizations/{provider}/{orgname}/repositories/{reponame}/settings/quality/{gitAction}',
            headers = headers,json=data)

    print(gitAction,"-> status:",response.status_code)

def main():
    print('\nWelcome to Codacy!')

    parser = argparse.ArgumentParser(description='Codacy Security Report')

    parser.add_argument('--baseurl', dest='baseurl', default='https://app.codacy.com',
                        help='codacy server address (ignore if you use cloud)')
    parser.add_argument('--provider', dest='provider', default=None,
                        help='git provider (gh|gl|bb|ghe|gle|bbe')
    parser.add_argument('--organization', dest='organization',default=None,
                        help='organization name')
    parser.add_argument('--apiToken', dest='apiToken', default=None,
                        help='the api-token to be used on the REST API')
    parser.add_argument('--reponame', dest='reponame', default=None,
                        help='comma separated list of the repositories to be updated, none means all')
    args = parser.parse_args()

    print("\nScript is running... take a coffee and enjoy!\n")

    startdate = time.time()

    repositories = listRepositories(args.baseurl, args.provider, args.organization, args.apiToken)
    allRepos = (args.reponame == None)
    targetRepos = []
    if not allRepos:
        targetRepos = args.reponame.split(',')
    for repo in repositories:
        if allRepos or repo['name'] in targetRepos:
            print("Updating Quality Settings for PR in",repo['name'])
            #uncomment the following line if you want to update the quality settings for the commits
            #updateQualitySettings(args.provider,args.organization,repo['name'],'commits',args.apiToken)
            updateQualitySettings(args.provider,args.organization,repo['name'],'pull-requests',args.apiToken)

    enddate = time.time()
    print("\nThe script took ",round(enddate-startdate,2)," seconds")


main()