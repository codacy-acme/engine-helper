import json
import requests
import csv
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

def getIssues(baseurl,provider, organization, apiToken,repository):
    countTotalIssues = 0
    countWarning = 0
    countErrors = 0
    countMinor = 0
    hasNextPage = True
    cursor = ''
    headers = {
                'content-type': 'application/json',
                'accept': 'application/json',
                'api-token': apiToken
            }
    while(hasNextPage):
        url = f'{baseurl}/api/v3/analysis/organizations/{provider}/{organization}/repositories/{repository}/issues/search?limit=100&{cursor}'
        response = requests.post(url, headers=headers)
        time.sleep(1)
        print(response.status_code)
        issues = json.loads(response.text)
        if 'data' in issues:
            for issue in issues['data']:
                if issue['patternInfo']['severityLevel'] == 'Warning':
                    countWarning+=1
                elif issue['patternInfo']['severityLevel'] == 'Error':
                    countErrors+=1
                elif issue['patternInfo']['severityLevel'] == 'Info':
                    countMinor+=1
            hasNextPage = 'cursor' in issues['pagination']
            if hasNextPage:
                cursor = 'cursor=%s' % issues['pagination']['cursor']
        else:
            hasNextPage=False
    countTotalIssues+=countWarning+countErrors+countMinor
    return [countMinor,countWarning,countErrors,countTotalIssues]

def generateReport(baseurl,provider,organization,token):
    tableIssues = open(f'{organization}-issuesReport.csv', 'w')
    writeTableIssues = csv.writer(tableIssues)
    headerTableIssues = ["Repository","Critical","Medium","Minor","Total"]
    writeTableIssues.writerow(headerTableIssues)
    totalIssues = 0
    totalCriticalIssues=0
    totalMediumIssues=0
    totalMinorIssues=0
    repositories = listRepositories(baseurl, provider, organization, token)
    for repo in repositories:
        print("Checking repo", repo['name'])
        countPerRepo = getIssues(baseurl,provider, organization, token,repo['name'])
        totalIssues+=countPerRepo[3]
        totalCriticalIssues+=countPerRepo[2]
        totalMediumIssues+=countPerRepo[1]
        totalMinorIssues+=countPerRepo[0]
        repoInfo = (repo['name'],countPerRepo[2],countPerRepo[1],countPerRepo[0],countPerRepo[3])
        writeTableIssues.writerow(repoInfo)
    issueTotalCount = ["TOTAL",totalCriticalIssues,totalMediumIssues,totalMinorIssues,totalIssues]
    writeTableIssues.writerow(issueTotalCount)
    tableIssues.close()

def main():
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