import json
import os
import requests
import re
import time
from bs4 import BeautifulSoup
import xlsxwriter
import argparse

def readCookieFile():
    with open('auth.cookie', 'r') as myfile:
        data = myfile.read().replace('\n', '')
        return data

def listRepositories(baseurl,orgid):
    hasNext = True
    pageNumber = 0
    repos = []
    while(hasNext):
        url = '%s/admin/organization/%s/projects?pageNumber=%s' % (
            baseurl,orgid, pageNumber)
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

def getIssues(baseurl,provider, organization, apiToken,orgid):
    failedCurl = 0
    repositories = listRepositories(baseurl,orgid)
    for repo in repositories:
        hasNextPage = True
        cursor = ''
        tableIssues = []
        repository = repo['name']
        print('Checking issues on the repo',repo['name'])
        headers = {
                'content-type': 'application/json',
                'accept': 'application/json',
                'api-token': apiToken
                }
        data = {"categories": ["Security"]}
        while(hasNextPage):
            url = f'{baseurl}/api/v3/analysis/organizations/{provider}/{organization}/repositories/{repository}/issues/search?limit=100&{cursor}'
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                secIssues = json.loads(response.text)
                for issue in secIssues['data']:
                    tableIssues.append(
                        {
                            'id': issue['patternInfo']['id'],
                            'category': issue['patternInfo']['category'],
                            'severityLevel': issue['patternInfo']['severityLevel'],
                            'message': issue['message']
                        }
                    )
                if 'pagination' in secIssues:
                    hasNextPage = 'cursor' in secIssues['pagination']
                    if hasNextPage:
                        cursor = 'cursor=%s' %secIssues['pagination']['cursor']
                else:
                    hasNextPage = False
            else:
                print(response.text)
                if failedCurl == 3:
                    hasNextPage = False
                    failedCurl = 0
                else:
                    failedCurl+=1
        with open('./%s/%s.json' % (organization, repository), 'w') as f:
            f.write(json.dumps(tableIssues))

def getOrgs(baseurl,token):
    hasNextPage = True
    cursor = ''
    listOrgs = []
    while(hasNextPage):
        url = f"{baseurl}/api/v3/user/organizations?{cursor}"
        headers = {
            "accept":"application/json",
            "api-token":token
        }
        response = requests.get(url,headers=headers)
        orgs = json.loads(response.text)
        for org in orgs['data']:
            listOrgs.append(
                        {
                            'name': org['name'],
                            'provider': org['provider'],
                            'identifier': org['identifier']
                        }
                    )
        hasNextPage = 'cursor' in orgs['pagination']
        if hasNextPage:
            cursor = 'cursor=%s' % orgs['pagination']['cursor']
    return listOrgs

def writeSecurityReport(orgs,baseurl,token):
    allOrgs = (orgs == None)
    if not allOrgs:
        targetOrgs = orgs.split(',')
    list_Orgs = getOrgs(baseurl,token)
    workbook = xlsxwriter.Workbook('./securityReport.xlsx')
    worksheet = workbook.add_worksheet('CountSecurityIssues')
    worksheet2 = workbook.add_worksheet('listSecurityIssues')
    header_format = workbook.add_format()
    header_format.set_align('center')
    header_format.set_bold()
    listFormat = workbook.add_format()
    listFormat.set_align('center')
    rowSheet1 = 0
    rowSheet2 = 0
    for org in list_Orgs:
        if allOrgs or org['name'] in targetOrgs:
            orgname = org['name']
            if not os.path.exists(f'./{orgname}'):
                os.makedirs(f'./{orgname}')
            getIssues(baseurl,org['provider'],org['name'],token,org['identifier'])
            path_to_repos = f'{orgname}/'
            json_files_repos = [pos_json for pos_json in os.listdir(path_to_repos) if pos_json.endswith('.json')]
            countTotalSecurityIssues = 0
            orgHeader = ('ORGANIZATION',org['name'])
            issueHeader = ('Repository', 'Issue','Severity')
            repoHeader = ('Repository', 'Critical', 'Medium', 'Minor','Total')
            worksheet.write_row(rowSheet1,0,orgHeader,header_format)
            worksheet2.write_row(rowSheet2,0,orgHeader,header_format)
            rowSheet1+=1
            rowSheet2+=1
            worksheet.write_row(rowSheet1,0,repoHeader,header_format)
            worksheet2.write_row(rowSheet2,0,issueHeader,header_format)
            rowSheet2+=1
            for jsonFile in json_files_repos:
                tableSecIssues = []
                countSecurityIssues = 0
                countWarning = 0
                countErrors = 0
                countMinor = 0
                issues = json.load(open('%s%s' %(path_to_repos,jsonFile)))
                worksheet2.write(rowSheet2, 0, jsonFile[0:-5],listFormat)
                for issue in issues:
                    countWarning = countWarning+1 if issue['severityLevel'] == 'Warning' else countWarning
                    countErrors = countErrors+1 if issue['severityLevel'] == 'Error' else countErrors
                    countMinor = countMinor+1 if issue['severityLevel'] == 'Info' else countMinor
                    countSecurityIssues+=1
                    if issue['message'] not in tableSecIssues:
                        tableSecIssues.append(issue['message'])
                        worksheet2.write(rowSheet2, 1, issue['message'],listFormat)
                        worksheet2.write(rowSheet2, 2, issue['severityLevel'],listFormat)
                        rowSheet2+=1
                countTotalSecurityIssues+=countSecurityIssues
                rowSheet1+=1
                secInfo = (jsonFile[0:-5],countErrors,countWarning,countMinor,countSecurityIssues)
                worksheet.write_row(rowSheet1,0,secInfo,listFormat)
            rowSheet1+=1
            worksheet.write(rowSheet1, 4, countTotalSecurityIssues,listFormat)
            rowSheet1+=1
    workbook.close()

def main():
    print('\nWelcome to Codacy!')

    parser = argparse.ArgumentParser(description='Codacy Security Report')

    parser.add_argument('--baseurl', dest='baseurl', default='https://app.codacy.com',
                        help='codacy server address (ignore if you use cloud)')
    parser.add_argument('--token', dest='token', default=None,
                        help='the api-token to be used on the REST API')
    parser.add_argument('--orgname', dest='orgname', default=None,
                        help='comma separated list of the organizations, none means all')
    args = parser.parse_args()

    print("\nScript is running... take a coffee and enjoy!\n")

    startdate = time.time()

    writeSecurityReport(args.orgname,args.baseurl,args.token)

    enddate = time.time()
    print("The script took ",round(enddate-startdate,2)," seconds")


main()
