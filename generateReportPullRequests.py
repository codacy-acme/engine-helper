import requests
import json
from datetime import timedelta,datetime
import csv
import time
import argparse

def getPRList(baseurl,provider,organization,repository,apiToken,typeOfPR):
    hasNextPage = True
    cursor = ''
    result = []
    currentDate = datetime.strptime(datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"%Y-%m-%d %H:%M:%S")
    headers = {
        'Accept': 'application/json',
        'api-token': apiToken
    }
    while hasNextPage:
        url = '%s/api/v3/analysis/organizations/%s/%s/repositories/%s/pull-requests?search=%s&%s' % (
            baseurl, provider, organization,repository,typeOfPR,cursor)
        response = requests.get(url,headers = headers)
        pullRequests = json.loads(response.text)
        if 'data' in pullRequests:
            for eachPullRequest in pullRequests['data']:
                datePR = datetime.strptime(eachPullRequest['pullRequest']['updated'], "%Y-%m-%dT%H:%M:%SZ")
                if (datePR >= currentDate-timedelta(days=30)):
                    result.append(
                        {
                        'date':eachPullRequest['pullRequest']['updated'],
                        'id':eachPullRequest['pullRequest']['id'],
                        'number':eachPullRequest['pullRequest']['number'],
                        'title':eachPullRequest['pullRequest']['title'],
                        'Author':eachPullRequest['pullRequest']['owner']['name'],
                        'newIssues':eachPullRequest['newIssues'] if 'newIssues' in eachPullRequest else '-',
                        'fixedIssues':eachPullRequest['fixedIssues']if 'fixedIssues' in eachPullRequest else '-',
                        'deltaClonesCount':eachPullRequest['deltaClonesCount'] if 'deltaClonesCount' in eachPullRequest else '-',
                        'deltaComplexity':eachPullRequest['deltaComplexity'] if 'deltaComplexity' in eachPullRequest else '-',
                        'deltaCoverageWithDecimals':eachPullRequest['deltaCoverageWithDecimals'] if 'deltaCoverageWithDecimals' in eachPullRequest else '-',
                        'diffCoverage':eachPullRequest['diffCoverage'] if 'diffCoverage' in eachPullRequest else '-',
                        'typeOfPR': typeOfPR
                        }
                    )
                else:
                    hasNextPage=False
                    break
            hasNextPage = 'cursor' in pullRequests['pagination']
            if hasNextPage:
                cursor = 'cursor=%s' % pullRequests['pagination']['cursor']
        else:
            hasNextPage=False
    return result

def sortByAuthor(e):
    return e['Author']

def generatePRReport(baseurl,provider,organization,repoName,apiToken):
    tablePROverview = open(f'{organization}-PROverview-lastMonth.csv', 'w')
    writeTablePROverview = csv.writer(tablePROverview)
    headerTablePROverview = ["Status","Date","id","number","title","Author","New Issues"
                                                   ,"Fixed Issues","Complexity","Duplication",
                                                   "deltaCoverageWithDecimals","diffCoverage"]
    writeTablePROverview.writerow(headerTablePROverview)
    print("Checking",repoName)
    ## Closed PR's
    PRMergedList = getPRList(baseurl,provider,organization,repoName,apiToken,'merged')
    ## Open PR's
    PROpenList = getPRList(baseurl,provider,organization,repoName,apiToken,'last-updated')
    PRList = PRMergedList+PROpenList
    PRList.sort(key=sortByAuthor)
    for pullrequest in PRList:
        PRRow = ["Open" if pullrequest["typeOfPR"] != 'merged' else "Closed",pullrequest["date"],pullrequest["id"],pullrequest["number"],pullrequest["title"],pullrequest["Author"],
                pullrequest["newIssues"],pullrequest["fixedIssues"],pullrequest["deltaClonesCount"],pullrequest["deltaComplexity"],
                pullrequest["deltaCoverageWithDecimals"],pullrequest["diffCoverage"]]
        writeTablePROverview.writerow(PRRow)
    tablePROverview.close()
    
def main():
    print('Welcome!!\n')
    parser = argparse.ArgumentParser(description='Codacy Integration Helper')
    parser.add_argument('--apiToken', dest='apiToken', default=None,
                        help='the api-token to be used on the REST API')
    parser.add_argument('--provider', dest='provider',
                        default=None, help='git provider (gh|gl|bb|ghe|gle|bbe')
    parser.add_argument('--organization', dest='organization',
                        default=None, help='organization name')
    parser.add_argument('--baseurl', dest='baseurl', default='https://app.codacy.com',
                        help='codacy server address (ignore if cloud)')
    parser.add_argument('--repoName', dest='repoName', default=None,
                        help='Repository you want to gather data from')

    args = parser.parse_args()

    startdate = time.time()
    if args.repoName != None:
        generatePRReport(args.baseurl,args.provider,args.organization,args.repoName,args.apiToken)
    else:
        print("Missing --repoName")

    enddate = time.time()
    print("\nThe script took ",round(enddate-startdate,2)," seconds")


main()