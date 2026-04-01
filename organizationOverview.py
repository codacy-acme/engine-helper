import csv
import requests
import json
import sys
import time
from datetime import date
import argparse

#### REPOSITORIES AND LAST UPDATE DATE
def listRepositories(provider, organization, apiToken):
    hasNextPage = True
    cursor = ''
    result = []
    headers = {
        'Accept': 'application/json',
        'api-token': apiToken
    }
    while hasNextPage:
        url = f'https://app.codacy.com/api/v3/organizations/{provider}/{organization}/repositories?limit=100&{cursor}'
        response = requests.get(url, headers=headers, timeout=10)
        repositories = json.loads(response.text)
        for repository in repositories['data']:
            result.append(
                    {
                        'name': repository['name'],
                        'lastUpdated':repository['lastUpdated'] if 'lastUpdated' in repository else "None"
                    }
                )
        hasNextPage = 'cursor' in repositories['pagination']
        if hasNextPage:
            cursor = 'cursor=%s' % repositories['pagination']['cursor']
    return result

#### GRADE AND COVERAGE
def getCoverageGrade(provider, organization, apiToken,repository):
    totalIssues=0
    coveragePercentage=None
    grade=None
    coveragePercentage = None 
    headers = {
                'content-type': 'application/json',
                'accept': 'application/json',
                'api-token': apiToken
            }
    url = f'https://app.codacy.com/api/v3/analysis/organizations/{provider}/{organization}/repositories/{repository}'
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code < 300:
        repository = json.loads(response.text)
        if 'data' in repository:
            grade = repository['data']['gradeLetter'] if 'gradeLetter' in repository['data'] else None
            totalIssues = repository['data']['issuesCount'] if 'issuesCount' in repository['data'] else 0
            if 'coverage' in repository['data']:
                coveragePercentage = repository['data']['coverage']['coveragePercentage'] if 'coveragePercentage' in repository['data']['coverage'] else None
        else:
            print("getCoverageGrade",repository, response.status_code)
    else:
            print("getCoverageGrade",repository, response.status_code)
    return [coveragePercentage,grade,totalIssues]

def writeReport(provider,organization,repositories,apiToken,today):

    repoOverviewTable = open(f'{organization}-OrgOverview-{today}.csv', 'w')
    writeRepoOverviewTable = csv.writer(repoOverviewTable)
    headerRepoOverviewTable = ['Repository', 'Last Updated', 'Coverage', 'Grade', 'Total Issues']
    writeRepoOverviewTable.writerow(headerRepoOverviewTable)
    i = 0
    for repository in repositories:
        i+=1
        print(i,"checking",repository['name'])
        repoOverview = getCoverageGrade(provider, organization, apiToken,repository['name'])
        
        patternRow = [repository['name'],repository['lastUpdated'],
                      repoOverview[0],repoOverview[1],repoOverview[2]] 
        writeRepoOverviewTable.writerow(patternRow)
 
    repoOverviewTable.close()    

def main():
    print('\nWelcome to Codacy Integration Helper - A solution to get the Organization Overview\n')
    parser = argparse.ArgumentParser(description='Codacy Integration Helper')
    parser.add_argument('--apiToken', dest='apiToken', required=True,
                        help='the api-token to be used on the REST API')
    parser.add_argument('--provider', dest='provider', required=True,
                        help='git provider (gh|ghe)')
    parser.add_argument('--organization', dest='organization', required=True,
                        help='organization name')

    args = parser.parse_args()
    
    startdate = time.time()   

    today = date.today()
    
    print("listing the repos...")
    repositories = listRepositories(args.provider, args.organization, args.apiToken)
    
    #create csv with the org report
    print("writing the report...")
    writeReport(args.provider, args.organization, repositories, args.apiToken, today)

    enddate = time.time()
    print("\nThe script took ",round(enddate-startdate,2)," seconds")


main()
