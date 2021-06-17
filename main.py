#!/usr/bin/env python3
import argparse
import requests
import json
# import logging

# try:
#     import http.client as http_client
# except ImportError:
#     # Python 2
#     import httplib as http_client
# http_client.HTTPConnection.debuglevel = 1
# # You must initialize logging, otherwise you'll not see debug output.
# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True


def listEngines(baseurl):
    url = '%s/api/v3/tools'%baseurl
    r = requests.get(url)
    engines = json.loads(r.text)
    for engine in engines['data']:
        print('[%s] %s'%(engine['uuid'],engine['name']))
    return


#TODO: paginate instead of requesting 10000 repos
def listRepositories(baseurl, provider, organization, token):
    if token == None:
        raise Exception('api-token needs to be defined')
    headers = {
        'Accept': 'application/json',
        'api-token': token
    }
    url = '%s/api/v3/organizations/%s/%s/repositories?limit=10000'%(baseurl,provider, organization)
    r = requests.get(url, headers=headers)
    repositories = json.loads(r.text)
    for repository in repositories['data']:
        print('[%s] %s'%(repository['repositoryId'],repository['name']))
    return repositories['data']

def setUseConfigurationFileForAll(baseurl, provider, organizationId, engineId, use, token):
    repositories = listRepositories(baseurl, provider, organizationId, token)
    for repo in repositories:
        setUseConfigurationFile(baseurl,repo['repositoryId'],engineId, use)
    return

def setUseConfigurationFile(baseurl, repoId, engineId, use):
    headers = {
        'authority': 'app.codacy.com',
        'x-requested-with': 'XMLHttpRequest',
        'cookie': readCookieFile()
    }

    params = (
        ('enable', 'true'),
        ('useConfigurationFile', str(use).lower()),
    )

    data = '{}'

    response = requests.post('%s/p/%s/engine/%s/status'%(baseurl,repoId,engineId), headers=headers, params=params, data=data)
    print(response)

def setToolStatusForAll(baseurl, provider, organizationId, engineId, use, token):
    repositories = listRepositories(baseurl, provider, organizationId, token)
    for repo in repositories:
        setToolStatus(baseurl,repo['repositoryId'],engineId, use)
    return

def setToolStatus(baseurl, repoId, engineId, use):
    headers = {
        'authority': 'app.codacy.com',
        'x-requested-with': 'XMLHttpRequest',
        'cookie': readCookieFile()
    }

    params = (
        ('enable', str(use).lower()),
        ('useConfigurationFile', 'false'),
    )

    data = '{}'

    response = requests.post('%s/p/%s/engine/%s/status'%(baseurl,repoId,engineId), headers=headers, params=params, data=data)
    print(response)

def readCookieFile():
    with open ("auth.cookie", "r") as myfile:
        data=myfile.read().replace('\n', '')
        return data

def main():
    print('Welcome to Codacy Engine Helper - A temporary solution')
    parser = argparse.ArgumentParser(description='Codacy Engine Helper')
    parser.add_argument('--token', dest='token', default=None, help='the api-token to be used on the REST API')
    parser.add_argument('--action', dest="action", default=None, choices=['enableengine', 'disableengine', 'listengines','useconfigurationfile','dontuseconfigurationfile'], help='action to take', required=True)
    parser.add_argument('--which', dest='which', default=None, help='repository to be updated, none means all')
    parser.add_argument('--provider', dest='provider', default=None, help='git provider')
    parser.add_argument('--organization', dest='organization', default=None, help='organization id')
    parser.add_argument('--engine', dest='engine', default=None, help='engine id')
    parser.add_argument('--baseurl', dest='baseurl', default='https://app.codacy.com', help='codacy server address (ignore if cloud)')
    args = parser.parse_args()
    if args.action == 'listengines':
        listEngines(args.baseurl)
    elif args.action == 'useconfigurationfile' or args.action == 'dontuseconfigurationfile':
        if args.engine == None:
            raise Exception('In order to use this command you need to pass the flags --engine and (--organization or --which)')
        if args.which == None:
            if args.organization == None:
                raise Exception('In order to use this command you need to pass the flags --engine and (--organization #### --provider ### or --which ####)')
            setUseConfigurationFileForAll(args.baseurl, args.provider, args.organization, args.engine, args.action == 'useconfigurationfile', args.token)
        else:
            setUseConfigurationFile(args.baseurl, args.which, args.engine, args.action == 'useconfigurationfile')
    elif args.action == 'enableengine' or args.action == 'disableengine':
        if args.engine == None or args.organization == None:
            raise Exception('In order to use this command you need to pass the flags --engine and --organization')
        if args.which == None:
            setToolStatusForAll(args.baseurl, args.provider, args.organization, args.engine, args.action == 'enableengine', args.token)
        else:
            setToolStatus(args.baseurl, args.which, args.engine, args.action == 'enableengine')

main()
