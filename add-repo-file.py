import argparse
import requests
import csv
import time
import sys

def read_repositories_from_csv(csv_file):
    try:
        with open(csv_file, 'r') as file:
            csv_reader = csv.reader(file)
            repos = [row[0].strip() for row in csv_reader]
        print(f"Read {len(repos)} repositories from CSV file:")
        for repo in repos:
            print(f"  - {repo}")
        return repos
    except Exception as e:
        print(f"Error reading CSV file: {str(e)}")
        sys.exit(1)

def add_repository(baseurl, provider, organization, repo, token):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'api-token': token,
        'caller': 'codacy-integration-helper'
    }
    data = {
        "provider": provider,
        "repositoryFullPath": f'{organization}/{repo}'
    }
    url = f'{baseurl}/api/v3/repositories'
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return True, f"Successfully added {repo}: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"Failed to add {repo}: {e.response.status_code if e.response else 'N/A'}, Response: {e.response.text if e.response else 'N/A'}"

def add_all_repositories(baseurl, provider, organization, token, csv_file):
    repositories = read_repositories_from_csv(csv_file)
    
    results = {"success": [], "failed": []}
    
    for repo in repositories:
        success, message = add_repository(baseurl, provider, organization, repo, token)
        if success:
            results["success"].append(repo)
        else:
            results["failed"].append((repo, message))
    
    print("\nResults:")
    print(f"Successfully added {len(results['success'])} repositories:")
    for repo in results['success']:
        print(f"  - {repo}")
    
    print(f"\nFailed to add {len(results['failed'])} repositories:")
    for repo, message in results['failed']:
        print(f"  - {repo}: {message}")
    
    return results

def main():
    print('\nWelcome to Codacy Integration Helper - A solution to Add Repositories\n')
    parser = argparse.ArgumentParser(description='Codacy Integration Helper')
    parser.add_argument('--token', dest='token', required=True,
                        help='the api-token to be used on the REST API')
    parser.add_argument('--csv_file', dest='csv_file', required=True,
                        help='path to the CSV file containing repository names')
    parser.add_argument('--provider', dest='provider', required=True,
                        help='git provider (gh|ghe)')
    parser.add_argument('--organization', dest='organization', required=True,
                        help='organization name')
    parser.add_argument('--baseurl', dest='baseurl', default='https://app.codacy.com',
                        help='codacy server address (ignore if cloud)')
    args = parser.parse_args()
    
    start_date = time.time()
    
    add_all_repositories(args.baseurl, args.provider, args.organization, args.token, args.csv_file)
    
    end_date = time.time()
    print(f"\nThe script took {round(end_date - start_date, 2)} seconds")

if __name__ == "__main__":
    main()
