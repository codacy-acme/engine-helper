#!/usr/bin/env python3
import argparse
import requests
from bs4 import BeautifulSoup
import json
import csv
import re
import logging

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

def enableAllSecurityPatternsForOrg(baseurl, provider, org, token):
    repos = listRepositories(baseurl, provider, org, token)
    for repo in repos:
        enableAllSecurityPatternsForRepo(baseurl, provider, org, repo['name'])

def enableAllSecurityPatternsForRepo(baseurl, provider, org, repoName):
    repo_url = '%s/%s/%s/%s/security'%(baseurl, provider, org, repoName)
    authority = re.sub('http[s]{0,1}://','',baseurl)
    headers = {
        'authority': authority,
        'x-requested-with': 'XMLHttpRequest',
        'cookie': readCookieFile(),
        'Content-Type': 'application/json'
    }
    response = requests.get(repo_url, headers=headers)
    page = BeautifulSoup(response.text, 'html.parser')

    rule_ids = listSecurityRulesById(page)
    repo_id = findRepoId(page)
    enablePatterns(baseurl, repo_id, rule_ids)

def enablePatterns(baseurl, repoId, idsToEnable):
    authority = re.sub('http[s]{0,1}://','',baseurl)
    headers = {
        'authority': authority,
        'x-requested-with': 'XMLHttpRequest',
        'cookie': readCookieFile(),
        'Content-Type': 'application/json'
    }
    data = json.dumps({
        "projectId": repoId,
        "patternId": idsToEnable
    })
    print(data)
    response = requests.post('%s/project/addPattern' % (baseurl), headers=headers, data=data)
    print(response)
    print(response.text)

def listSecurityRulesById(page):
    sec_patterns = page.find(class_='on-sec-patterns').get('data-sec-patterns')
    return [pattern for engine in json.loads(sec_patterns) for pattern in engine]

def findRepoId(page):
    return page.find(id='current-repository-id')['value']
    

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

def readCookieFile():
    with open("auth.cookie", "r") as myfile:
        data = myfile.read().replace('\n', '')
        return data

def main():
    print('Codacy Security Rules Auditor')
    parser = argparse.ArgumentParser(description='Codacy Security Rules Auditor')
    parser.add_argument('--token', dest='token', default=None,
                        help='the api-token to be used on the REST API') 
    parser.add_argument('--which', dest='which', default=None,
                        help='repository to be audited, none means all')
    parser.add_argument('--provider', dest='provider',
                        default=None, help='git provider')
    parser.add_argument('--organization', dest='organization',
                        default=None, help='organization id')
    parser.add_argument('--baseurl', dest='baseurl', default='https://app.codacy.com',
                        help='codacy server address (ignore if cloud)')
    args = parser.parse_args()

    enableAllSecurityPatternsForOrg(args.baseurl, args.provider, args.organization, args.token)
    

main()
