# engine-helper

An helper to enable, disable or toggle configuration files for Codacy engines.

## Usage

Create a file named auth.cookie and dump inside it the value of your Codacy cookie.

The `requirements.txt` lists all Python libraries that should be installed before running the script:

```bash
pip3 install -r requirements.txt
```

```text
arguments:
    -h, --help            show this help message and exit
    --token TOKEN         the api-token to be used on the REST API
    --action {enableengine,disableengine,listengines,useconfigurationfile,dontuseconfigurationfile} action to take
    --which WHICH         repository to be updated, none means all
    --provider PROVIDER   git provider
    --organization ORGANIZATION   organization id
    --engine ENGINE       engine id
    --baseurl BASEURL     codacy server address (ignore if cloud)
```

## Enable Security only Patterns (only for on-prem)

### Create patterns.json file
```
psql -U codacy -h {host} -d postgres
\c analysis
\t on
\pset format unaligned
with t as (select "id", "internalId" from "Pattern")
select json_agg(t) from t \g patterns.json
\q
```

### Execution

```bash
python3 main.py --action securityonly --baseurl https://yourserveraddress --token {token} --provider {git-provider} --organization {organization} --which {repoId}
```
Flag --which is optional. If missing, will be for all repositories.

## Remove current integration and add for a specific account

This script should be used if you are looking to set set-up a service account or similar.
The script will open some tabs on the browser in order to enable the integration.
Currently works on Codacy Cloud. On-prem will be available in the next release (>= 4.4.0)

### Execution

```bash
python3 reintegrator.py --token {token} --provider {git-provider} --organization {organization} --which {reponame (optional)} --baseurl {baseurl (optional)}
```

Flag --which is optional. If missing, will be for all repositories.

## Add Slack integration 

This script will add the slack integration automatically for a specific repository (or all repositories if the option --which and --repoid is not present). To integrate a specific repository, you must use the arguments --which <reponame> and --repoid <repoid>

### Execution

```bash
python3 addSlackIntegration.py --token {token} --provider {git-provider} --organization {organization} --which {reponame (optional)} --repoid {repoid (optional)} --baseurl {baseurl (optional)} --slackChannel {slack channel} --webhookURL {url of slack app}
```

Flag --which is optional. If missing, will be for all repositories.

## Create Coding Standard

This script will create a coding standard with all Medium and Critical Security issues enabled (all the other ones disabled) automatically for all repositories with the languages already present in all repositories within the organization and supported by Codacy

### Execution

```bash
python3 createCodingStandards.py --token {token} --provider {git-provider} --organization {organization} --baseurl {baseurl (optional)}
```

## Generate Configuration File for Tool

Generates a configuration file for the given tool. Since it's a PoC, currently only supports PMD.

```bash
 config_file_generator.py [-h] [--token TOKEN] [--provider PROVIDER] [--organization ORGANIZATION] [--tooluuid TOOLUUID] [--baseurl BASEURL]
```

Tools list can be retrieved using:
```bash
python3 main.py --action listengines [--baseurl BASEURL]
```

## Script to generate a report with all security issues of an organization

This script will generate a report (in XLSX format) with all security issues you can find on all organizations you have permission to see or a specific organization and the list of all security issues per repository

### Execution

```bash
python3 generateSecurityReport.py --baseurl {ignore it, if cloud} --orgname {organization names separated by comma or ignore it if you want all organizations} --token {API token}
```

## Script to generate a report with the performance of all commits for the last x days

This script will generate a CSV file where you can find the new, fixed and ignored issues for all commits in the last x months for every repository across the organization.

### Execution

```bash
python3 commitsPerformance.py --baseurl {ignore it, if cloud} --provider {git-provider} --organization {organization name} --orgid {organization id} --token {API token} --months {number of months}
```

## Script to update Quality Settings 

This script will update the Quality Settings for Pull-Requests (you can do the same for the commits as well) with the following rules: the PR's will be blocked if it has at least one Security issue or Medium/Critical issue of other category (Error Prone, Performance, Code Style, etc). This script allows you to update the Quality Settings for a specific list of repos or the entire organization.

### Execution

```bash
python3 updateQualitySettings.py --baseurl {ignore it, if cloud} --provider {git-provider} --organization {organization name} --orgid {organization id} --token {API token} --reponame {comma separated list of the repositories to be updated, none means all}
```

## Script to enable all decorations in the Integrations tab

With this script, you'll be able to enable all decorations on the Integrations tab in all your active repositories in Codacy or in specific repositories using the flag --reponame

### Execution

```bash
python3 enableDecorations.py --baseurl {ignore it, if cloud} --provider {git-provider} --organization {organization name} --token {API token} --reponame {comma separated list of the repositories to be updated, none means all}
```

