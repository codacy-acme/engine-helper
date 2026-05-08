#!/usr/bin/env python3
"""
Codacy Security Items CSV Generator

This script fetches security items from the Codacy API and generates a CSV report.
It handles pagination automatically and extracts the following fields:
- id: Unique identifier of the security item
- severity: Priority/severity level (Critical, High, Medium, Low)
- description: Title/summary of the security issue
- repository: Repository name where the issue was found
- source: Item source (Codacy, Jira, PenTest, ZAP, etc.)
- opened_at: When the item was first detected
- closed_at: When the item was resolved (if applicable)
- html_url: Direct link to view the item in Codacy
- line_number: Line number where the issue occurs (if applicable)
- filepath: File path where the issue was found (if applicable)
- pattern_internal_id: Internal pattern identifier (if applicable)
"""

import requests
import time
import csv
import argparse
from typing import List, Dict, Any, Optional


class CodacySecurityItemsClient:
    """Client for fetching security items from Codacy API."""

    def __init__(self, base_url: str, api_token: str):
        """
        Initialize the Codacy client.

        Args:
            base_url: Codacy API base URL (e.g., https://app.codacy.com)
            api_token: Codacy API token
        """
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Accept': 'application/json',
            'api-token': api_token
        }

    def _build_query_params(self, repositories, statuses, priorities, categories, scan_types):
        """Build query parameters for API request."""
        params = {'limit': 100}

        if repositories:
            params['repositories'] = ','.join(repositories)
        if statuses:
            params['status'] = statuses
        if priorities:
            params['priority'] = priorities
        if categories:
            params['category'] = categories
        if scan_types:
            params['scanType'] = scan_types

        return params

    def _handle_api_error(self, response, exception):
        """Handle API errors and provide meaningful messages."""
        print(f"Error fetching security items: {exception}")
        if response.status_code == 401:
            print("Authentication failed. Please check your API token.")
        elif response.status_code == 403:
            print("Access forbidden. Please check your permissions.")
        elif response.status_code == 404:
            print("Organization not found or no access.")

    def fetch_security_items(
        self,
        provider: str,
        organization: str,
        repositories: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        priorities: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        scan_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all security items with pagination support.

        Args:
            provider: Git provider (gh, gl, bb)
            organization: Organization name
            repositories: List of repository names to filter
            statuses: List of statuses to filter
            priorities: List of priorities to filter
            categories: List of security categories to filter
            scan_types: List of scan types to filter

        Returns:
            List of security items
        """
        url = f'{self.base_url}/api/v3/organizations/{provider}/{organization}/security/items'
        params = self._build_query_params(repositories, statuses, priorities, categories, scan_types)

        all_items = []
        page_count = 0
        has_next_page = True
        cursor = ''

        while has_next_page:
            page_count += 1
            print(f"Fetching page {page_count}...")

            current_params = params.copy()
            if cursor:
                current_params['cursor'] = cursor

            try:
                response = requests.get(url, headers=self.headers, params=current_params)
                response.raise_for_status()

                data = response.json()
                items = data.get('data', [])
                all_items.extend(items)

                print(f"Fetched {len(items)} items from page {page_count}")

                # Check if there's a next page
                pagination = data.get('pagination', {})
                has_next_page = 'cursor' in pagination and pagination['cursor']

                if has_next_page:
                    cursor = pagination['cursor']
                    time.sleep(0.1)  # Be respectful to the API

            except requests.exceptions.RequestException as e:
                self._handle_api_error(response, e)
                raise

        print(f"Total items fetched: {len(all_items)}")
        return all_items

    def _extract_file_info(self, item):
        """Extract file path and line number from item."""
        filepath = ''
        line_number = ''

        # Try to extract file information from various possible fields
        if 'filePath' in item:
            filepath = item.get('filePath', '')
        elif 'file' in item:
            filepath = item.get('file', {}).get('path', '')

        # Extract line number
        if 'lineNumber' in item:
            line_number = str(item.get('lineNumber', ''))
        elif 'line' in item:
            line_number = str(item.get('line', ''))

        return filepath, line_number

    def _extract_pattern_id(self, item):
        """Extract pattern internal ID from item."""
        if 'patternId' in item:
            return item.get('patternId', '')
        elif 'pattern' in item:
            return item.get('pattern', {}).get('id', '')
        elif 'itemSourceId' in item and item.get('itemSource') == 'Codacy':
            return item.get('itemSourceId', '')
        return ''

    def extract_csv_data(self, items: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Extract and format data for CSV export.

        Args:
            items: Raw security items from API

        Returns:
            List of dictionaries with CSV-ready data
        """
        csv_data = []

        for item in items:
            filepath, line_number = self._extract_file_info(item)
            pattern_internal_id = self._extract_pattern_id(item)

            csv_row = {
                'id': item.get('id', ''),
                'severity': item.get('priority', ''),
                'description': item.get('title', ''),
                'repository': item.get('repository', ''),
                'source': item.get('itemSource', ''),
                'opened_at': item.get('openedAt', ''),
                'closed_at': item.get('closedAt', ''),
                'html_url': item.get('htmlUrl', ''),
                'line_number': line_number,
                'filepath': filepath,
                'pattern_internal_id': pattern_internal_id
            }

            csv_data.append(csv_row)

        return csv_data


def write_csv(data: List[Dict[str, str]], filename: str):
    """
    Write data to CSV file.

    Args:
        data: List of dictionaries with CSV data
        filename: Output CSV filename
    """
    if not data:
        print("No data to write to CSV")
        return

    fieldnames = [
        'id', 'severity', 'description', 'repository', 'source',
        'opened_at', 'closed_at', 'html_url', 'line_number',
        'filepath', 'pattern_internal_id'
    ]

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"CSV report generated: {filename}")
    print(f"Total rows: {len(data)}")


