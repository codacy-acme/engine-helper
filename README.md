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
python3 addRepositories.py --baseurl {ignore it, if cloud} --provider {git-provider} --organization {organization name} --token {API token on user account} --githubToken {user token from github account}--reponame {comma separated list of the repositories to be updated, none means all}
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