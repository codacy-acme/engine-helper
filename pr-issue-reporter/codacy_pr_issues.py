import os
import requests
import argparse
import csv
from typing import List, Dict, Any

class CodacyAPI:
    BASE_URL = "https://app.codacy.com/api/v3"

    def __init__(self):
        self.api_token = os.environ.get("CODACY_API_TOKEN")
        self.git_provider = os.environ.get("GIT_PROVIDER")
        self.organization_name = os.environ.get("CODACY_ORGANIZATION_NAME")

        if not all([self.api_token, self.git_provider, self.organization_name]):
            raise ValueError("Missing required environment variables. Please set CODACY_API_TOKEN, GIT_PROVIDER, and CODACY_ORGANIZATION_NAME.")

        self.headers = {
            "api-token": self.api_token,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def get_repositories(self) -> List[Dict[str, Any]]:
        url = f"{self.BASE_URL}/organizations/{self.git_provider}/{self.organization_name}/repositories"
        all_repositories = []
        cursor = None

        while True:
            params = {"limit": 100}
            if cursor:
                params["cursor"] = cursor

            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            repositories = data.get("data", [])
            all_repositories.extend(repositories)

            pagination = data.get("pagination", {})
            cursor = pagination.get("cursor")

            if not cursor:
                break

        print(f"Total repositories fetched: {len(all_repositories)}")
        return all_repositories

    def get_repository(self, repo_name: str) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/organizations/{self.git_provider}/{self.organization_name}/repositories/{repo_name}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json().get("data", {})

    def get_pull_requests(self, repo_name: str, pr_status: str) -> List[Dict[str, Any]]:
        url = f"{self.BASE_URL}/analysis/organizations/{self.git_provider}/{self.organization_name}/repositories/{repo_name}/pull-requests"
        all_pull_requests = []
        cursor = None

        while True:
            params = {"limit": 100}
            if pr_status == "open":
                params["search"] = "last-updated"
            elif pr_status == "closed":
                params["search"] = "merged"

            if cursor:
                params["cursor"] = cursor

            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            pull_requests = data.get("data", [])
            all_pull_requests.extend(pull_requests)

            pagination = data.get("pagination", {})
            cursor = pagination.get("cursor")

            if not cursor:
                break

        print(f"Total pull requests fetched: {len(all_pull_requests)}")
        return all_pull_requests

    def get_pull_request_issues(self, repo_name: str, pull_request_number: int) -> List[Dict[str, Any]]:
        url = f"{self.BASE_URL}/analysis/organizations/{self.git_provider}/{self.organization_name}/repositories/{repo_name}/pull-requests/{pull_request_number}/issues"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])

