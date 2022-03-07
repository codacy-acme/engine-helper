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
python3 reintegrator.py --token {token} --provider {git-provider} --organization {organization} --which {reponame (optional)} --repoid {repoid (optional)} --baseurl {baseurl (optional)}
```

Flag --which is optional. If missing, will be for all repositories.


## Generate Configuration File for Tool

Generates a configuration file for the given tool. Since it's a PoC, currently only supports PMD.

```bash
 config_file_generator.py [-h] [--token TOKEN] [--provider PROVIDER] [--organization ORGANIZATION] [--tooluuid TOOLUUID] [--baseurl BASEURL]
```

Tools list can retrieved using:
```bash
python3 main.py --action listengines [--baseurl BASEURL]
```