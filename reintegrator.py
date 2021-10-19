#!/usr/bin/env python3
import argparse
import requests
import json
import re
from bs4 import BeautifulSoup
import webbrowser
import time


providers = {
    'gh': 'GitHub',
    'gl': 'GitLab',
    'bb': 'BitBucket',
    'ghe': 'GitHubEnterprise',
    'gle': 'GitLabEnterprise',
    'bbe': 'Stash'


}


def readCookieFile():
    with open('auth.cookie', 'r') as myfile:
        data = myfile.read().replace('\n', '')
        return data


# integration-github
# integration-gitlab
# integration-bitbucket
# integration-github-enterprise
# integration-gitlab-enterprise
# integration-stash

def findIntegrationId(baseurl, provider, org, repo):
    #url = '%s/p/%s/settings/integrations' % (baseurl, repoId)
    url = '%s/%s/%s/%s/settings/integrations' % (baseurl, provider, org, repo)
    authority = re.sub('http[s]{0,1}://', '', baseurl)
    headers = {
        'authority': authority,
        'x-requested-with': 'XMLHttpRequest',
        'cookie': readCookieFile(),
        'Content-Type': 'application/json'
    }
    response = requests.get(url, headers=headers)
    html_doc = response.text
    soup = BeautifulSoup(html_doc, 'html.parser')
    integrations_view = soup.find(id='IntegrationsView')
    gp_integration = integrations_view.find(class_=re.compile(
        'integration-(github|gitlab|bitbucket|github-enterprise|gitlab-enterprise|stash)'))
    if(gp_integration == None):
        return -1
    else:
        return gp_integration.get('id').replace('notification-', '')


def addIntegration(baseurl, repoId, provider):
    authority = re.sub('http[s]{0,1}://', '', baseurl)
    headers = {
        'authority': authority,
        'x-requested-with': 'XMLHttpRequest',
        'cookie': readCookieFile(),
        'Content-Type': 'application/json'
    }
    url = '%s/integrations/create/%s/%s' % (baseurl,
                                            repoId, providers[provider])
    data = '{}'
    response = requests.post(url, headers=headers, data=data)
    print(response)


def deleteIntegration(baseurl, repoId, integrationId):
    authority = re.sub('http[s]{0,1}://', '', baseurl)
    headers = {
        'authority': authority,
        'x-requested-with': 'XMLHttpRequest',
        'cookie': readCookieFile(),
        'Content-Type': 'application/json'
    }
    url = '%s/integrations/delete/%s/%s' % (baseurl, repoId, integrationId)
    data = '{}'
    response = requests.post(url, headers=headers, data=data)
    print(response)


def enableIntegration(baseurl, repoId, provider):
    url = '%s/add/addService/redirect/%s/%s' % (baseurl, provider, repoId)
    #print(url)
    #chrome_path = 'open -a /Applications/Google\ Chrome.app %s'
    #webbrowser.get(chrome_path).open(url, new=2)
    webbrowser.open(url, new=2)
    # sleep for browser time
    time.sleep(1)


def reintegrate(baseurl, provider, organization, repository, repoId):
    integrationId = findIntegrationId(
        baseurl, provider, organization, repository)
    if integrationId != -1:
        deleteIntegration(baseurl, repoId, integrationId)
    addIntegration(baseurl, repoId, provider)
    if(provider == 'gh'):
        providerEnable = 'GithubReadOnly'
    else:
        providerEnable = providers[provider]
    enableIntegration(baseurl, repoId, providerEnable)


def reintegrateAll(baseurl, provider, organization, token):
    repositories = listRepositories(baseurl, provider, organization, token)
    for repo in repositories:
        reintegrate(baseurl, provider, organization,
                    repo['name'], repo['repositoryId'])
        enableDecoration(baseurl, provider,
                         organization, repo['name'], repo['repositoryId'])


# TODO: paginate instead of requesting 10000 repos
def listRepositories(baseurl, provider, organization, token):
    if token == None:
        raise Exception('api-token needs to be defined')
    headers = {
        'Accept': 'application/json',
        'api-token': token
    }
    url = '%s/api/v3/organizations/%s/%s/repositories?limit=10000' % (
        baseurl, provider, organization)
    r = requests.get(url, headers=headers)
    repositories = json.loads(r.text)
    return repositories['data']


def enableAllDecorations(baseurl, provider, organization, token):
    repositories = listRepositories(baseurl, provider, organization, token)
    for repo in repositories:
        enableDecoration(baseurl, repo['repositoryId'], providers[provider])


def enableDecoration(baseurl, provider, organization, repo, repoId):
    integrationId = findIntegrationId(baseurl, provider, organization, repo)
    authority = re.sub('http[s]{0,1}://', '', baseurl)
    headers = {
        'authority': authority,
        'x-requested-with': 'XMLHttpRequest',
        'cookie': readCookieFile(),
        'Content-Type': 'application/json'
    }
    url = '%s/integrations/update/%s/%s/' % (baseurl, repoId, integrationId)
    data = '{}'
    if(provider == 'gle'):
        data = {
            "mappings": """[{\"notificationType\":\"GitLabCommitStatus\",\"eventType\":\"PullRequestDeltaCreated\",\"integrationId\":%s},{\"notificationType\":\"GitLabPullRequestComment\",\"eventType\":\"PullRequestDeltaCreated\",\"integrationId\":%s},{\"notificationType\":\"GitLabPullRequestSummary\",\"eventType\":\"PullRequestDeltaCreated\",\"integrationId\":%s}]"""%(integrationId, integrationId, integrationId)
        }
    elif(provider == "gh"):
        data = {
            "mappings": """[{"notificationType": "GitHubCommitStatus","eventType": "PullRequestDeltaCreated", "integrationId": %s},{"notificationType": "GitHubPullRequestComment","eventType": "PullRequestDeltaCreated", "integrationId": %s},{"notificationType": "GitHubPullRequestSummary","eventType": "PullRequestDeltaCreated", "integrationId": %s},{"notificationType": "GitHubSuggestions", "eventType": "PullRequestDeltaCreated", "integrationId": %s}]""" % (integrationId, integrationId, integrationId, integrationId)}

    response = requests.post(url, headers=headers, data=json.dumps(data))
    print(response.text)


def main():
    print('Welcome to Codacy Integration Helper - A temporary solution')
    parser = argparse.ArgumentParser(description='Codacy Integration Helper')
    parser.add_argument('--token', dest='token', default=None,
                        help='the api-token to be used on the REST API')
    parser.add_argument('--which', dest='which', default=None,
                        help='repository to be updated, none means all')
    parser.add_argument('--provider', dest='provider',
                        default=None, help='git provider (gh|gl|bb|ghe|gle|bbe')
    parser.add_argument('--organization', dest='organization',
                        default=None, help='organization id')
    parser.add_argument('--baseurl', dest='baseurl', default='https://app.codacy.com',
                        help='codacy server address (ignore if cloud)')
    parser.add_argument('--repoid', dest='repoId', default=None,
                        help='Repository numeric id')
    args = parser.parse_args()
    if args.which == None:
        reintegrateAll(args.baseurl, args.provider,
                       args.organization, args.token)
    else:
        reintegrate(args.baseurl, args.provider,
                    args.organization, args.which, args.repoId)
        enableDecoration(args.baseurl, args.provider,
                         args.organization, args.which, args.repoId)


main()
