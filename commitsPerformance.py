import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import timedelta,datetime
import csv
import argparse
import time

def readCookieFile():
    with open('auth.cookie', 'r') as myfile:
        data = myfile.read().replace('\n', '')
        return data

def listRepositories(orgid):
    hasNext = True
    pageNumber = 0
    repos = []
    while(hasNext):
        url = 'https://app.codacy.com/admin/organization/%s/projects?pageNumber=%s' % (
            orgid, pageNumber)
        authority = re.sub('http[s]{0,1}://', '', url).split('/')[0]
        headers = {
            'authority': authority,
            'cookie': readCookieFile()
        }
        response = requests.get(url, headers=headers)
        html_doc = response.text
        soup = BeautifulSoup(html_doc, 'html.parser')
        trs = soup.find(class_='new-table').find('tbody').find_all('tr')
        for tr in trs:
            tds = tr.find_all('td')
            if tds[0].text != '\nAccess\nPrivate\n' and tds[0].text != '\nAccess\nPublic\n':
                repo = {
                    'name': tds[1].text
                }
                repos.append(repo)
        hasNext = soup.find(class_='fa-angle-right').parent.name == 'a'
        pageNumber += 1
    return repos

def getCommitsList(baseurl,provider,organization,repository,apiToken,nrdays):
    commitIdList = []
    currentDate = datetime.strptime(datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"%Y-%m-%d %H:%M:%S")
    url = '%s/api/v3/analysis/organizations/%s/%s/repositories/%s/commit-statistics?days=%s' % (
            baseurl, provider, organization,repository,nrdays)
    headers = {
        'Accept': 'application/json',
        'api-token': apiToken
    }
    response = requests.get(url,headers = headers)
    if response.status_code == 200:
        commits = json.loads(response.text)
        for eachCommit in commits['data']:
            dateCommit = datetime.strptime(eachCommit['commitTimestamp'], "%Y-%m-%dT%H:%M:%SZ")
            if (dateCommit >= currentDate-timedelta(days=int(nrdays))):
                commitIdList.append(
                    {
                        'commitID': eachCommit['commitId'],
                        'shortCommitUUID': eachCommit['commitShortUUID'],
                        'commitDate': eachCommit['commitTimestamp'],
                    }
                )
    else:
        print(response.status_code)
    return commitIdList

def getIssuesCount(baseurl,listCommits,provider, organization,repository,apiToken):
    authority = re.sub('http[s]{0,1}://', '', baseurl).split('/')[0]
    headers = {
            'authority': authority,
            'cookie': readCookieFile()
            }
    newIssues = 0
    fixedIssues = 0
    nrCommits = 0
    for eachCommit in listCommits:
        url = '%s/admin?searchQuery=%s' % (
            baseurl, eachCommit['commitID'])
        response = requests.get(url,headers = headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        for a in soup.find_all('li'):
            if a.text[21:31] == eachCommit['shortCommitUUID']:
                issues = getMetrics(baseurl,a.text[21:],provider, organization,repository,apiToken)
                newIssues+=issues[0]
                fixedIssues+=issues[1]
                nrCommits+=1
    return [newIssues, fixedIssues,nrCommits]

def getMetrics(baseurl,commitUUID,provider, organization,repository,apiToken):
    url = '%s/api/v3/analysis/organizations/%s/%s/repositories/%s/commits/%s/deltaStatistics' % (
            baseurl, provider, organization,repository,commitUUID)
    headers = {
        'Accept': 'application/json',
        'api-token': apiToken
    }
    response = requests.get(url,headers = headers)
    if response.status_code == 200:
        commits = json.loads(response.text)
        return [commits['newIssues'],commits['fixedIssues']]
    else:
        print("failed to get metrics")
        return [0,0]

def listIgnoredIssues(provider,organization,repository,apiToken):
    hasNextPage = True
    cursor = ""
    countIgnoredIssues = 0
    while(hasNextPage):
        url = f'https://app.codacy.com/api/v3/analysis/organizations/{provider}/{organization}/repositories/{repository}/ignoredIssues/search?{cursor}'
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'api-token': apiToken
        }
        response = requests.post(url,headers=headers)
        issues = json.loads(response.text)
        countIgnoredIssues+=len(issues['data'])
        hasNextPage = 'cursor' in issues['pagination']
        if hasNextPage:
            cursor = 'cursor=%s' % issues['pagination']['cursor']
    return countIgnoredIssues

def generateReport(baseurl,provider,organization,orgid,apiToken,nrDays):
    totalNewIssues = 0
    totalFixedIssues = 0
    totalIgnoredIssues = 0
    totalCommits = 0
    repositories = listRepositories(orgid)
    file = open(f'{organization}.csv', 'w')
    writer = csv.writer(file)
    data = ["Repository","New Issues","Fixed Issues","Ignored Issues","Number of Commits"]
    writer.writerow(data)
    for repo in repositories:
        print("Checking",repo['name'])
        listCommits = getCommitsList(baseurl,provider,organization,repo['name'],apiToken,nrDays)
        countIssues = getIssuesCount(baseurl,listCommits,provider, organization,repo['name'],apiToken)
        countIgnoredIssues = listIgnoredIssues(provider,organization,repo['name'],apiToken)
        totalIgnoredIssues+=countIgnoredIssues
        totalNewIssues+=countIssues[0]
        totalFixedIssues+=countIssues[1]
        totalCommits+=countIssues[2]
        data = [repo['name'],countIssues[0],countIssues[1],countIgnoredIssues,countIssues[2]]
        writer.writerow(data)
    data = ["TOTAL",totalNewIssues,totalFixedIssues,totalIgnoredIssues,totalCommits]
    writer.writerow(data)
    file.close()

def main():
    print('\nWelcome to Codacy!')

    parser = argparse.ArgumentParser(description='Codacy Security Report')

    parser.add_argument('--baseurl', dest='baseurl', default='https://app.codacy.com',
                        help='codacy server address (ignore if you use cloud)')
    parser.add_argument('--provider', dest='provider', default=None,
                        help='git provider (gh|gl|bb|ghe|gle|bbe')
    parser.add_argument('--organization', dest='organization',default=None,
                        help='organization name')
    parser.add_argument('--orgid', dest='orgid', default=None,
                        help='organization id')
    parser.add_argument('--token', dest='apiToken', default=None,
                        help='the api-token to be used on the REST API')
    parser.add_argument('--days', dest='nrDays', default=31,
                        help='number of days')
    args = parser.parse_args()

    print("\nScript is running... take a coffee and enjoy!\n")

    startdate = time.time()

    generateReport(args.baseurl,args.provider,args.organization,args.orgid,args.apiToken,args.nrDays)

    enddate = time.time()
    print("\nThe script took ",round(enddate-startdate,2)," seconds")


main()