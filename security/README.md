# Codacy Security Items CSV Generator

This script fetches security items from the Codacy API and generates a comprehensive CSV report. It handles pagination automatically and provides filtering options for targeted reporting.

## Features

- **Automatic pagination**: Fetches all security items across multiple pages
- **Flexible filtering**: Filter by repositories, statuses, priorities, categories, and scan types
- **Comprehensive data extraction**: Extracts 11 key fields per security item
- **CSV export**: Generates clean, structured CSV files for analysis
- **Summary statistics**: Provides counts by severity and source

## CSV Output Fields

The generated CSV includes the following fields:

| Field | Description |
|-------|-------------|
| `id` | Unique identifier of the security item |
| `severity` | Priority/severity level (Critical, High, Medium, Low) |
| `description` | Title/summary of the security issue |
| `repository` | Repository name where the issue was found |
| `source` | Item source (Codacy, Jira, PenTest, ZAP, etc.) |
| `opened_at` | When the item was first detected (ISO 8601 format) |
| `closed_at` | When the item was resolved (ISO 8601 format, if applicable) |
| `html_url` | Direct link to view the item in Codacy |
| `line_number` | Line number where the issue occurs (if applicable) |
| `filepath` | File path where the issue was found (if applicable) |
| `pattern_internal_id` | Internal pattern identifier (if applicable) |

## Requirements

- Python 3.6+
- `requests` library (install with: `pip install requests`)
- Valid Codacy API token with appropriate permissions

## Usage

### Basic Usage

Generate a report for all security items in an organization:

```bash
python security-items.py \
  --base-url https://app.codacy.com \
  --token YOUR_API_TOKEN \
  --provider gh \
  --organization your-org-name
```

### Filtering Options

#### Filter by Repositories

```bash
python security-items.py \
  --base-url https://app.codacy.com \
  --token YOUR_API_TOKEN \
  --provider gh \
  --organization your-org-name \
  --repositories "repo1,repo2,repo3"
```

#### Filter by Priority/Severity

```bash
python security-items.py \
  --base-url https://app.codacy.com \
  --token YOUR_API_TOKEN \
  --provider gh \
  --organization your-org-name \
  --priorities "Critical,High"
```

#### Filter by Status (Open Items Only)

```bash
python security-items.py \
  --base-url https://app.codacy.com \
  --token YOUR_API_TOKEN \
  --provider gh \
  --organization your-org-name \
  --statuses "OnTrack,DueSoon,Overdue"
```

#### Filter by Scan Types

```bash
python security-items.py \
  --base-url https://app.codacy.com \
  --token YOUR_API_TOKEN \
  --provider gh \
  --organization your-org-name \
  --scan-types "SAST,SCA,Secrets"
```

#### Custom Output Filename

```bash
python security-items.py \
  --base-url https://app.codacy.com \
  --token YOUR_API_TOKEN \
  --provider gh \
  --organization your-org-name \
  --output "security-report-2024.csv"
```

## Available Filter Values

### Providers
- `gh` - GitHub
- `gl` - GitLab  
- `bb` - Bitbucket

### Statuses
- `OnTrack` - Items within SLA
- `DueSoon` - Items approaching due date
- `Overdue` - Items past due date
- `ClosedOnTime` - Items resolved within SLA
- `ClosedLate` - Items resolved after due date
- `Ignored` - Items marked as ignored

### Priorities
- `Critical` - Critical severity
- `High` - High severity
- `Medium` - Medium severity
- `Low` - Low severity

### Scan Types
- `SAST` - Static Application Security Testing
- `SCA` - Software Composition Analysis
- `ContainerSCA` - Container Software Composition Analysis
- `Secrets` - Secrets detection
- `IaC` - Infrastructure as Code
- `CICD` - CI/CD security
- `License` - License compliance
- `PenTesting` - Penetration testing
- `DAST` - Dynamic Application Security Testing
- `CSPM` - Cloud Security Posture Management

## API Endpoint

This script uses the Codacy Security Items API endpoint:

```
GET /api/v3/organizations/{provider}/{organization}/security/items
```

For complete API documentation, visit: https://api.codacy.com/api/api-docs#listsecurityitems

## Output Example

The script generates output similar to:

```
Fetching security items for gh/myorg...
Filtering by priorities: ['Critical', 'High']
Fetching page 1...
Fetched 100 items from page 1
Fetching page 2...
Fetched 45 items from page 2
Total items fetched: 145
CSV report generated: security_items.csv
Total rows: 145

--- Summary ---
By Severity:
  Critical: 23
  High: 122

By Source:
  Codacy: 140
  PenTest: 5
```

## Error Handling

The script provides detailed error messages for common issues:

- **401 Unauthorized**: Invalid API token
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Organization not found or no access
- **Network errors**: Connection issues or API unavailability

## Performance Notes

- Uses pagination with 100 items per page for optimal performance
- Includes a small delay (0.1s) between requests to be respectful to the API
- Progress is displayed for long-running operations

## Security Considerations

- Store API tokens securely (e.g., environment variables)
- Don't commit API tokens to version control
- Use read-only tokens when possible
- Follow your organization's API token management policies