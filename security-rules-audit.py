#!/usr/bin/env python3
import argparse
import requests
from bs4 import BeautifulSoup
import json
import re
import logging

# try:
#     import http.client as http_client
# except ImportError:
#     # Python 2
#     import httplib as http_client
# http_client.HTTPConnection.debuglevel = 1
# # You must initialize logging, otherwise you'll not see debug output.
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True

def getSecurityPatternsForRepo(baseurl, provider, org, repoName):
    available_tools = findToolsForRepo(baseurl, provider, org, repoName)
    available_patterns = []

    for tool in available_tools:
        authority = re.sub('http[s]{0,1}://','',baseurl)
        headers = {
            'authority': authority,
            'x-requested-with': 'XMLHttpRequest',
            'cookie': readCookieFile(),
            'Content-Type': 'application/json'
        }
        response = requests.get(baseurl + tool['url'], headers=headers)
        page = BeautifulSoup(response.text, 'html.parser')
        pattern_items = page.find_all(class_='pattern-item')
        
        for item in pattern_items:
            category = item.find(class_='pattern-category').get_text() if item.find(class_='pattern-category') else ''
            if category == 'Security':
                name = item.find(class_='pattern-header').h5.get_text().strip()
                enabled = 'checked' in item.input.attrs if item.input != None else False
                available_patterns.append({"tool": tool['name'], "name": name, "enabled": enabled})

    return available_patterns

def findToolsForRepo(baseurl, provider, org, repoName):
    repo_url = '%s/%s/%s/%s/patterns/list'%(baseurl, provider, org, repoName)
    authority = re.sub('http[s]{0,1}://','',baseurl)
    headers = {
        'authority': authority,
        'x-requested-with': 'XMLHttpRequest',
        'cookie': readCookieFile(),
        'Content-Type': 'application/json'
    }
    response = requests.get(repo_url, headers=headers)
    html_doc = response.text
    soup = BeautifulSoup(html_doc, 'html.parser')
    tools_panel = soup.find(id='tools-panel')
    list_items = tools_panel.find_all(class_='list-group-item')

    available_tools = []
    for item in list_items:
        name = item.find(class_='tool').get_text().split('\n')[0].strip()
        tool_url = item.a.get('href') if item.a != None else findDefaultToolURL(item)
        enabled = 'checked' in item.input.attrs if item.input != None else False
        available_tools.append({'name': name, 'url': tool_url, 'enabled': enabled})

    return available_tools

def findDefaultToolURL(tool_item):
    data_url = tool_item.input.get('data-url')
    repo_id = data_url.split('/')[1]
    tool_id = data_url.split('/')[3]
    print('/p/%s/patterns/list?engine=%s'%(repo_id, tool_id))
    return '/p/%s/patterns/list?engine=%s'%(repo_id, tool_id)

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
    print(url)
    r = requests.get(url, headers=headers)
    repositories = json.loads(r.text)
    for repository in repositories['data']:
        print('[%s] %s' % (repository['repositoryId'], repository['name']))
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

    report = getSecurityPatternsForRepo(args.baseurl, args.provider, args.organization, args.which)

    for pattern in report:
        print(pattern)

    # findToolsForRepo(args.baseurl, args.provider, args.organization, args.which)

main()
