import argparse
import requests
import json
import re
from bs4 import BeautifulSoup

def readCookieFile():
    with open('auth.cookie', 'r') as myfile:
        data = myfile.read().replace('\n', '')
        return data

def findIntegrationId(baseurl,provider, organization, repo):
    url = '%s/%s/%s/%s/settings/integrations' % (baseurl,provider, organization, repo)
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

def listRepositories(baseurl, provider, organization, token):
    headers = {
        'Accept': 'application/json',
        'api-token': token
    }
    url = '%s/api/v3/organizations/%s/%s/repositories?limit=10000' % (
        baseurl, provider, organization)
    r = requests.get(url, headers=headers)
    repositories = json.loads(r.text)
    return repositories['data']

def enableAllDecorations(baseurl,provider, organization, token,which):
    repositories = listRepositories(baseurl,provider, organization, token)
    allAboard = (which == None)
    targetRepos = []
    if not allAboard:
        targetRepos = which.split(',')
    for repo in repositories:
        if allAboard or repo['name'] in targetRepos:
            enableDecoration(baseurl,provider,organization, repo['name'], repo['repositoryId'])

def enableDecoration(baseurl, provider, organization, repo, repoId, default=''):
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
            "mappings": """[{"notificationType": "GitHubCommitStatus","eventType": "PullRequestDeltaCreated", "integrationId": %s},{"notificationType": "GitHubPullRequestComment","eventType": "PullRequestDeltaCreated", "integrationId": %s},{"notificationType": "GitHubPullRequestSummary","eventType": "PullRequestDeltaCreated", "integrationId": %s},{"notificationType": "GitHubSuggestions", "eventType": "PullRequestDeltaCreated", "integrationId": %s},{"notificationType": "GitHubCoverageSummary","eventType": "CoverageStatusCreated", "integrationId": %s}]""" % (integrationId, integrationId, integrationId, integrationId, integrationId)}
    elif(provider == "bb"):
        data = {
            "mappings": """[{"notificationType":"BitbucketCommitStatus","eventType":"PullRequestDeltaCreated","integrationId":%s},{"notificationType":"BitbucketPullRequestComment","eventType":"PullRequestDeltaCreated","integrationId":%s},{"notificationType":"BitbucketPullRequestSummary","eventType":"PullRequestDeltaCreated","integrationId":%s}]"""% (integrationId, integrationId, integrationId)
        }
    elif(provider == 'ghe'):
        data = {
            "mappings": default.replace('INTEGRATION_PLACEHOLDER', integrationId)
        }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    print(repo,"updated",response.status_code)


def main():
    print('Welcome to Codacy Integration Helper - A temporary solution')
    parser = argparse.ArgumentParser(description='Codacy Integration Helper')
    parser.add_argument('--token', dest='token', default=None,
                        help='the api-token to be used on the REST API')
    parser.add_argument('--reponame', dest='reponame', default=None,
                        help='comma separated list of the repositories to be updated, none means all')
    parser.add_argument('--provider', dest='provider',
                        default=None, help='git provider (gh|gl|bb|ghe|gle|bbe')
    parser.add_argument('--organization', dest='organization',
                        default=None, help='organization name')
    parser.add_argument('--baseurl', dest='baseurl', default='https://app.codacy.com',
                        help='codacy server address (ignore if cloud)')

    args = parser.parse_args()

    enableAllDecorations(args.baseurl,args.provider, args.organization, args.token,args.reponame)


main()