# Codacy Coding Standards Migration Tool

A Python script to migrate coding standards between Codacy environments. This tool supports:
- Self-Hosted Codacy to Codacy Cloud migration
- Codacy Cloud to Codacy Cloud migration (between organizations)

## Features

- Interactive standard selection
- Multiple destination organization support
- Proper tool and pattern migration
- Handles pagination for large pattern sets
- Preserves tool configurations and pattern parameters
- Supports both self-hosted and cloud-to-cloud migrations
- Progress tracking and detailed logging

## Prerequisites

- Python 3.6+
- Required Python packages:
  ```bash
  pip install requests
  pip install halo
  ```
- Access tokens:
  - For Self-Hosted to Cloud migration: Both self-hosted and cloud API tokens
  - For Cloud to Cloud migration: Codacy cloud API token

## Environment Variables

Set the following environment variables before running the script:

For Self-Hosted to Cloud migration:
```bash
export SELF_HOSTED_API_TOKEN="your-self-hosted-token"
export CLOUD_API_TOKEN="your-cloud-token"
export SELF_HOSTED_API_URL="https://codacy.your-domain.com/api/v3"  # Optional, defaults to https://codacy.mycompany.com/api/v3
```

For Cloud to Cloud migration:
```bash
export CLOUD_API_TOKEN="your-cloud-token"
```

## Usage

Run the script:
```bash
python script.py
```

The script will guide you through:
1. Selecting migration mode (Self-Hosted to Cloud or Cloud to Cloud)
2. Choosing the provider (gh for GitHub, gl for GitLab, bb for BitBucket)
3. Entering source organization name
4. Entering destination organization(s)
5. Selecting the coding standard to migrate

## Migration Process

The tool follows these steps for each destination:

1. **Setup Phase**
   - Validates environment variables
   - Fetches source coding standard details
   - Gets list of enabled tools and their patterns

2. **Creation Phase**
   - Creates new coding standard in destination
   - Sets proper language configuration

3. **Tool Configuration Phase**
   For each tool:
   - Enables the tool
   - Gets all currently enabled patterns (handling pagination)
   - Disables any auto-enabled patterns
   - Updates with specific source patterns

4. **Finalization Phase**
   - Promotes the standard to make it active

## Error Handling

The script includes comprehensive error handling for:
- API connection issues
- Missing environment variables
- Invalid organization names
- Pattern migration failures
- Pagination errors

## Limitations

- Cannot modify tools not available in destination environment
- Some tool configurations may need manual review
- API rate limiting may affect large migrations
- Tool configurations are environment-specific

## Troubleshooting

Common issues and solutions:

1. **Authentication Errors**
   - Verify environment variables are set correctly
   - Ensure tokens have proper permissions
   - Check token validity

2. **Pattern Migration Issues**
   - Verify source patterns are enabled
   - Check tool compatibility between environments
   - Review pattern IDs in both environments

3. **Rate Limiting**
   - Script includes built-in delays between requests
   - Adjust sleep duration if needed

4. **Missing Tools**
   - Verify tool availability in destination
   - Check tool name mappings
   - Review tool compatibility

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.
