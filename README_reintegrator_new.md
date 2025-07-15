# Codacy Integration Helper - API-based Version

This is a modern rewrite of the original `reintegrator.py` script to work with Codacy's new SPA (Single Page Application) architecture. The original script used web scraping and is no longer functional due to Codacy's migration to a React-based frontend.

## What Changed

### Original Script Issues
- **Web Scraping**: Used BeautifulSoup to parse HTML pages that no longer exist
- **Cookie Authentication**: Relied on browser cookies which are unreliable for automation
- **Internal Endpoints**: Made requests to internal web URLs that have been deprecated
- **Browser Automation**: Required opening browser windows for OAuth flows

### New API-based Approach
- **REST API**: Uses Codacy's official REST API v3 endpoints
- **Token Authentication**: Secure API token-based authentication
- **Documented Endpoints**: Uses officially supported and documented API endpoints
- **No Browser Required**: Pure API-based solution with no browser dependencies

## Features

### Core Functionality
- List repositories in an organization
- Get current integration settings for repositories
- Update integration settings (commit status, PR comments, PR summary, suggestions)
- Refresh provider integrations
- Batch process multiple repositories

### Supported Providers
- `gh` - GitHub
- `gl` - GitLab  
- `bb` - Bitbucket
- `ghe` - GitHub Enterprise
- `gle` - GitLab Enterprise
- `bbe` - Bitbucket Enterprise (Stash)

### Integration Settings
- **Commit Status**: Enable/disable status checks on commits
- **Pull Request Comments**: Enable/disable issue annotations on PRs
- **Pull Request Summary**: Enable/disable coverage summary (GitHub only)
- **Suggestions**: Enable/disable suggested fixes (GitHub only)
- **AI Enhanced Comments**: Enable/disable AI-enhanced comments

## Installation

The script uses the same dependencies as the original, but no longer requires BeautifulSoup or browser automation:

```bash
pip install requests
```

## Usage

### Basic Usage
```bash
python reintegrator_new.py --token YOUR_API_TOKEN --provider gh --organization your-org
```

### Process Specific Repositories
```bash
python reintegrator_new.py --token YOUR_API_TOKEN --provider gh --organization your-org --which "repo1,repo2,repo3"
```

### Custom Settings
```bash
# Enable all features for GitHub
python reintegrator_new.py --token YOUR_API_TOKEN --provider gh --organization your-org \
  --commit-status --pr-comments --pr-summary --suggestions

# Disable specific features
python reintegrator_new.py --token YOUR_API_TOKEN --provider gh --organization your-org \
  --no-pr-summary --no-suggestions
```

### Enterprise/Self-hosted Codacy
```bash
python reintegrator_new.py --token YOUR_API_TOKEN --provider ghe --organization your-org \
  --baseurl https://your-codacy-instance.com
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--token` | Codacy API token (required) | - |
| `--provider` | Git provider (gh\|gl\|bb\|ghe\|gle\|bbe) | - |
| `--organization` | Organization name (required) | - |
| `--baseurl` | Codacy server URL | https://app.codacy.com |
| `--which` | Comma-separated list of repositories | All repositories |
| `--commit-status` / `--no-commit-status` | Enable/disable commit status checks | Provider default |
| `--pr-comments` / `--no-pr-comments` | Enable/disable PR comments | Provider default |
| `--pr-summary` / `--no-pr-summary` | Enable/disable PR summary (GitHub only) | Provider default |
| `--suggestions` / `--no-suggestions` | Enable/disable suggestions (GitHub only) | Provider default |

## API Token

You need a Codacy API token with appropriate permissions:

1. Go to your Codacy account settings
2. Navigate to "API Tokens" 
3. Create a new token with organization and repository permissions
4. Use this token with the `--token` parameter

## Provider-Specific Defaults

The script applies sensible defaults based on the provider:

### GitHub (`gh`, `ghe`)
- Commit Status: ✓ Enabled
- PR Comments: ✓ Enabled  
- PR Summary: ✓ Enabled
- Suggestions: ✓ Enabled
- AI Enhanced Comments: ✗ Disabled

### GitLab (`gl`, `gle`)
- Commit Status: ✓ Enabled
- PR Comments: ✓ Enabled
- PR Summary: ✗ Disabled (GitHub only)
- Suggestions: ✗ Disabled (GitHub only)
- AI Enhanced Comments: ✓ Enabled

### Bitbucket (`bb`, `bbe`)
- Commit Status: ✓ Enabled
- PR Comments: ✓ Enabled
- PR Summary: ✗ Disabled (GitHub only)
- Suggestions: ✗ Disabled (GitHub only)
- AI Enhanced Comments: ✓ Enabled

## Error Handling

The script includes comprehensive error handling:
- API authentication errors
- Network connectivity issues
- Invalid repository names
- Permission errors
- Rate limiting

Failed repositories are reported in the summary, and the script exits with appropriate status codes.

## Migration from Original Script

### Command Line Compatibility
The new script maintains backward compatibility with the original command line interface:

```bash
# Original command
python reintegrator.py --provider gh --organization MyOrg --token TOKEN

# New command (same syntax)
python reintegrator_new.py --provider gh --organization MyOrg --token TOKEN
```

### Key Differences
1. **No cookie file required**: The new script uses API tokens instead of cookies
2. **No browser automation**: Everything is done via API calls
3. **Better error handling**: More detailed error messages and recovery
4. **Additional options**: More granular control over integration settings

## Troubleshooting

### Common Issues

**Authentication Error (401)**
- Verify your API token is correct and has not expired
- Ensure the token has the required permissions for the organization

**Repository Not Found (404)**
- Check that the repository name is correct
- Verify you have access to the repository
- Ensure the organization name is correct

**Permission Denied (403)**
- Your API token may not have sufficient permissions
- You may not be a member of the organization
- The repository may be private and you don't have access

**Rate Limiting (429)**
- The script will automatically retry with backoff
- Consider processing fewer repositories at once

### Debug Mode
For debugging, you can modify the script to enable verbose logging by adding:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## API Endpoints Used

The script uses these Codacy API v3 endpoints:

- `GET /organizations/{provider}/{org}/repositories` - List repositories
- `GET /organizations/{provider}/{org}/integrations/providerSettings` - Get org settings
- `GET /organizations/{provider}/{org}/repositories/{repo}/integrations/providerSettings` - Get repo settings
- `PATCH /organizations/{provider}/{org}/repositories/{repo}/integrations/providerSettings` - Update repo settings
- `POST /organizations/{provider}/{org}/repositories/{repo}/integrations/refreshProvider` - Refresh integration

## Contributing

When making changes to this script:

1. Test with different providers (GitHub, GitLab, Bitbucket)
2. Verify error handling for various failure scenarios
3. Ensure backward compatibility with the original command line interface
4. Update this README with any new features or changes

## License

This script is part of the Codacy engine-helper toolkit and follows the same license as the parent project.
