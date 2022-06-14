import argparse
import requests
import json
import re
from bs4 import BeautifulSoup
import time

def readCookieFile():
    with open('auth.cookie', 'r') as myfile:
        data = myfile.read().replace('\n', '')
        return data

def findIntegrationId(baseurl, provider, org, repo):
    url = '%s/%s/%s/%s/settings/integrations' % (baseurl, provider, org, repo)
    authority = re.sub('http[s]{0,1}://', '', baseurl)
    headers = {
        'authority': authority,
        'cookie': readCookieFile(),
        'Content-Type': 'application/json'
    }
    response = requests.get(url, headers=headers)
    html_doc = response.text
    soup = BeautifulSoup(html_doc, 'html.parser')
    integrations_view = soup.find(class_="panel panel-default notification-item integration-slack")
    if(integrations_view == None):
        return -1
    else:
        return integrations_view.get('id').replace('notification-','')

def addSlackIntegration(baseurl,repoId):
    authority = re.sub('http[s]{0,1}://', '', baseurl)
    headers = {
        'authority': authority,
        'cookie': readCookieFile(),
        'Content-Type': 'application/json'
    }
    url = '%s/integrations/create/%s/Slack' % (baseurl,repoId)
    data = '{}'
    response = requests.post(url, headers=headers, data=data)
    if(response.status_code > 199 and response.status_code < 300):
        print(f"RepoID: [{str(repoId)}] Slack integrated successfully:",response.status_code)
    else:
        print(f"RepoID [{str(repoId)}] Slack not integrated:",response.status_code)
    return response.status_code

def listRepositories(baseurl, provider, organization, token):
    if token == None:
        raise Exception('api-token needs to be defined')
    headers = {
        'Accept': 'application/json',
        'api-token': token
    }
    url = '%s/api/v3/organizations/%s/%s/repositories?limit=1000' % (
        baseurl, provider, organization)
    r = requests.get(url, headers=headers)
    repositories = json.loads(r.text)
    return repositories['data']

def addSlackAllRepos(baseurl,provider,organization,repositories):
    for repo in repositories:
        if(findIntegrationId(baseurl, provider, organization, repo['name']) == -1):
            addSlackIntegration(baseurl,repo['repositoryId'])
        else:
            print(f"Repository: [{repo['name']}] Slack already integrated")

def enableAllDecorations(baseurl, provider, organization,webhookURL,slackChannel, repositories):
    for repo in repositories:
        if(findIntegrationId(baseurl, provider, organization, repo['name']) != -1):
            enableDecoration(baseurl, provider,organization, repo['name'],repo['repositoryId'], webhookURL,slackChannel)
        else:
            print(f"Repository: [{repo['name']}] Slack integration not created yet")

def enableDecoration(baseurl, provider, organization, repo, repoId, webhookURL,slackChannel):
    integrationId = findIntegrationId(baseurl, provider, organization, repo)
    authority = re.sub('http[s]{0,1}://', '', baseurl)
    headers = {
        'authority': authority,
        'cookie': readCookieFile(),
        'Content-Type': 'application/json'
    }
    url = '%s/integrations/update/%s/%s/?deleteEvents=false' % (baseurl, repoId, integrationId)
    data = '{"webHook":"%s","channel":"%s"}' %(webhookURL,slackChannel)
    response = requests.post(url, headers=headers, data=data)
    if(response.status_code > 299 or response.status_code < 200):
        print(f"Repository: [{repo}] with the ID: [{str(repoId)}] not configured properly:",response.status_code)
    else:
        print(f"Repository: [{repo}] with the ID: [{str(repoId)}] Slack configured!",response.status_code)
    return response.status_code

def main():
    print('\nWelcome to Codacy Integration Helper - A temporary solution to Add Slack integration\n')
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
    parser.add_argument('--slackChannel', dest='slackChannel', default=None,
                        help='Slack Channel')
    parser.add_argument('--webhookURL', dest='webhookURL', default=None,
                        help='Webhook URL from Slack')
    args = parser.parse_args()

    start_time = time.time()

    if(args.which == None and args.repoId == None):
        repositories = listRepositories(args.baseurl, args.provider,args.organization,args.token)
        addSlackAllRepos(args.baseurl, args.provider,args.organization,repositories)
        enableAllDecorations(args.baseurl,args.provider,args.organization,args.webhookURL,args.slackChannel,repositories)
    elif(args.which == None or args.repoId == None):
        print("Did you miss some of the options --which or --repoid?")
    else:
        if(findIntegrationId(args.baseurl,args.provider,args.organization,args.which) == -1):
            integrationStatusCode = addSlackIntegration(args.baseurl,args.repoId)
            if(integrationStatusCode > 199 and integrationStatusCode < 300):
                enableDecoration(args.baseurl, args.provider, args.organization, args.which, args.repoId, args.webhookURL,args.slackChannel)
            else:
                print(f"Repository: [{args.which}] with the ID: [{args.repoId}] wasn't created:",integrationStatusCode)
        else:
            enableDecoration(args.baseurl, args.provider, args.organization, args.which, args.repoId, args.webhookURL,args.slackChannel)

    end_time = time.time()
    print(f"\nThe program has finished in ",round((end_time - start_time),2), " seconds\n")

main()