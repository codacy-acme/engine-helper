# Codacy Ignored Issues Report Generator

This script generates a report of ignored issues for pull requests in a Codacy repository. If no pull requests are found, it searches for ignored issues across the entire repository.

## Prerequisites
`
- Python 3.x
- `requests` library (`pip install requests`)

## Setup

1. Clone this repository or download the script file.

2. Set up the following environment variables:

   ```
   CODACY_API_TOKEN=your_codacy_api_token
   GIT_PROVIDER=gh  # Use 'gh' for GitHub, 'bb' for Bitbucket, etc.
   CODACY_ORGANIZATION_NAME=your_organization_name
   CODACY_REPOSITORY_NAME=your_repository_name
   ```

   You can set these variables in your shell or create a `.env` file and use a library like `python-dotenv` to load them.

## Usage

Run the script using Python:

```
python ignored-report.py
```

The script will:

1. Fetch pull requests from the specified Codacy repository.
2. For each pull request, retrieve ignored issues.
3. If no pull requests are found, it will search for ignored issues across the entire repository.
4. Generate a JSON report file with the findings.

## Output

The script generates a JSON file named `codacy_ignored_issues_report_YYYYMMDD_HHMMSS.json` in the same directory. This file contains details about ignored issues for each pull request or for the entire repository.

The console output will show:
- The name of the generated report file
- The total number of reports generated
- The total number of ignored issues found

## Troubleshooting

If you encounter any issues:

1. Ensure all required environment variables are set correctly.
2. Check your Codacy API token has the necessary permissions.
3. Verify the organization name and repository name are correct.

## Note

