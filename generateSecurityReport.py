import json
import os
import requests
import re
import time
from reportlab.pdfgen import canvas
from bs4 import BeautifulSoup
from datetime import datetime
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
        masterBranch = checkMainBranch(baseurl,provider,organization,repo['name'],apiToken)
        headers = {
                'content-type': 'application/json',
                'api-token': apiToken
                }
        data = {"branchName": masterBranch, "categories": ["Security"]}
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
                print(repository,response.text)
                if failedCurl == 3:
                    hasNextPage = False
                    failedCurl = 0
                else:
                    failedCurl+=1
        with open('./%s/%s.json' % (organization, repository), 'w') as f:
            f.write(json.dumps(tableIssues))

def checkMainBranch(baseurl,provider,orgname,repo,token):
    hasNextPage = True
    cursor = ''
    while(hasNextPage):
        url = f"{baseurl}/api/v3/organizations/{provider}/{orgname}/repositories/{repo}/branches?{cursor}"
        headers = {
            "accept":"application/json",
            "api-token":token
        }
        response = requests.get(url,headers=headers)
        branches = json.loads(response.text)
        for branch in branches['data']:
            if branch['isDefault'] == True:
                return branch['name']
        hasNextPage = 'cursor' in branches['pagination']
        if hasNextPage:
            cursor = 'cursor=%s' % branches['pagination']['cursor']

def writeSecurityReportPDF(path_to_repos,json_files_repos,organization):
    countTotalSecurityIssues = 0
    reportPDF = canvas.Canvas(f'{organization}-securityReport.pdf')
    y = 800
    reportPDF.setFont('Helvetica-Bold', 20)
    reportPDF.drawString(200, y, f"Security Report - {datetime.today().strftime('%d-%m-%Y')}")
    for jsonFile in json_files_repos:
        tableSecIssues = []
        countSecurityIssues = 0
        countWarning = 0
        countErrors = 0
        countMinor = 0
        issues = json.load(open('%s%s' %(path_to_repos,jsonFile)))
        reportPDF.setFont('Helvetica-Bold', 15)
        y-=20
        reportPDF.drawString(5, y, f'Repository: {jsonFile[:-5]}')
        reportPDF.setFont('Helvetica', 14)
        for issue in issues:
            countWarning = countWarning+1 if issue['severityLevel'] == 'Warning' else countWarning
            countErrors = countErrors+1 if issue['severityLevel'] == 'Error' else countErrors
            countMinor = countMinor+1 if issue['severityLevel'] == 'Info' else countMinor
            countSecurityIssues+=1
            if issue['id'] not in tableSecIssues:
                tableSecIssues.append(issue['id'])
                y-=20
                reportPDF.drawString(5, y, f"Pattern: {issue['id']}")
                if y-20 < 100:
                    reportPDF.showPage()
                    y = 800
                    reportPDF.setFont('Helvetica', 14)
        countTotalSecurityIssues+=countSecurityIssues
        y-=20
        reportPDF.drawString(5, y, f'Critical: {countErrors} - Medium: {countWarning} - Minor: {countMinor}')
        y-=20
        reportPDF.drawString(5, y, f'Count of security issues: {countSecurityIssues}')
        if y-20 < 100:
            reportPDF.showPage()
            y = 800
        else:
            y-=20
    reportPDF.setFont('Helvetica-Bold', 15)
    y-=30
    reportPDF.drawString(5, y, f'Total security issues of organization: {countTotalSecurityIssues}')
    reportPDF.save()

def writeSecurityReportXLSX(path_to_repos,json_files_repos,organization):
    countTotalSecurityIssues = 0
    workbook = xlsxwriter.Workbook(f'./{organization}-securityReport.xlsx')
    worksheet = workbook.add_worksheet('CountSecurityIssues')
    worksheet2 = workbook.add_worksheet('listSecurityIssues')
    header_format = workbook.add_format()
    header_format.set_align('center')
    header_format.set_bold()
    listFormat = workbook.add_format()
    listFormat.set_align('center')
    rowSheet1 = 0
    rowSheet2 = 0
    header = ('Repository', 'Critical', 'Medium', 'Minor','Total')
    header2 = ('Repository', 'Issue','Severity')
    worksheet.write_row(rowSheet1,0,header,header_format)
    worksheet2.write_row(rowSheet2,0,header2,header_format)
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
    worksheet.write(rowSheet1+1, 4, countTotalSecurityIssues,listFormat)
    workbook.close()

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
    parser.add_argument('--token', dest='token', default=None,
                        help='the api-token to be used on the REST API')
    parser.add_argument('--format', dest='fileFormat', default=None,
                        help='the format of the report: pdf or xlsx')
    args = parser.parse_args()

    print("\nScript is running... take a coffee and enjoy!\n")

    startdate = time.time()

    if args.fileFormat.lower() not in ['pdf','xlsx']:
        print("Wrong format. Use PDF or XLSX")
        return
    else:
        if not os.path.exists(f'./{args.organization}'):
            os.makedirs(f'./{args.organization}')
        getIssues(args.baseurl,args.provider,args.organization,args.token,args.orgid)
        path_to_repos = f'{args.organization}/'
        json_files_repos = [pos_json for pos_json in os.listdir(path_to_repos) if pos_json.endswith('.json')]

    if args.fileFormat.lower() == 'pdf':
        writeSecurityReportPDF(path_to_repos,json_files_repos,args.organization)
    else:
        writeSecurityReportXLSX(path_to_repos,json_files_repos,args.organization)

    enddate = time.time()
    print("The script took ",round(enddate-startdate,2)," seconds")


main()