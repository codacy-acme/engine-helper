import os
import requests
import json
from datetime import datetime

# Use environment variables
CODACY_API_TOKEN = os.environ.get("CODACY_API_TOKEN")
GIT_PROVIDER = os.environ.get("GIT_PROVIDER")
ORGANIZATION_NAME = os.environ.get("CODACY_ORGANIZATION_NAME")
REPOSITORY_NAME = os.environ.get("CODACY_REPOSITORY_NAME")

BASE_URL = "https://app.codacy.com/api/v3"

headers = {
    "api-token": CODACY_API_TOKEN,
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def get_pull_requests(state):
    url = f"{BASE_URL}/analysis/organizations/{GIT_PROVIDER}/{ORGANIZATION_NAME}/repositories/{REPOSITORY_NAME}/pull-requests"
    
    params = {"search": state}
    print(f"Fetching {state} pull requests from: {url}")
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching {state} pull requests: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def search_ignored_issues(pull_request_number=None):
    url = f"{BASE_URL}/analysis/organizations/{GIT_PROVIDER}/{ORGANIZATION_NAME}/repositories/{REPOSITORY_NAME}/ignoredIssues/search"
    
    body = {}
    if pull_request_number:
        body["branchName"] = f"pull-request-{pull_request_number}"
    
    print(f"Searching ignored issues from: {url}")
    print(f"Request body: {json.dumps(body)}")
    response = requests.post(url, headers=headers, json=body)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error searching ignored issues: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def generate_report(pull_request_data, ignored_issues):
    if pull_request_data:
        pr = pull_request_data.get("pullRequest", {})
        report = {
            "pull_request_id": pr.get("number"),
            "title": pr.get("title"),
            "status": pr.get("status"),
            "author": pr.get("owner", {}).get("name"),
            "created_at": pr.get("updated"),
            "is_up_to_standards": pull_request_data.get("isUpToStandards"),
            "new_issues": pull_request_data.get("newIssues"),
            "fixed_issues": pull_request_data.get("fixedIssues"),
            "delta_coverage": pull_request_data.get("deltaCoverage"),
            "diff_coverage": pull_request_data.get("diffCoverage"),
        }
    else:
        report = {
            "pull_request_id": None,
            "title": "Repository-wide ignored issues",
            "status": "N/A",
            "author": "N/A",
            "created_at": "N/A",
        }
    
    report["ignored_issues_count"] = len(ignored_issues.get("data", [])) if ignored_issues else "Unable to fetch"
    report["ignored_issues"] = []
    
    if ignored_issues and "data" in ignored_issues:
        for issue in ignored_issues["data"]:
            report["ignored_issues"].append({
                "file": issue.get("filePath"),
                "line": issue.get("lineNumber"),
                "issue": issue.get("message"),
                "pattern": issue.get("patternInfo", {}).get("id"),
                "category": issue.get("patternInfo", {}).get("category"),
                "level": issue.get("patternInfo", {}).get("level"),
                "tool": issue.get("toolInfo", {}).get("name"),
                "language": issue.get("language")
            })
    
    return report

def main():
    print("Script started.")
    # Check if all required environment variables are set
    required_vars = ["CODACY_API_TOKEN", "GIT_PROVIDER", "CODACY_ORGANIZATION_NAME", "CODACY_REPOSITORY_NAME"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"Error: The following environment variables are not set: {', '.join(missing_vars)}")
        return

    open_prs = get_pull_requests("last-updated")
    closed_prs = get_pull_requests("merged")

    all_prs = []
    if open_prs and "data" in open_prs:
        all_prs.extend(open_prs["data"])
    if closed_prs and "data" in closed_prs:
        all_prs.extend(closed_prs["data"])

    print(f"Found {len(all_prs)} pull requests in total.")

    all_reports = []
    if all_prs:
        for pr_data in all_prs:
            if isinstance(pr_data, dict) and "pullRequest" in pr_data and "number" in pr_data["pullRequest"]:
                pr_number = pr_data["pullRequest"]["number"]
                print(f"Processing PR #{pr_number}")
                
                ignored_issues = search_ignored_issues(pr_number)
                report = generate_report(pr_data, ignored_issues)
                all_reports.append(report)
            else:
                print(f"Unexpected PR structure: {pr_data}")
    else:
        print("No pull requests found. Fetching all ignored issues for the repository.")
        ignored_issues = search_ignored_issues()
        report = generate_report(None, ignored_issues)
        all_reports.append(report)

    if not all_reports:
        print("No reports generated. No ignored issues found in the repository.")
        return

    # Generate a timestamp for the filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"codacy_ignored_issues_report_{timestamp}.json"

    # Write the report to a file
    with open(filename, 'w') as f:
        json.dump(all_reports, f, indent=2)

    print(f"Report generated and saved to {filename}")
    print(f"Total reports generated: {len(all_reports)}")
    print(f"Total ignored issues: {sum(len(report['ignored_issues']) for report in all_reports)}")

if __name__ == "__main__":
    main()