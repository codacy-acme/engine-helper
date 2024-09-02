# Codacy Integration Helper

## Overview

The Codacy Integration Helper is a Python script designed to automate the process of adding repositories to Codacy. It reads repository names from a CSV file and attempts to add each repository to your Codacy organization.

## Features

- Read repository names from a CSV file
- Add multiple repositories to Codacy in bulk
- Provide detailed success/failure reports for each repository addition attempt

## Prerequisites

- Python 3.x
- `requests` library (install using `pip install requests`)
- Codacy API token
- CSV file containing repository names

## Installation

1. Clone this repository or download the script (`codacy_integration_helper.py`).
2. Install the required Python library:

   ```
   pip install requests
   ```

3. Prepare a CSV file with the names of the repositories you want to add (one repository name per line).

## Usage

Run the script from the command line with the following arguments:

```
python add-repo-file.py --token YOUR_API_TOKEN --csv_file PATH_TO_CSV_FILE --provider PROVIDER --organization ORG_NAME [--baseurl CODACY_URL]
```

### Arguments

- `--token`: Your Codacy API token (required)
- `--csv_file`: Path to the CSV file containing repository names (required)
- `--provider`: Git provider (e.g., 'gh' for GitHub, 'ghe' for GitHub Enterprise) (required)
- `--organization`: Your organization name in Codacy (required)
- `--baseurl`: Codacy server address (default: 'https://app.codacy.com')

### Example

```
python codacy_integration_helper.py --token abcdef123456 --csv_file repos.csv --provider gh --organization myorg
```

## CSV File Format

The CSV file should contain one repository name per line. For example:

```
repo1
repo2
repo3
```


## Output

The script will provide detailed output including:
- The repositories read from the CSV file
- A list of successfully added repositories
- A list of repositories that failed to add, along with error messages


## Notes

- The script will attempt to add all repositories listed in the CSV file, even if they are already in Codacy. Duplicate additions will typically result in a failure response from the API.
- The script does not perform any validation of repository names before attempting to add them. Ensure that the names in your CSV file are correct.
