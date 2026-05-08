#!/usr/bin/env python3
"""
Codacy SRM Items Reporter
Fetches all security items from the Codacy API with pagination support.
"""

from time import sleep
import requests
from typing import List, Dict, Optional
import sys
import csv
from datetime import datetime


class CodacySRMReporter:
    """Client for fetching SRM items from Codacy API."""
    
    BASE_URL = "https://app.codacy.com/api/v3"
    
    def __init__(self, api_token: str, provider: str, organization: str):
        """
        Initialize the Codacy SRM Reporter.
        
        Args:
            api_token: Codacy API token
            provider: Git provider (e.g., 'gh', 'gl', 'bb')
            organization: Organization name on the Git provider
        """
        self.api_token = api_token
        self.provider = provider
        self.organization = organization
        self.headers = {
            'Accept': 'application/json',
            'api-token': self.api_token
        }
    
    def get_issue_details(self, repository: str, issue_id: str) -> Optional[Dict]:
        """
        Fetch detailed issue information including filePath and lineNumber.
        
        Args:
            repository: Repository name
            issue_id: Issue ID from itemSourceId
            
        Returns:
            Issue details dictionary or None if not found
        """
        url = f"{self.BASE_URL}/analysis/organizations/{self.provider}/{self.organization}/repositories/{repository}/issues/{issue_id}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', {})
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Issue not found - might be a different type of security item
                return None
            print(f"HTTP Error fetching issue {issue_id}: {e}", file=sys.stderr)
            return None
        except requests.exceptions.RequestException as e:
            print(f"Request Error fetching issue {issue_id}: {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Unexpected Error fetching issue {issue_id}: {e}", file=sys.stderr)
            return None
    
    def enrich_srm_item(self, item: Dict) -> Dict:
        """
        Enrich an SRM item with filePath and lineNumber from issue details.
        
        Args:
            item: SRM item dictionary
            
        Returns:
            Enriched SRM item with filePath and lineNumber added
        """
        item_source_id = item.get('itemSourceId')
        repository = item.get('repository')
        
        # Only fetch issue details if we have the required fields
        if item_source_id and repository and item.get('itemSource') == 'Codacy':
            issue_details = self.get_issue_details(repository, item_source_id)
            
            if issue_details:
                item['filePath'] = issue_details.get('filePath')
                item['lineNumber'] = issue_details.get('lineNumber')
                item['falsePositiveProbability'] = issue_details.get('falsePositiveProbability')
        
        return item
    
    def _enrich_items(self, items: List[Dict]) -> int:
        """
        Enrich items with file paths and line numbers.
        
        Args:
            items: List of SRM items to enrich
            
        Returns:
            Count of successfully enriched items
        """
        print(f"\nEnriching items with file paths and line numbers...", file=sys.stderr)
        enriched_count = 0
        
        for i, item in enumerate(items, 1):
            if i % 10 == 0:
                print(f"Enriching item {i}/{len(items)}...", file=sys.stderr)
                sleep(1)  # To avoid hitting rate limits
            
            enriched_item = self.enrich_srm_item(item)
            
            # Check if enrichment was successful
            if 'filePath' in enriched_item and enriched_item['filePath']:
                enriched_count += 1
        
        print(f"Enrichment complete! {enriched_count}/{len(items)} items enriched", file=sys.stderr)
        return enriched_count
    
    def fetch_all_srm_items(self, limit: int = 100, enrich: bool = True) -> List[Dict]:
        """
        Fetch all SRM items with pagination support.
        
        Args:
            limit: Number of items per page (default: 100)
            enrich: Whether to enrich items with filePath and lineNumber (default: True)
            
        Returns:
            List of all SRM items
        """
        all_items = []
        cursor = None
        page = 1
        
        while True:
            print(f"Fetching page {page}...", file=sys.stderr)
            
            items, next_cursor, total = self._fetch_page(cursor, limit)
            all_items.extend(items)
            
            print(f"Retrieved {len(items)} items (Total so far: {len(all_items)}/{total})", file=sys.stderr)
            
            if not next_cursor or len(items) == 0:
                break
            
            cursor = next_cursor
            page += 1
        
        print(f"Completed! Total items retrieved: {len(all_items)}", file=sys.stderr)
        
        # Enrich items with issue details if requested
        if enrich and all_items:
            self._enrich_items(all_items)
        
        return all_items
    
    def _calculate_time_to_remediate(self, opened_at: str, closed_at: str) -> str:
        """
        Calculate time to remediate between opened and closed dates.
        
        Args:
            opened_at: Opening timestamp (ISO 8601 format)
            closed_at: Closing timestamp (ISO 8601 format)
            
        Returns:
            Human-readable time difference or empty string if calculation not possible
        """
        if not opened_at or not closed_at:
            return ''
        
        try:
            # Parse ISO 8601 timestamps
            opened = datetime.fromisoformat(opened_at.replace('Z', '+00:00'))
            closed = datetime.fromisoformat(closed_at.replace('Z', '+00:00'))
            
            # Calculate difference
            diff = closed - opened
            
            # Return in days (with decimal precision)
            days = diff.total_seconds() / 86400
            return f"{days:.2f}"
            
        except (ValueError, AttributeError) as e:
            return ''
    
    def _prepare_csv_row(self, item: Dict) -> Dict:
        """
        Prepare a single SRM item for CSV export.
        
        Args:
            item: SRM item dictionary
            
        Returns:
            Dictionary with CSV row data
        """
        return {
            'repository': item.get('repository', ''),
            'projectKey': item.get('projectKey', ''),
            'scanType': item.get('scanType', ''),
            'priority': item.get('priority', ''),
            'confidence': item.get('falsePositiveProbability', ''),
            'ruleId': item.get('itemSourceId', ''),
            'ruleName': item.get('title', ''),
            'filePath': item.get('filePath', ''),
            'lineNumber': item.get('lineNumber', ''),
            'status': item.get('status', ''),
            'openedAt': item.get('openedAt', ''),
            'closedAt': item.get('closedAt', ''),
            'timeToRemediate': self._calculate_time_to_remediate(
                item.get('openedAt', ''), 
                item.get('closedAt', '')
            ),
            'dueAt': item.get('dueAt', ''),
            'securityCategory': item.get('securityCategory', ''),
            'cve': item.get('cve', ''),
            'cwe': item.get('cwe', ''),
            'cvssScore': item.get('cvssScore', ''),
            'itemId': item.get('id', ''),
            'itemSourceId': item.get('itemSourceId', ''),
            'title': item.get('title', ''),
            'htmlUrl': item.get('htmlUrl', '')
        }
    
    def export_to_csv(self, items: List[Dict], output_file: str) -> None:
        """
        Export SRM items to a CSV file.
        
        Args:
            items: List of SRM items
            output_file: Path to the output CSV file
        """
        fieldnames = [
            'repository', 'projectKey', 'scanType', 'priority', 'confidence',
            'ruleId', 'ruleName', 'filePath', 'lineNumber', 'status',
            'openedAt', 'closedAt', 'timeToRemediate', 'dueAt', 'securityCategory', 'cve',
            'cwe', 'cvssScore', 'itemId', 'itemSourceId', 'title', 'htmlUrl'
        ]
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in items:
                writer.writerow(self._prepare_csv_row(item))
        
        print(f"CSV exported to: {output_file}", file=sys.stderr)
    
    def _fetch_page(self, cursor: Optional[str] = None, limit: int = 100) -> tuple:
        """
        Fetch a single page of SRM items.
        
        Args:
            cursor: Pagination cursor for the next page
            limit: Number of items per page
            
        Returns:
            Tuple of (items, next_cursor, total)
        """
        url = f"{self.BASE_URL}/organizations/{self.provider}/{self.organization}/security/items"
        
        params = {'limit': limit}
        if cursor:
            params['cursor'] = cursor
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            items = data.get('data', [])
            pagination = data.get('pagination', {})
            next_cursor = pagination.get('cursor')
            total = pagination.get('total', 0)
            
            return items, next_cursor, total
            
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}", file=sys.stderr)
            print(f"Response: {response.text}", file=sys.stderr)
            raise
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {e}", file=sys.stderr)
            raise
        except Exception as e:
            print(f"Unexpected Error: {e}", file=sys.stderr)
            raise


