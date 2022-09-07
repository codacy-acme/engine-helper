import requests
import bs4
import re
import time
import argparse

def readCookieFile():
    with open('auth.cookie', 'r') as myfile:
        data = myfile.read().replace('\n', '')
        return data

def listRepositories(orgname):
    hasNext = True
    pageNumber = 0
    repos = []
    while(hasNext):
        url = 'https://app.codacy.com/admin/organization/%s/projects?pageNumber=%s' % (
            orgname, pageNumber)
        authority = re.sub('http[s]{0,1}://', '', url).split('/')[0]
        headers = {
            'authority': authority,
            'cookie': readCookieFile()
        }
        response = requests.get(url, headers=headers)
        html_doc = response.text
        soup = bs4.BeautifulSoup(html_doc, 'html.parser')
        trs = soup.find(class_='new-table').find('tbody').find_all('tr')
        for tr in trs:
            tds = tr.find_all('td')
            if tds[0].text != '\nAccess\nPrivate\n' and tds[0].text != '\nAccess\nPublic\n':
                repo = {
                    'id': tds[0].text,
                    'name': tds[1].text
                }
                repos.append(repo)
        hasNext = soup.find(class_='fa-angle-right').parent.name == 'a'
        pageNumber += 1
    return repos

def updateQualitySettings(provider,orgname,reponame,gitAction,apiToken):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'api-token': apiToken
    }
    data = {
        "issueThreshold": {
        "threshold": 0,
        "minimumSeverity": "Warning"
        },
        "securityIssueThreshold": 0
    }

    response = requests.put(f'https://app.codacy.com/api/v3/organizations/{provider}/{orgname}/repositories/{reponame}/settings/quality/{gitAction}',
            headers = headers,json=data)

    print(gitAction,"-> status:",response.status_code)

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
    parser.add_argument('--reponame', dest='reponame', default=None,
                        help='comma separated list of the repositories to be updated, none means all')
    args = parser.parse_args()

    print("\nScript is running... take a coffee and enjoy!\n")

    startdate = time.time()

    repositories = listRepositories(args.orgid)
    allRepos = (args.reponame == None)
    targetRepos = []
    if not allRepos:
        targetRepos = args.reponame.split(',')
    for repo in repositories:
        if allRepos or repo['name'] in targetRepos:
            print("Updating Quality Settings for PR in",repo['name'])
            #uncomment the following line if you want to update the quality settings for the commits
            #updateQualitySettings(args.provider,args.organization,repo['name'],'commits',args.apiToken)
            updateQualitySettings(args.provider,args.organization,repo['name'],'pull-requests',args.apiToken)

    enddate = time.time()
    print("\nThe script took ",round(enddate-startdate,2)," seconds")


main()