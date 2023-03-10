import requests
import json
from datetime import timedelta,datetime,date
import csv
import time
from dateutil.relativedelta import relativedelta
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
                            'name': repository['name'],
                        }
                )
        hasNextPage = 'cursor' in repositories['pagination']
        if hasNextPage:
            cursor = 'cursor=%s' % repositories['pagination']['cursor']
    return result

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
    commits = json.loads(response.text)
    for eachCommit in commits['data']:
        dateCommit = datetime.strptime(eachCommit['commitTimestamp'], "%Y-%m-%dT%H:%M:%SZ")
        if (dateCommit >= currentDate-timedelta(days=int(nrdays))):
            if 'coveragePercentageWithDecimals' in eachCommit:
                commitIdList.append(
                    {
                    eachCommit['coveragePercentageWithDecimals']
                    }
                )
    return commitIdList

def generateReport(baseurl,provider,organization,apiToken):
    repositories = listRepositories(baseurl, provider, organization, apiToken)
    tableCoverageOverview = open(f'{organization}-coverageOverview.csv', 'w')
    writeTableCoverageOverview = csv.writer(tableCoverageOverview)
    headerTableCoverageOverview = ["Repository","Current","Intermediate","3 months"]
    writeTableCoverageOverview.writerow(headerTableCoverageOverview)
    for repo in repositories:
        print("Checking",repo['name'])
        commitsList = getCommitsList(baseurl,provider,organization,repo['name'],apiToken,90)
        if len(commitsList)>0:
            middleIndex = (len(commitsList) - 1)/2
            coverageRow = [repo['name'],str(commitsList[0])[1:-1]+"%",str(commitsList[int(middleIndex)])[1:-1]+"%",str(commitsList[-1])[1:-1]+"%"] 
            writeTableCoverageOverview.writerow(coverageRow)
        else:
            coverageRow = [repo['name'],"-","-","-"] 
            writeTableCoverageOverview.writerow(coverageRow)
    tableCoverageOverview.close()
   
def main():
    print('Welcome to Codacy Integration Helper - A temporary solution')
    parser = argparse.ArgumentParser(description='Codacy Integration Helper')
    parser.add_argument('--apiToken', dest='apiToken', default=None,
                        help='the api-token to be used on the REST API')
    parser.add_argument('--provider', dest='provider',
                        default=None, help='git provider (gh|gl|bb|ghe|gle|bbe')
    parser.add_argument('--organization', dest='organization',
                        default=None, help='organization name')
    parser.add_argument('--baseurl', dest='baseurl', default='https://app.codacy.com',
                        help='codacy server address (ignore if cloud)')

    args = parser.parse_args()

    startdate = time.time()

    generateReport(args.baseurl,args.provider,args.organization,args.apiToken)

    enddate = time.time()
    print("\nThe script took ",round(enddate-startdate,2)," seconds")


main()