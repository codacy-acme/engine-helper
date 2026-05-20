import csv
import requests
import argparse
import time
from datetime import date
from collections import Counter
import concurrent.futures

def get_headers(api_token):
    return {
        'Accept': 'application/json',
        'api-token': api_token
    }

def list_repositories(provider, organization, api_token, session):
    cursor = ''
    seen_cursors = set()
    result = []
    pages_fetched = 0
    
    while True:
        url = f'https://app.codacy.com/api/v3/organizations/{provider}/{organization}/repositories?limit=100{cursor}'
        response = session.get(url, headers=get_headers(api_token), timeout=10)
        response.raise_for_status() 
        
        data = response.json()
        repos = data.get('data', [])
        if not repos:
            break
            
        for repo in repos:
            result.append({
                'name': repo.get('name'),
                'lastUpdated': repo.get('lastUpdated', 'None')
            })
            
        pages_fetched += 1
        
        pagination = data.get('pagination', {})
        cursor_val = pagination.get('cursor')
        
        # Safeguard: Ensure cursor exists AND is unique to prevent infinite loops
        if cursor_val and cursor_val not in seen_cursors:
            seen_cursors.add(cursor_val)
            cursor = f"&cursor={cursor_val}"
        else:
            break
            
    print(f"[System] Found a total of {len(result)} repositories across {pages_fetched} pages.")
    return result

def get_issues_counts(provider, organization, repository, api_token, session):
    cursor = ''
    seen_cursors = set()
    severity_counts = Counter()
    category_counts = Counter()
    pages_fetched = 0
    
    while True:
        url = f'https://app.codacy.com/api/v3/analysis/organizations/{provider}/{organization}/repositories/{repository}/issues/search?limit=100{cursor}'
        response = session.post(url, headers=get_headers(api_token), timeout=10)
        
        if response.status_code != 200:
            print(f"   ! [{repository}] getIssues error -> {response.status_code}")
            break
            
        data = response.json()
        issues = data.get('data', [])
        
        # If it 
        returns an empty list, we have reached the end
        if not issues:
            break
            
        for issue in issues:
            pattern_info = issue.get('patternInfo', {})
            severity_counts[pattern_info.get('severityLevel')] += 1
            category_counts[pattern_info.get('category')] += 1
            
        pages_fetched += 1
        # Print progress every 10 pages so you know the thread is alive
        if pages_fetched % 10 == 0:
            print(f"   ↳ [{repository}] Fetched {pages_fetched} pages... ({sum(severity_counts.values())} issues found so far)")
            
        pagination = data.get('pagination', {})
        cursor_val = pagination.get('cursor')
        
        # Safeguard: Ensure cursor exists AND is unique
        if cursor_val and cursor_val not in seen_cursors:
            seen_cursors.add(cursor_val)
            cursor = f"&cursor={cursor_val}"
        else:
            break
            
    return severity_counts, category_counts

def get_coverage_grade(provider, organization, repository, api_token, session):
    url = f'https://app.codacy.com/api/v3/analysis/organizations/{provider}/{organization}/repositories/{repository}'
    response = session.get(url, headers=get_headers(api_token), timeout=10)
    
    if response.status_code < 300:
        data = response.json().get('data', {})
        grade = data.get('gradeLetter')
        coverage = data.get('coverage', {}).get('coveragePercentage')
        return coverage, grade
    else:
        print(f"   ! [{repository}] getCoverageGrade error -> {response.status_code}")
        return None, None

def process_single_repo(repo, provider, organization, api_token, session):
    repo_name = repo['name']
    print(f"[+] Started processing: {repo_name}")
    
    severity_counts, category_counts = get_issues_counts(provider, organization, repo_name, api_token, session)
    coverage, grade = get_coverage_grade(provider, organization, repo_name, api_token, session)
    
    total_issues = (
        severity_counts['Error'] + 
        severity_counts['Warning'] + 
        severity_counts['Info'] + 
        severity_counts['High']
    )
    
    print(f"[✓] Finished processing: {repo_name} | Total Issues: {total_issues}")
    
    return [
        repo_name, repo['lastUpdated'], coverage, grade,
        severity_counts['Error'], severity_counts['High'], severity_counts['Warning'], severity_counts['Info'], total_issues,
        category_counts['ErrorProne'], category_counts['CodeStyle'], category_counts['Complexity'], 
        category_counts['UnusedCode'], category_counts['Security'], category_counts['Compatibility'], 
        category_counts['Performance'], category_counts['Documentation'], category_counts['BestPractice'], 
        category_counts['Comprehensibility'], category_counts['Duplication']    
    ]

def write_report(provider, organization, repositories, api_token):
    today = date.today()
    filename = f'{organization}-OrgOverview-{today}.csv'
    
    headers = [
        'Repository', 'Last Updated', 'Coverage', 'Grade', 'Critical', 'High', 'Medium', 'Minor', 'Total Issues',
        'ErrorProne', 'CodeStyle', 'Complexity', 'UnusedCode', 'Security', 'Compatibility', 'Performance', 
        'Documentation', 'BestPractice', 'Comprehensibility', 'Duplication'
    ]

    with requests.Session() as session:
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            # Using 10 parallel worker threads
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(process_single_repo, repo, provider, organization, api_token, session)
                    for repo in repositories
                ]
                
                for future in concurrent.futures.as_completed(futures):
                    try:
                        row_data = future.result()
                        writer.writerow(row_data)
                    except Exception as e:
                        print(f"[!] Critical error on a repository execution thread: {e}")

def main():
    print('\nWelcome to Codacy Integration Helper - Organization Overview\n')
    parser = argparse.ArgumentParser(description='Codacy Integration Helper')
    parser.add_argument('--apiToken', dest='apiToken', required=True, help='the api-token to be used on the REST API')
    parser.add_argument('--provider', dest='provider', required=True, help='git provider (gh|gl|bb)')
    parser.add_argument('--organization', dest='organization', required=True, help='organization name')
    args = parser.parse_args()

    start_time = time.time()

    with requests.Session() as session:
        repositories = list_repositories(args.provider, args.organization, args.apiToken, session)
        
    write_report(args.provider, args.organization, repositories, args.apiToken)

    print(f"\nThe script completed successfully in {round(time.time() - start_time, 2)} seconds!")

if __name__ == "__main__":
    main()