def create_argument_parser():
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate CSV report of Codacy security items",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate report for all security items
  python security-items.py --base-url https://app.codacy.com --token YOUR_TOKEN --provider gh --organization myorg

  # Filter by specific repositories
  python security-items.py --base-url https://app.codacy.com --token YOUR_TOKEN --provider gh --organization myorg --repositories repo1,repo2

Available values:
  Providers: gh (GitHub), gl (GitLab), bb (Bitbucket)
  Statuses: OnTrack, DueSoon, Overdue, ClosedOnTime, ClosedLate, Ignored
  Priorities: Critical, High, Medium, Low
  Scan Types: SAST, SCA, ContainerSCA, Secrets, IaC, CICD, License, PenTesting, DAST, CSPM
        """)

    # Required arguments
    parser.add_argument('--base-url',
                        default='https://app.codacy.com',
                       help='Codacy base URL (e.g., https://app.codacy.com)')
    parser.add_argument('--token', required=True, help='Codacy API token')
    parser.add_argument('--provider', required=True, choices=['gh', 'gl', 'bb'], help='Git provider')
    parser.add_argument('--organization', required=True, help='Organization name')
    parser.add_argument('--output', default='security_items.csv',
                       help='Output CSV filename (default: security_items.csv)')

    # Optional filters
    parser.add_argument('--repositories', help='Comma-separated list of repository names')
    parser.add_argument('--statuses', help='Comma-separated list of statuses')
    parser.add_argument('--priorities', help='Comma-separated list of priorities')
    parser.add_argument('--categories', help='Comma-separated list of security categories')
    parser.add_argument('--scan-types', help='Comma-separated list of scan types')

    return parser


def parse_filter_arguments(args):
    """Parse comma-separated filter arguments."""
    return {
        'repositories': args.repositories.split(',') if args.repositories else None,
        'statuses': args.statuses.split(',') if args.statuses else None,
        'priorities': args.priorities.split(',') if args.priorities else None,
        'categories': args.categories.split(',') if args.categories else None,
        'scan_types': args.scan_types.split(',') if args.scan_types else None,
    }


def print_filters(filters):
    """Print active filters."""
    for name, values in filters.items():
        if values:
            print(f"Filtering by {name}: {values}")


def print_summary(csv_data):
    """Print summary statistics."""
    print("\n--- Summary ---")
    if not csv_data:
        return

    severities = {}
    sources = {}

    for row in csv_data:
        # Count by severity
        severity = row['severity'] or 'Unknown'
        severities[severity] = severities.get(severity, 0) + 1

        # Count by source
        source = row['source'] or 'Unknown'
        sources[source] = sources.get(source, 0) + 1

    print("By Severity:")
    for severity, count in sorted(severities.items()):
        print(f"  {severity}: {count}")

    print("\nBy Source:")
    for source, count in sorted(sources.items()):
        print(f"  {source}: {count}")


def main():
    """Main function to parse arguments and generate the security items CSV."""
    parser = create_argument_parser()
    args = parser.parse_args()

    # Parse filter arguments
    filters = parse_filter_arguments(args)

    # Initialize client
    client = CodacySecurityItemsClient(args.base_url, args.token)

    # Print what we're doing
    print(f"Fetching security items for {args.provider}/{args.organization}...")
    print_filters(filters)

    try:
        items = client.fetch_security_items(
            provider=args.provider,
            organization=args.organization,
            **filters
        )

        # Extract CSV data and write to file
        csv_data = client.extract_csv_data(items)
        write_csv(csv_data, args.output)

        # Print summary
        print_summary(csv_data)

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