def select_repository(repositories: List[Dict[str, Any]]) -> str:
    print("\nAvailable Repositories:")
    for i, repo in enumerate(repositories, 1):
        print(f"{i}. {repo['name']}")
    while True:
        try:
            choice = int(input("\nEnter the number of the repository you want to select: "))
            if 1 <= choice <= len(repositories):
                return repositories[choice - 1]['name']
            print("Invalid choice. Please enter a number from the list.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def choose_pr_status():
    while True:
        choice = input("Do you want to see (1) Open pull requests, or (2) Merged (closed) pull requests? Enter 1 or 2: ")
        if choice == '1':
            return "open"
        elif choice == '2':
            return "closed"
        print("Invalid choice. Please enter 1 or 2.")

def select_pull_request(pull_requests: List[Dict[str, Any]]) -> int:
    print("\nAvailable Pull Requests:")
    for pr in pull_requests:
        pr_info = pr.get('pullRequest', {})
        pr_number = pr_info.get('number')
        pr_title = pr_info.get('title')
        pr_status = pr_info.get('status')
        updated_at = pr_info.get('updated')
        print(f"#{pr_number} - {pr_title} (Status: {pr_status}, Last Updated: {updated_at})")

    while True:
        try:
            pr_number = int(input("\nEnter the Pull Request number: "))
            if any(pr['pullRequest']['number'] == pr_number for pr in pull_requests):
                return pr_number
            print("Invalid PR number. Please choose from the list above.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def map_severity_to_ui(api_severity: str) -> str:
    severity_mapping = {
        "Info": "Minor",
        "Warning": "Medium",
        "Error": "Critical"
    }
    return severity_mapping.get(api_severity, api_severity)

def save_to_csv(issues: List[Dict[str, Any]], filename: str):
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['message', 'severity', 'filePath', 'line', 'category', 'tool', 'patternId']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for issue in issues:
            commit_issue = issue.get('commitIssue', {})
            pattern_info = commit_issue.get('patternInfo', {})
            writer.writerow({
                'message': commit_issue.get('message', ''),
                'severity': map_severity_to_ui(pattern_info.get('severityLevel', '')),
                'filePath': commit_issue.get('filePath', ''),
                'line': commit_issue.get('lineNumber', ''),
                'category': pattern_info.get('category', ''),
                'tool': commit_issue.get('toolInfo', {}).get('name', ''),
                'patternId': pattern_info.get('id', '')
            })

def main():
    parser = argparse.ArgumentParser(description="Filter Codacy issues by severity in pull requests.")
    parser.add_argument("--severity", choices=["minor", "medium", "critical"], help="Filter by severity")

    args = parser.parse_args()

    try:
        codacy = CodacyAPI()
        repositories = codacy.get_repositories()
        selected_repo = select_repository(repositories)
        repo_info = codacy.get_repository(selected_repo)
        print(f"Successfully connected to repository: {repo_info.get('name', 'Unknown')}")
    except (ValueError, requests.exceptions.RequestException) as e:
        print(f"Error initializing Codacy API or fetching repositories: {e}")
        if isinstance(e, requests.exceptions.RequestException) and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response content: {e.response.content}")
        return

    try:
        pr_status = choose_pr_status()
        pull_requests = codacy.get_pull_requests(selected_repo, pr_status)
        if not pull_requests:
            print(f"No {pr_status} pull requests found for this repository.")
            return
        pr_number = select_pull_request(pull_requests)
        selected_pr = next(pr for pr in pull_requests if pr['pullRequest']['number'] == pr_number)
        pr_info = selected_pr['pullRequest']
        print(f"\nSelected Pull Request: #{pr_number} - {pr_info.get('title', 'No title')}")
        print(f"Status: {pr_info.get('status', 'Unknown')}")
        print(f"New Issues: {selected_pr.get('newIssues', 'Unknown')}")
        print(f"Fixed Issues: {selected_pr.get('fixedIssues', 'Unknown')}")

        issues = codacy.get_pull_request_issues(selected_repo, pr_number)
        
        if args.severity:
            issues = [issue for issue in issues if map_severity_to_ui(issue['commitIssue']['patternInfo']['severityLevel']).lower() == args.severity.lower()]

        print(f"\nFound {len(issues)} issues in Pull Request #{pr_number}:")

        # Display summary of all issues
        for issue in issues:
            commit_issue = issue.get('commitIssue', {})
            pattern_info = commit_issue.get('patternInfo', {})
            tool_info = commit_issue.get('toolInfo', {})

            message = commit_issue.get('message', 'No message provided')
            severity = map_severity_to_ui(pattern_info.get('severityLevel', 'Unknown'))
            file_path = commit_issue.get('filePath', 'Unknown')
            line = commit_issue.get('lineNumber', 'Unknown')
            category = pattern_info.get('category', 'Unknown')
            tool = tool_info.get('name', 'Unknown')
            pattern_id = pattern_info.get('id', 'Unknown')

            print(f"- {message}")
            print(f"  Severity: {severity}")
            print(f"  File: {file_path}")
            print(f"  Line: {line}")
            print(f"  Category: {category}")
            print(f"  Tool: {tool}")
            print(f"  Pattern ID: {pattern_id}")
            print()  # Add a blank line between issues for better readability

        if issues:
            csv_filename = f"{selected_repo}_pr_{pr_number}_issues.csv"
            save_to_csv(issues, csv_filename)
            print(f"\nDetailed issue information has been saved to {csv_filename}")
        else:
            print("No issues found.")

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        if e.response:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response content: {e.response.content}")

if __name__ == "__main__":
    main()