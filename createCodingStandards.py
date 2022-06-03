import requests
import json
import re
import time
import argparse

def createDraft(baseurl,provider, organization,token,languages):
    codingID = getCodingStandardId(baseurl,provider,organization,token,False)
    authority = re.sub('http[s]{0,1}://', '', baseurl)
    headers = {
        'authority': authority,
        'x-requested-with': 'XMLHttpRequest',
        'Content-Type': 'application/json',
        'api-token': token
    }
    url = f'{baseurl}/api/v3/organizations/{provider}/{organization}/coding-standards?sourceCodingStandard={codingID}'
    data = '{"name":"defaultCodingStandard","languages": %s}' % (languages)
    createDraft = requests.post(url, headers=headers,data=data)
    return createDraft.status_code

def createCodingStandard(baseurl,provider, organization,token,languages,repo):
    authority = re.sub('http[s]{0,1}://', '', baseurl)
    headers = {
        'authority': authority,
        'x-requested-with': 'XMLHttpRequest',
        'Content-Type': 'application/json',
        'api-token': token
    }
    url = f'{baseurl}/api/v3/organizations/{provider}/{organization}/coding-standards?sourceRepository={repo}'
    data = '{"name":"defaultCodingStandard","languages": %s}' % (languages)
    createDraft = requests.post(url, headers=headers,data=data)
    return createDraft.status_code

def listLanguagesAllRepos(repositories):
    languages = []
    for lang in repositories:
        languages.extend(lang['languages'])
    languages = list(dict.fromkeys(languages))
    return json.dumps(languages)

def listRepositories(baseurl,provider,organization,token):
    authority = re.sub('http[s]{0,1}://', '', baseurl)
    headers = {
        'authority': authority,
        'x-requested-with': 'XMLHttpRequest',
        'Content-Type': 'application/json',
        'api-token': token
    }
    url = '%s/api/v3/organizations/%s/%s/repositories' % (baseurl,provider,organization)
    repositories = json.loads(requests.get(url, headers=headers).text)['data']
    return repositories

def getCodingStandardId(baseurl,provider,organization,token,existingDraft):
    authority = re.sub('http[s]{0,1}://', '', baseurl)
    headers = {
        'authority': authority,
        'x-requested-with': 'XMLHttpRequest',
        'Content-Type': 'application/json',
        'api-token': token
    }
    url = '%s/api/v3/organizations/%s/%s/coding-standards' % (baseurl,provider,organization)
    data = json.loads(requests.get(url, headers=headers).text)['data']
    for id in data:
        if(id['isDraft'] == existingDraft):
           return id['id']

def listTools(baseurl,provider,organization,token,codingID):
    authority = re.sub('http[s]{0,1}://', '', baseurl)
    headers = {
        'authority': authority,
        'x-requested-with': 'XMLHttpRequest',
        'Content-Type': 'application/json',
        'api-token': token
    }
    url = f'{baseurl}/api/v3/organizations/{provider}/{organization}/coding-standards/{codingID}/tools'
    listTools = requests.get(url, headers=headers).text
    data = json.loads(listTools)['data']
    return data

def enableTools(data,baseurl,provider,organization,token,codingID): #enable all tools according to the languages in CS languages
    enabled = True
    for tools in data:
        print("Enabling the tool ID:", tools['uuid'])
        enableDisableTool(baseurl,provider,organization,token,tools['uuid'],enabled,codingID)

def listPatterns(baseurl,toolID, provider, organization, codingID,token):
    result = []
    cursor = ''
    hasNextPage = True
    authority = re.sub('http[s]{0,1}://', '', baseurl)
    headers = {
        'authority': authority,
        'Content-Type': 'application/json',
        'Accept' : 'application/json',
        'api-token': token
    }
    while hasNextPage:
        url = '%s/api/v3/organizations/%s/%s/coding-standards/%s/tools/%s/patterns?limit=100&%s' % (    
            baseurl, provider, organization, codingID,toolID, cursor)
        r = requests.get(url, headers=headers)
        patterns = json.loads(r.text)
        for pattern in patterns['data']:
            result.append(
                        {
                            'id': pattern['patternDefinition']['id'],
                            'name': pattern['patternDefinition']['title'],
                            'category': pattern['patternDefinition']['category'],
                            'severityLevel': pattern['patternDefinition']['severityLevel'],
                            'enabled': pattern['patternDefinition']['enabled']
                        }
                )
        hasNextPage = 'cursor' in patterns['pagination']
        if hasNextPage:
            cursor = 'cursor=%s' % patterns['pagination']['cursor']
    return result

