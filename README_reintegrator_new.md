# Codacy Integration Helper - API Version

A modern replacement for the original `reintegrator.py` script that works with Codacy's SPA architecture.

## Purpose

This script changes repository integration ownership from one user account to another using API tokens. 

**Use Case Example**: If a repository was integrated by John but should be owned by `codacy_bot`, run this script with `codacy_bot`'s API token to transfer the integration ownership.

## Key Features

- **API-based**: Uses Codacy's official REST API v3 instead of web scraping
- **Token authentication**: Secure API token-based authentication
- **Integration ownership transfer**: Changes who owns the repository integration
- **Comprehensive logging**: Shows current and new integration owners
- **Batch processing**: Can process multiple repositories at once
- **Error handling**: Proper error reporting and recovery

## Installation

1. Ensure you have Python 3.6+ installed
2. Install required dependencies:
   ```bash
   pip install requests
   ```

## Usage

### Basic Usage

```bash
# Transfer integration ownership to the account associated with the token
python3 reintegrator_new.py --provider gh --organization MyOrg --token YOUR_API_TOKEN
```

### Single Repository

```bash
# Transfer ownership for a specific repository
python3 reintegrator_new.py --provider gh --organization MyOrg --token YOUR_API_TOKEN --which "my-repo"
```

### Multiple Repositories

```bash
# Transfer ownership for specific repositories
python3 reintegrator_new.py --provider gh --organization MyOrg --token YOUR_API_TOKEN --which "repo1,repo2,repo3"
```

### Different Codacy Instance

```bash
# For self-hosted Codacy instances
python3 reintegrator_new.py --provider gh --organization MyOrg --token YOUR_API_TOKEN --baseurl https://codacy.mycompany.com
```

## Command Line Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--token` | Yes | Codacy API token for the account that should own the integrations |
| `--provider` | Yes | Git provider: `gl` (GitLab), `bb` (Bitbucket) |
| `--organization` | Yes | Organization name (case-sensitive) |
| `--baseurl` | No | Codacy server address (default: `https://app.codacy.com`) |
| `--which` | No | Comma-separated list of repositories to process (default: all repositories) |

## How It Works

1. **Lists repositories** in the specified organization
2. **Filters repositories** if `--which` is specified
3. **For each repository**:
   - Shows current integration owner (for logging)
   - Calls the refresh provider integration API endpoint
   - This automatically changes the integration owner to the account associated with the token
   - Shows new integration owner (for confirmation)

## API Token Setup

1. Log in to Codacy with the account that should own the integrations
2. Go to Account Settings → API Tokens
3. Generate a new API token with appropriate permissions
4. Use this token with the `--token` argument

## Migration from Original Script

The original `reintegrator.py` used web scraping and is no longer compatible with Codacy's SPA architecture. This new script:

- ✅ **Works with current Codacy**: Compatible with SPA architecture
- ✅ **More reliable**: Uses stable API endpoints instead of HTML parsing
- ✅ **Better security**: API tokens instead of cookie manipulation
- ✅ **Simpler**: Focused on core functionality (ownership transfer)
- ✅ **Faster**: No browser automation or complex HTML parsing

### Command Comparison

```bash
# Old script (broken)
python reintegrator.py --provider gh --organization MyOrg --token TOKEN

# New script (working)
python3 reintegrator_new.py --provider gh --organization MyOrg --token TOKEN
```

## Example Output

```
Codacy Integration Helper - API-based version
Changes repository integration ownership to the account associated with the provided token
Starting reintegration for organization: MyOrg
Provider: gh
This will change integration ownership to the account associated with the provided token
Found 5 repositories
Filtering to 2 specified repositories

--- Processing repository: my-app ---
Current integration owner: john@company.com
Reintegrating my-app with new token owner...
✓ Successfully reintegrated my-app
New integration owner: codacy_bot@company.com

--- Processing repository: my-api ---
Current integration owner: john@company.com
Reintegrating my-api with new token owner...
✓ Successfully reintegrated my-api
New integration owner: codacy_bot@company.com

=== Summary ===
Successfully reintegrated: 2/2 repositories

✓ All repositories reintegrated successfully!
```

## Troubleshooting

### Common Issues

1. **404 Not Found**: Check organization name case sensitivity (e.g., `MyOrg` vs `myorg`)
2. **401 Unauthorized**: Verify API token is valid and has necessary permissions
3. **Repository not found**: Ensure repository exists and is accessible with the provided token

### Error Messages

- `Could not find repository`: Repository doesn't exist or token lacks access
- `API request failed`: Network issues or API endpoint problems
- `Failed to list repositories`: Organization doesn't exist or token lacks permissions

## API Endpoints Used

- `GET /api/v3/organizations/{provider}/{org}/repositories` - List repositories
- `GET /api/v3/organizations/{provider}/{org}/repositories/{repo}/integrations/providerSettings` - Get integration info
- `POST /api/v3/organizations/{provider}/{org}/repositories/{repo}/integrations/refreshProvider` - Refresh integration (changes owner)

## Requirements

- Python 3.6+
- `requests` library
- Valid Codacy API token
- Network access to Codacy instance

## License

This script is part of the Codacy engine-helper toolkit.
