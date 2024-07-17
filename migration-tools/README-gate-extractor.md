# Codacy Quality Settings Migration Script

This script automates the process of migrating quality settings from a self-hosted Codacy instance to Codacy Cloud. It handles the migration of repository, commit, and pull request quality settings for all repositories in a specified organization.

## Features

- Migrates quality settings for multiple repositories in a single run
- Handles three types of quality settings: repository, commits, and pull requests
- Verifies the migration by comparing self-hosted settings with updated cloud settings
- Provides a progress bar for visual feedback during migration
- Generates a detailed JSON report of the migration process
- Displays a summary of migration results upon completion

## Requirements

- Python 3.6+
- `requests` library
- `tqdm` library

You can install the required libraries using pip:

```
pip install requests tqdm
```

## Setup

1. Clone this repository or download the script file.

2. Set up the following environment variables:

   ```
   export SELF_HOSTED_API_URL="http://your-self-hosted-codacy-url"
   export SELF_HOSTED_API_TOKEN="your-self-hosted-api-token"
   export CLOUD_API_TOKEN="your-codacy-cloud-api-token"
   ```

   Replace the values with your actual self-hosted Codacy URL and API tokens.

## Usage

Run the script using the following command:

```
python3 gate-extractor.py -p <provider> -o <self-hosted-org> -c <cloud-org>
```

Arguments:
- `-p, --provider`: The Git provider (e.g., gh for GitHub, gl for GitLab)
- `-o, --organization`: The organization name in your self-hosted Codacy instance
- `-c, --cloud-organization`: The organization name in Codacy Cloud

Example:
```
python3 gate-extractor.py -p gh -o my-self-hosted-org -c my-cloud-org
```

## Output

The script will display a progress bar showing the migration progress. Upon completion, it will generate two outputs:

1. A JSON file named `<organization>_migration_results.json` containing detailed migration results for each repository and setting type.

2. A summary in the console, showing:
   - Total number of repositories processed
   - Number of fully successful migrations
   - Number of repositories with issues

## Troubleshooting

If you encounter any issues:

1. Check that your environment variables are correctly set.
2. Ensure you have the necessary permissions in both your self-hosted instance and Codacy Cloud.
3. Verify that the repositories exist in both the self-hosted instance and Codacy Cloud.
4. Review the generated JSON file for specific error messages for each repository and setting type.

## Caution

This script will overwrite existing quality settings in Codacy Cloud. Make sure to review the changes and have a backup of your current cloud settings before running the migration.

## Support

If you encounter any problems or have any questions, please open an issue in this repository or contact Codacy support.