def enableSecurityPatterns(patterns,baseurl,provider,organization,token,toolUuid,codingID):
    patternsPayload = []
    for pattern in patterns:
        if(pattern['category'] == 'Security') and (pattern['severityLevel'] == 'Warning' or pattern['severityLevel'] == 'Error'):
            patternsPayload.append({
                "id": pattern['id'],
                "enabled": True
            })
    for i in range(0, len(patternsPayload), 1000):
        enableDisableRule(baseurl,provider,organization,token,toolUuid,patternsPayload[i:i+1000],codingID)

def disableAllPatterns(patterns,baseurl,provider,organization,token,toolUuid,codingID):
    patternsPayload = []
    for pattern in patterns:
        patternsPayload.append({
            "id": pattern['id'],
            "enabled": False
            })
    for i in range(0, len(patternsPayload), 1000):
        enableDisableRule(baseurl,provider,organization,token,toolUuid,patternsPayload[i:i+1000],codingID)

def enableToolsAndRules(baseurl,provider,organization,token,codingID):
    tools = listTools(baseurl,provider,organization,token,codingID)
    enableTools(tools,baseurl,provider,organization,token,codingID)
    for tool in tools:
        print("\nWe're working on the tool ID: ",tool['uuid'])
        patterns = listPatterns(baseurl,tool['uuid'], provider, organization, codingID,token)
        disableAllPatterns(patterns,baseurl,provider,organization,token,tool['uuid'],codingID)
        enableSecurityPatterns(patterns,baseurl,provider,organization,token,tool['uuid'],codingID)
        print("The work is done for the tool ID: ",tool['uuid'])

def enableDisableTool(baseurl,provider,organization,token,toolUuid,enabled,codingID):
    authority = re.sub('http[s]{0,1}://', '', baseurl)
    headers = {
        'authority': authority,
        'Content-Type': 'application/json',
        'Accept' : 'application/json',
        'api-token': token
    }
    url = f'{baseurl}/api/v3/organizations/{provider}/{organization}/coding-standards/{codingID}/tools/{toolUuid}'
    data = """
        {
        "enabled": %s,
        "patterns": [
        ]
        }
        """ % (enabled)
    updateTool = requests.patch(url, data = data, headers=headers)
    print(updateTool.status_code)
    time.sleep(1)

def enableDisableRule(baseurl,provider,organization,token,toolUuid,patternsPayload,codingID):
    authority = re.sub('http[s]{0,1}://', '', baseurl)
    headers = {
        'authority': authority,
        'Content-Type': 'application/json',
        'Accept' : 'application/json',
        'api-token': token
    }
    url = f'{baseurl}/api/v3/organizations/{provider}/{organization}/coding-standards/{codingID}/tools/{toolUuid}'
    data = {
        "enabled": True,
        "patterns": patternsPayload
    }
    data = json.dumps(data)
    updateRule = requests.patch(url, data = data, headers=headers)
    print(updateRule.status_code)
    time.sleep(1)

def applyCodingStandardToRepositories(baseurl,provider,organization,token,codingID,repositories):
    authority = re.sub('http[s]{0,1}://', '', baseurl)
    headers = {
        'authority': authority,
        'Content-Type': 'application/json',
        'Accept' : 'application/json',
        'api-token': token
    }
    url = f'{baseurl}/api/v3/organizations/{provider}/{organization}/coding-standards/{codingID}/repositories'
    data = """
        {
            "link": [
                "%s"
            ],
            "unlink": [ 
            ]
        }
    """ % (repositories)
    applyCodingStandard = requests.patch(url, data = data, headers=headers)
    print(applyCodingStandard.status_code)
    time.sleep(1)

