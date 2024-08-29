# Codacy API Pull Request Issues Script

This script will fetch and display issues for pull requests in a specified repository. It allows users to view and filter issues based on severity levels.

## Features

- Fetch and display all repositories in your Codacy organization
- Select a specific repository to analyze
- List open or closed pull requests for the selected repository
- Display issues for a selected pull request
- Filter issues by severity (minor, medium, critical)
- Save issue details to a CSV file for further analysis

## Requirements

- Python 3.6 or higher
- `requests` library

## Setup

1. Clone this repository or download the script file.

2. Install the required Python library:
   ```
   pip install requests
   ```

3. Set up the following environment variables:
   - `CODACY_API_TOKEN`: Your Codacy API token
   - `GIT_PROVIDER`: Your Git provider (e.g., "gh" for GitHub, "gl" for GitLab)
   - `CODACY_ORGANIZATION_NAME`: Your Codacy organization name

   You can set these variables in your shell or create a `.env` file in the same directory as the script.

## Usage

Run the script from the command line:

```
python codacy_pr_issues.py [--severity {minor,medium,critical}]
```

The `--severity` argument is optional. If provided, it will filter the issues based on the specified severity level.

## Script Workflow

1. The script connects to the Codacy API and fetches all repositories in your organization.
2. You select a repository from the list.
3. The script fetches all pull requests for the selected repository.
4. You choose whether to view open or closed pull requests.
5. You select a specific pull request to analyze.
6. The script fetches and displays all issues for the selected pull request.
7. If a severity filter is applied, only issues matching the specified severity are shown.
8. Issue details are saved to a CSV file for further analysis.

## CSV Output

The script generates a CSV file named `{repository_name}_pr_{pr_number}_issues.csv` containing the following information for each issue:

- Message
- Severity
- File Path
- Line Number
- Category
- Tool
- Pattern ID

## Notes

- Large repositories or pull requests with many issues may take some time to process.