def print_summary(items: List[Dict]) -> None:
    """Print summary statistics for SRM items."""
    print(f"\n=== SRM Items Summary ===")
    print(f"Total items: {len(items)}")
    
    if not items:
        return
    
    # Count by status
    status_counts = {}
    for item in items:
        status = item.get('status', 'Unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"\nBy Status:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")
    
    # Count by priority
    priority_counts = {}
    for item in items:
        priority = item.get('priority', 'Unknown')
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
    
    print(f"\nBy Priority:")
    for priority, count in sorted(priority_counts.items()):
        print(f"  {priority}: {count}")
    
    # Count by scan type
    scantype_counts = {}
    for item in items:
        scan_type = item.get('scanType', 'Unknown')
        scantype_counts[scan_type] = scantype_counts.get(scan_type, 0) + 1
    
    print(f"\nBy Scan Type:")
    for scan_type, count in sorted(scantype_counts.items()):
        print(f"  {scan_type}: {count}")


def main():
    """Main entry point for the script."""
    import os
    
    # Get configuration from environment variables or command line arguments
    api_token = os.getenv('CODACY_API_TOKEN')
    provider = os.getenv('CODACY_PROVIDER', 'gh')
    organization = os.getenv('CODACY_ORGANIZATION')
    output_file = os.getenv('OUTPUT_FILE', f'srm_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    
    if not api_token:
        print("Error: CODACY_API_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    if not organization:
        print("Error: CODACY_ORGANIZATION environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    # Initialize the reporter
    reporter = CodacySRMReporter(api_token, provider, organization)
    
    # Fetch all SRM items
    try:
        items = reporter.fetch_all_srm_items()
        print_summary(items)
        
        # Export to CSV
        if items:
            reporter.export_to_csv(items, output_file)
            print(f"\n✓ Report generated: {output_file}")
        else:
            print("\nNo items to export.")
        
        return items
        
    except Exception as e:
        print(f"Failed to fetch SRM items: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
