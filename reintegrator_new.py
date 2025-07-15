#!/usr/bin/env python3
"""
Codacy Integration Helper - API-based version
A rewrite of the original reintegrator.py to work with Codacy's SPA architecture
using the official REST API instead of web scraping.
"""

import argparse
import requests
import sys
from typing import Dict, List, Optional, Any


class CodacyAPIClient:
    """Client for interacting with Codacy's REST API"""

    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'api-token': api_token
        })

    def _make_request(
            self,
            method: str,
            endpoint: str,
            **kwargs) -> requests.Response:
        """Make an API request with error handling"""
        url = f"{self.base_url}/api/v3{endpoint}"

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {method} {url}")
            print(f"Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            raise

    def list_repositories(self, provider: str,
                          organization: str) -> List[Dict[str, Any]]:
        """List all repositories in an organization"""
        repositories = []
        cursor = ''

        while True:
            endpoint = f"/organizations/{provider}/{organization}/repositories"
            params = {'limit': 100}
            if cursor:
                params['cursor'] = cursor

            response = self._make_request('GET', endpoint, params=params)
            data = response.json()

            repositories.extend(data.get('data', []))

            pagination = data.get('pagination', {})
            if 'cursor' not in pagination:
                break
            cursor = pagination['cursor']

        return repositories

    def get_organization_integration_settings(
            self, provider: str, organization: str) -> Dict[str, Any]:
        """Get organization-level integration settings"""
        endpoint = f"/organizations/{provider}/{organization}/integrations/providerSettings"
        response = self._make_request('GET', endpoint)
        return response.json()

    def get_repository_integration_settings(
            self, provider: str, organization: str, repository: str) -> Dict[str, Any]:
        """Get repository-level integration settings"""
        endpoint = f"/organizations/{provider}/{organization}/repositories/{repository}/integrations/providerSettings"
        response = self._make_request('GET', endpoint)
        return response.json()

    def update_organization_integration_settings(
            self, provider: str, organization: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Update organization-level integration settings"""
        endpoint = f"/organizations/{provider}/{organization}/integrations/providerSettings"
        response = self._make_request('PATCH', endpoint, json=settings)
        return response.json()

    def update_repository_integration_settings(self,
                                               provider: str,
                                               organization: str,
                                               repository: str,
                                               settings: Dict[str,
                                                              Any]) -> Dict[str,
                                                                            Any]:
        """Update repository-level integration settings"""
        endpoint = f"/organizations/{provider}/{organization}/repositories/{repository}/integrations/providerSettings"
        response = self._make_request('PATCH', endpoint, json=settings)
        return response.json()

    def refresh_provider_integration(
            self, provider: str, organization: str, repository: str) -> Dict[str, Any]:
        """Refresh provider integration for a repository"""
        endpoint = f"/organizations/{provider}/{organization}/repositories/{repository}/integrations/refreshProvider"
        response = self._make_request('POST', endpoint, json={})
        return response.json()


class IntegrationManager:
    """Manages integration settings for repositories"""

    # Provider-specific default settings
    PROVIDER_SETTINGS = {
        'gh': {  # GitHub
            'commitStatus': True,
            'pullRequestComment': True,
            'pullRequestSummary': True,
            'suggestions': True,
            'aiEnhancedComments': False
        },
        'gl': {  # GitLab
            'commitStatus': True,
            'pullRequestComment': True,
            'pullRequestSummary': False,  # GitHub only
            'suggestions': False,  # GitHub only
            'aiEnhancedComments': True
        },
        'bb': {  # Bitbucket
            'commitStatus': True,
            'pullRequestComment': True,
            'pullRequestSummary': False,  # GitHub only
            'suggestions': False,  # GitHub only
            'aiEnhancedComments': True
        },
        'ghe': {  # GitHub Enterprise
            'commitStatus': True,
            'pullRequestComment': True,
            'pullRequestSummary': True,
            'suggestions': True,
            'aiEnhancedComments': False
        },
        'gle': {  # GitLab Enterprise
            'commitStatus': True,
            'pullRequestComment': True,
            'pullRequestSummary': False,  # GitHub only
            'suggestions': False,  # GitHub only
            'aiEnhancedComments': True
        },
        'bbe': {  # Bitbucket Enterprise (Stash)
            'commitStatus': True,
            'pullRequestComment': True,
            'pullRequestSummary': False,  # GitHub only
            'suggestions': False,  # GitHub only
            'aiEnhancedComments': True
        }
    }

    def __init__(self, client: CodacyAPIClient):
        self.client = client

    def get_current_settings(self,
                             provider: str,
                             organization: str,
                             repository: str) -> Optional[Dict[str,
                                                               Any]]:
        """Get current integration settings for a repository"""
        try:
            return self.client.get_repository_integration_settings(
                provider, organization, repository)
        except requests.exceptions.RequestException as e:
            print(f"Failed to get settings for {repository}: {e}")
            return None

    def update_integration_settings(self,
                                    provider: str,
                                    organization: str,
                                    repository: str,
                                    custom_settings: Optional[Dict[str,
                                                                   Any]] = None) -> bool:
        """Update integration settings for a repository"""
        try:
            # Get default settings for the provider
            default_settings = self.PROVIDER_SETTINGS.get(
                provider, self.PROVIDER_SETTINGS['gh'])

            # Use custom settings if provided, otherwise use defaults
            settings_to_apply = custom_settings if custom_settings else default_settings

            # Prepare the request body
            request_body = {
                'settings': settings_to_apply
            }

            print(f"Updating integration settings for {repository}...")
            print(f"Settings: {settings_to_apply}")

            # Update the settings
            self.client.update_repository_integration_settings(
                provider, organization, repository, request_body
            )

            print(f"✓ Successfully updated settings for {repository}")
            return True

        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to update settings for {repository}: {e}")
            return False

    def refresh_integration(
            self,
            provider: str,
            organization: str,
            repository: str) -> bool:
        """Refresh provider integration for a repository"""
        try:
            print(f"Refreshing integration for {repository}...")
            self.client.refresh_provider_integration(
                provider, organization, repository)
            print(f"✓ Successfully refreshed integration for {repository}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to refresh integration for {repository}: {e}")
            return False

    def reintegrate_repository(self,
                               provider: str,
                               organization: str,
                               repository: str,
                               custom_settings: Optional[Dict[str,
                                                              Any]] = None) -> bool:
        """Reintegrate a single repository with new settings"""
        print(f"\n--- Processing repository: {repository} ---")

        # Get current settings (for informational purposes)
        current_settings = self.get_current_settings(
            provider, organization, repository)
        if current_settings:
            print(f"Current settings: {current_settings.get('settings', {})}")

        # Update integration settings
        settings_updated = self.update_integration_settings(
            provider, organization, repository, custom_settings)

        # Refresh the integration
        integration_refreshed = self.refresh_integration(
            provider, organization, repository)

        success = settings_updated and integration_refreshed
        if success:
            print(f"✓ Successfully reintegrated {repository}")
        else:
            print(f"✗ Failed to reintegrate {repository}")

        return success

    def reintegrate_all(self,
                        provider: str,
                        organization: str,
                        target_repositories: Optional[List[str]] = None,
                        custom_settings: Optional[Dict[str,
                                                       Any]] = None) -> Dict[str,
                                                                             bool]:
        """Reintegrate all or specified repositories in an organization"""
        print(f"Starting reintegration for organization: {organization}")
        print(f"Provider: {provider}")

        # Get list of repositories
        try:
            repositories = self.client.list_repositories(
                provider, organization)
            print(f"Found {len(repositories)} repositories")
        except requests.exceptions.RequestException as e:
            print(f"Failed to list repositories: {e}")
            return {}

        # Filter repositories if specific ones are requested
        if target_repositories:
            repositories = [
                repo for repo in repositories if repo['name'] in target_repositories]
            print(f"Filtering to {len(repositories)} specified repositories")

        # Process each repository
        results = {}
        for repo in repositories:
            repo_name = repo['name']
            success = self.reintegrate_repository(
                provider, organization, repo_name, custom_settings)
            results[repo_name] = success

        # Summary
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        print(f"\n=== Summary ===")
        print(f"Successfully processed: {successful}/{total} repositories")

        if successful < total:
            failed_repos = [repo for repo,
                            success in results.items() if not success]
            print(f"Failed repositories: {', '.join(failed_repos)}")

        return results


def main():
    print('Codacy Integration Helper - API-based version')
    print('A modern replacement for the web-scraping based reintegrator')

    parser = argparse.ArgumentParser(
        description='Codacy Integration Helper - API Version')
    parser.add_argument('--token', dest='token', required=True,
                        help='Codacy API token for authentication')
    parser.add_argument('--provider', dest='provider', required=True,
                        help='Git provider (gh|gl|bb|ghe|gle|bbe)')
    parser.add_argument('--organization', dest='organization', required=True,
                        help='Organization name')
    parser.add_argument(
        '--baseurl',
        dest='baseurl',
        default='https://app.codacy.com',
        help='Codacy server address (default: https://app.codacy.com)')
    parser.add_argument(
        '--which',
        dest='which',
        default=None,
        help='Comma-separated list of repositories to update (default: all)')
    parser.add_argument(
        '--commit-status',
        dest='commit_status',
        action='store_true',
        help='Enable commit status checks')
    parser.add_argument(
        '--no-commit-status',
        dest='commit_status',
        action='store_false',
        help='Disable commit status checks')
    parser.add_argument(
        '--pr-comments',
        dest='pr_comments',
        action='store_true',
        help='Enable pull request comments')
    parser.add_argument(
        '--no-pr-comments',
        dest='pr_comments',
        action='store_false',
        help='Disable pull request comments')
    parser.add_argument('--pr-summary', dest='pr_summary', action='store_true',
                        help='Enable pull request summary (GitHub only)')
    parser.add_argument(
        '--no-pr-summary',
        dest='pr_summary',
        action='store_false',
        help='Disable pull request summary')
    parser.add_argument(
        '--suggestions',
        dest='suggestions',
        action='store_true',
        help='Enable suggestions (GitHub only)')
    parser.add_argument(
        '--no-suggestions',
        dest='suggestions',
        action='store_false',
        help='Disable suggestions')

    parser.set_defaults(
        commit_status=None,
        pr_comments=None,
        pr_summary=None,
        suggestions=None)

    args = parser.parse_args()

    # Validate provider
    valid_providers = ['gh', 'gl', 'bb', 'ghe', 'gle', 'bbe']
    if args.provider not in valid_providers:
        print(
            f"Error: Invalid provider '{args.provider}'. Must be one of: {', '.join(valid_providers)}")
        sys.exit(1)

    # Parse target repositories
    target_repositories = None
    if args.which:
        target_repositories = [repo.strip() for repo in args.which.split(',')]

    # Build custom settings if any flags were provided
    custom_settings = {}
    if args.commit_status is not None:
        custom_settings['commitStatus'] = args.commit_status
    if args.pr_comments is not None:
        custom_settings['pullRequestComment'] = args.pr_comments
    if args.pr_summary is not None:
        custom_settings['pullRequestSummary'] = args.pr_summary
    if args.suggestions is not None:
        custom_settings['suggestions'] = args.suggestions

    # Use custom settings only if any were provided
    settings_to_use = custom_settings if custom_settings else None

    # Initialize API client and integration manager
    try:
        client = CodacyAPIClient(args.baseurl, args.token)
        manager = IntegrationManager(client)

        # Run the reintegration
        results = manager.reintegrate_all(
            args.provider,
            args.organization,
            target_repositories,
            settings_to_use
        )

        # Exit with appropriate code
        if all(results.values()):
            print("\n✓ All repositories processed successfully!")
            sys.exit(0)
        else:
            print("\n✗ Some repositories failed to process")
            sys.exit(1)

    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
