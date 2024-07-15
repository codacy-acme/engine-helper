# Codacy Migration Script

## Overview

This script automates the process of migrating a coding standard from a self-hosted Codacy instance to Codacy Cloud. It performs the following steps:

1. Fetches the coding standard data from the self-hosted Codacy instance.
2. Creates a new coding standard in Codacy Cloud with the same languages as the self-hosted standard.
3. Disables all tools that are enabled by default in the new Codacy Cloud standard.
4. Updates the new coding standard with the tools and patterns from the self-hosted instance.
5. Promotes the new coding standard in Codacy Cloud.

## Requirements

- Python 3.6 or higher
- `requests` library (can be installed via `pip install requests`)

## Setup

1. Clone this repository or download the `cs-extractor-importer.py` script.
2. Install the required Python library:
   ```
   pip install requests
   ```
3. Set up the following environment variables:
   - `SELF_HOSTED_API_URL`: The API URL of your self-hosted Codacy instance 
   - `SELF_HOSTED_API_TOKEN`: The API token for your self-hosted Codacy instance
   - `CLOUD_API_TOKEN`: The API token for your Codacy Cloud instance

## Usage

Run the script with the following command:

```
python codacy_migration.py -p <provider> -o <self-hosted-org> -c <cloud-org>
```

Replace the placeholders with your specific values:
- `<provider>`: The Git provider (e.g., "gh" for GitHub, "gl" for GitLab)
- `<self-hosted-org>`: The organization name in your self-hosted Codacy instance
- `<cloud-org>`: The organization name in Codacy Cloud

## Example

```
python cs-extractor-importer.py -p gh -o my-self-hosted-org -c my-cloud-org
```

## Notes

- The script will create a new coding standard in Codacy Cloud with the name "Migrated: [Original Standard Name]".
- All default tools in the new Codacy Cloud standard will be disabled before migrating the self-hosted configuration.
- Only enabled tools and patterns from the self-hosted instance will be migrated to the Cloud standard.
- The script includes error handling and will print informative messages during the migration process.

## Troubleshooting

If you encounter any issues:
1. Ensure all environment variables are correctly set.
2. Check that your API tokens have the necessary permissions.
3. Verify that your self-hosted Codacy instance is accessible and that the Codacy Cloud API is available.

For any persistent issues, please check the error messages in the console output and consult the Codacy documentation or support channels.

## Disclaimer

This script is provided as-is. Always test the migration process in a non-production environment before using it on your main Codacy instance.