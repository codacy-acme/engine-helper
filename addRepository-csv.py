import argparse
import csv
import requests
import json
import time

def readRepositoriesFromCSV(csvFilePath):
    """Read repository names from a CSV file.

    Args:
        csvFilePath (str): The file path to the CSV containing repository names.

    Returns:
        list: A list of repository names.
    """
    repositories = []
    with open(csvFilePath, mode='r', encoding='utf-8') as csvfile:
        csvReader = csv.reader(csvfile)
        for row in csvReader:
            repositories.append(row[0])  # Assuming the repository name is in the first column
    return repositories

def addRepository(baseurl, provider, organization, repo, token):
    """Add a single repository to Codacy.

    Args:
        baseurl (str): The base URL for the Codacy API.
        provider (str): The git provider (e.g., 'gh' for GitHub, 'gl' for GitLab).
        organization (str): The organization name.
        repo (str): The repository name to be added.
        token (str): The API token for Codacy.
    """
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'api-token': token
    }
    data ={
        "repositoryFullPath": f'{organization}/{repo}',
        "provider": provider
    }
    url = f'{baseurl}/api/v3/repositories'
    response = requests.post(url, headers=headers, data=json.dumps(data))
    print(f'{repo}: {response.status_code}')

def main():
    parser = argparse.ArgumentParser(description='Codacy Integration Helper')
    parser.add_argument('--token', required=True,
                        help='The API token to be used on the REST API')
    parser.add_argument('--csvFilePath', required=True,
                        help='Path to the CSV file containing repository names')
    parser.add_argument('--provider', required=True,
                        help='Git provider (gh for GitHub, gl for GitLab, etc.)')
    parser.add_argument('--organization', required=True,
                        help='Organization name')
    parser.add_argument('--baseurl', default='https://app.codacy.com',
                        help='Codacy server address (ignore if cloud)')

    args = parser.parse_args()

    startdate = time.time()
    
    repositories = readRepositoriesFromCSV(args.csvFilePath)
    for repo in repositories:
        addRepository(args.baseurl, args.provider, args.organization, repo, args.token)

    enddate = time.time()
    print(f"\nThe script took {round(enddate-startdate,2)} seconds")

if __name__ == "__main__":
    main()
