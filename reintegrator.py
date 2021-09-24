#!/usr/bin/env python3
import argparse
import requests
import json
import re


def readCookieFile():
    with open("auth.cookie", "r") as myfile:
        data = myfile.read().replace('\n', '')
        return data

def integrate(baseurl, repoId, provider):
    authority = re.sub('http[s]{0,1}://','',baseurl)
    headers = {
        'authority': authority,
        'x-requested-with': 'XMLHttpRequest',
        'cookie': readCookieFile(),
        'Content-Type': 'application/json'
    }
    url = '%s/integrations/create/%s/%s' % (baseurl, repoId, provider)
    data = '{}'

    response = requests.post(url, headers=headers, data=data)
    print(response)
