import argparse
import requests
import json
import time

def listRepositoriesfromGithub(orgname,githubToken):
    page = 1
    listRepos = []
    hasNextPage = True
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {githubToken}'
    }
    
    while(hasNextPage):
        url = f'https://api.github.com/orgs/{orgname}/repos?page={page}'
        response = requests.get(url, headers=headers)
        repos = json.loads(response.text) 
        if len(repos) > 0:
            for repo in repos:
                listRepos.append(repo['name'])
            page+=1
        else:
            hasNextPage = False
    return listRepos
    
def addAllRepositories(baseurl,provider, organization, token,githubToken,reponame):
    repositories = listRepositoriesfromGithub(organization,githubToken)
    allAboard = (reponame == None)
    targetRepos = []
    if not allAboard:
        targetRepos = reponame.split(',')
    for repo in repositories:
        if allAboard or repo in targetRepos:
            addRepository(baseurl, provider, organization, repo,token)

def addRepository(baseurl, provider, organization, repo,token):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'api-token': token
    }
    data ={
        "repositoryFullPath": f'{organization}/{repo}',
        "provider": provider
    }
    url = f'{baseurl}/api/v3/repositories'
    response = requests.post(url, headers=headers, data=json.dumps(data))
    print(repo,response.status_code)

def main():
    print('\nWelcome to Codacy Integration Helper - A temporary solution to Add All repositories\n')
    parser = argparse.ArgumentParser(description='Codacy Integration Helper')
    parser.add_argument('--token', dest='token', default=None,
                        help='the api-token to be used on the REST API')
    parser.add_argument('--githubToken', dest='githubToken', default=None,
                        help='the github token to be used on the REST API of Github')
    parser.add_argument('--reponame', dest='reponame', default=None,
                        help='comma separated list of the repositories to be added, none means all')
    parser.add_argument('--provider', dest='provider',
                        default=None, help='git provider (gh|ghe)')
    parser.add_argument('--organization', dest='organization',
                        default=None, help='organization name')
    parser.add_argument('--baseurl', dest='baseurl', default='https://app.codacy.com',
                        help='codacy server address (ignore if cloud)')
    args = parser.parse_args()

    startdate = time.time()
    
    addAllRepositories(args.baseurl,args.provider, args.organization, args.token,args.githubToken,args.reponame)

    enddate = time.time()
    print("\nThe script took ",round(enddate-startdate,2)," seconds")


main()