## Script to add all repositories from Github

With this script, you'll be able to add all repositories into Codacy or specific repositories using the flag --reponame. This script is able to get all repositories directly from the organization on Github 

### Execution

```bash
python3 addRepositories.py --baseurl {ignore it, if cloud} --provider {git-provider} --organization {organization name} --token {API token on user account} --githubToken {user token from github account} --reponame {comma separated list of the repositories to be updated, none means all} --githubBaseURL {ignore it, if cloud. For SH instance, you should use http(s)://HOSTNAME/api/v3/}
```

## Script to get Coverage Overview from the last 3 months

With this script, you'll be able to see the coverage percentages from the last 3 months of commits in each repo of the entire organization. The available values are: the current coverage percentage, an intermediate coverage percentage (from a commit 1-2 months ago) and the coverage percentage of a commit from 3 months ago.

### Execution

```bash
python3 generateCoverageOverview.py --baseurl {ignore it, if cloud} --provider {git-provider} --organization {organization name} --apiToken {API token on user account}
```

## Script to get Pull Requests Overview from the last 30 days

With this script, you'll be able to generate a report with the following information:
-> PR Status
-> Date
-> PR Id
-> PR number
-> PR Title
-> PR Author
-> Issues added
-> Fixed issues
-> Complexity added
-> Clones added
-> Diff Coverage
-> Delta Coverage

from the last 30 days of a specific repository in your organization

### Execution

```bash
python3 generateReportPullRequests.py --baseurl {ignore it, if cloud} --provider {git-provider} --organization {organization name} --apiToken {API token on user account} --repoName {repository name}
```

## Script to get number of issues per severity of all repositories of organization

With this script, you'll be able to generate a report with all issues per repository by severity.

### Execution

```bash
python3 generateIssuesReport.py --baseurl {ignore it, if cloud} --provider {git-provider} --organization {organization name} --apiToken {API token on user account}
```

## Bitbucket Branch Cleanup Utility

This utility automates the maintenance of your Bitbucket repository by removing stale branches. It ensures that active development branches and the main codebase remain untouched while clearing out old, merged, or abandoned branches.



### 🚀 How It Works

The script applies the following decision logic to every branch in your repository:

1. **Whitelist Check:** Is the branch the `main/master/default` branch or in the `WHITELIST` (e.g., `develop`, `release`)? -> **KEEP**
2. **PR Check:** Does the branch have an **OPEN** Pull Request associated with it? -> **KEEP**
3. **Age Check:** Was the last commit made more than **X days** ago (Default: 180)?
    * **No:** -> **KEEP**
    * **Yes:** -> **DELETE** 

### 🛠️ Prerequisites

* Python 3.7+
* A Bitbucket **Repository Access Token**

### ⚙️ Setup

#### 1. Create Environment & Install Dependencies

To avoid system permission errors, run these commands in the script folder:

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the environment
# (On Mac/Linux):
source venv/bin/activate
# (On Windows):
# venv\Scripts\activate

# Install required libraries
pip install requests python-dotenv
```

#### 2. Create a Repository Access Token

**Do not use your personal password. Create a token specifically for this script:**

Go to Repository Settings > Security > Access Tokens.

Click Create Repository Access Token.

Select the following Scopes:

* Repositories: Read & Write (To read/delete branches)

* Pull requests: Read (To check for open PRs)

Copy the token immediately.

#### 3. Configure Environment Variables

Create a file named .env in the same folder as the script. Important: Ensure the variable names match exactly what is in the script.

```bash
BITBUCKET_WORKSPACE=your_workspace_id
BITBUCKET_USERNAME=your_username
BITBUCKET_REPO_SLUG=your_repo_slug
BITBUCKET_ACCESS_TOKEN=your_access_token_here
```

### 🏃‍♂️ Usage

#### Safety Mode (Dry Run)

By default, the script runs in Dry Run mode. It lists what would be deleted without actually removing anything.

```bash
python delete_bb_branches.py
```

#### Change Age Cutoff

To check for branches older than 90 days (instead of the default 180):

```bash
python delete_bb_branches.py --days 90
```

#### ⚠️ Live Deletion

Once you have verified the Dry Run output, pass the --force flag to perform the actual deletion.

```bash
python delete_bb_branches.py --force
```

Or if you want to delete all branches older than 90 days:

```bash
python delete_bb_branches.py --force --days 90
```

#### 🛡️ Whitelist Configuration

To prevent specific branch names from ever being deleted, edit the WHITELIST array inside delete_bb_branches.py:

```bash
WHITELIST = ['develop', 'release', 'master', 'main', 'production']
```

Note: the default branch is whitelisted by default