def promoteDraft(baseurl,provider,organization,token,codingID):
    authority = re.sub('http[s]{0,1}://', '', baseurl)
    headers = {
        'authority': authority,
        'x-requested-with': 'XMLHttpRequest',
        'Content-Type': 'application/json',
        'api-token': token
    }
    url = f'{baseurl}/api/v3/organizations/{provider}/{organization}/coding-standards/{codingID}/promote'
    promoteDraft = requests.post(url, headers=headers)
    print(promoteDraft.status_code)

def setDefault(baseurl,provider,organization,token,codingID):
    authority = re.sub('http[s]{0,1}://', '', baseurl)
    headers = {
        'authority': authority,
        'x-requested-with': 'XMLHttpRequest',
        'Content-Type': 'application/json',
        'api-token': token
    }
    url = f'{baseurl}/api/v3/organizations/{provider}/{organization}/coding-standards/{codingID}/setDefault'
    data = """
        {
            "isDefault": true
        }
        """
    setDefault = requests.post(url, headers=headers, data = data)
    print(setDefault.status_code)

def getFirstRepo(repositories):
    for repo in repositories:
        return repo['name']

def main():
    print('\nWelcome to Codacy!')

    parser = argparse.ArgumentParser(description='Codacy Integration Helper')
    parser.add_argument('--token', dest='token', default=None,
                        help='the api-token to be used on the REST API')
    parser.add_argument('--provider', dest='provider',
                        default=None, help='git provider (gh|gl|bb|ghe|gle|bbe')
    parser.add_argument('--organization', dest='organization',
                        default=None, help='organization name')
    parser.add_argument('--baseurl', dest='baseurl', default='https://app.codacy.com',
                        help='codacy server address (ignore if you use cloud)')
    args = parser.parse_args()
   
    print("\nScript is running... take a coffee and enjoy!\n")
    
    startdate = time.time()
    
    #1st step: check the list of languages of all repos
    repositories = listRepositories(args.baseurl,args.provider,args.organization,args.token)
    languages = listLanguagesAllRepos(repositories)

    #2nd step: create Coding Standard if it doesn't exist one or create a Draft of a existing Coding Standard
    repo = getFirstRepo(repositories)
    if (getCodingStandardId(args.baseurl,args.provider,args.organization,args.token,False) == None):
        createCodingStandardStatus = createCodingStandard(args.baseurl,args.provider,args.organization,args.token,languages,repo)
        if(createCodingStandardStatus < 200 and createCodingStandardStatus >= 300):
            print("Coding Standard was not created. Please try again later: ",createCodingStandardStatus)
            return 0
        else:
            codingStandardID = getCodingStandardId(args.baseurl,args.provider,args.organization,args.token,False)
    else:
        createDraftStatus = createDraft(args.baseurl,args.provider,args.organization,args.token,languages)
        if(createDraftStatus < 200 and  createDraftStatus >= 300):
            print("Draft was not created. Please try again later: ",createDraftStatus)
            return 0
        else:
            codingStandardID = getCodingStandardId(args.baseurl,args.provider,args.organization,args.token,True)
    
    #3rd step: enable all medium and critical security rules and disabled all the other rules
    enableToolsAndRules(args.baseurl,args.provider,args.organization,args.token,codingStandardID)
    
    #4th step: apply draft to all repos
    for repo in repositories:
        print("Applying this CS to the repo: ",repo['name'])
        applyCodingStandardToRepositories(args.baseurl,args.provider,args.organization,args.token,codingStandardID,repo['name'])

    #5th step: promote draft
    print("Promoting this CS...")
    promoteDraft(args.baseurl,args.provider,args.organization,args.token,codingStandardID)
    
    #6th step: set CS default
    print("Setting this CS as default...")
    setDefault(args.baseurl,args.provider,args.organization,args.token,codingStandardID)

    enddate = time.time()
    print("The script took ",round(enddate-startdate,2)," seconds")

main()