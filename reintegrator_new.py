#!/usr/bin/env python3
"""
Codacy Integration Helper - API-based version
A rewrite of the original reintegrator.py to work with Codacy's SPA architecture.

This script reintegrates repositories with a different user account by using their API token.
For example, if a repository was integrated by John but should be owned by codacy_bot,
run this script with codacy_bot's token to change the integration ownership.

Supports GitLab (gl) and BitBucket (bb) providers only.
GitHub integration is handled through GitHub Apps.
Self-hosted providers are not supported in this cloud-specific version.
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

    def get_repository_integration_info(
            self, provider: str, organization: str, repository: str) -> Optional[Dict[str, Any]]:
        """Get repository integration information for logging purposes"""
        try:
            endpoint = f"/organizations/{provider}/{organization}/repositories/{repository}/integrations/providerSettings"
            response = self._make_request('GET', endpoint)
            return response.json()
        except requests.exceptions.RequestException:
            # Integration might not exist yet, which is fine
            return None

    def refresh_provider_integration(self,
                                     provider: str,
                                     organization: str,
                                     repository: str) -> Optional[Dict[str,
                                                                       Any]]:
        """Refresh provider integration for a repository - this changes the integration owner"""
        endpoint = f"/organizations/{provider}/{organization}/repositories/{repository}/integrations/refreshProvider"
        response = self._make_request('POST', endpoint, json={})
        # POST requests may return 204 No Content with empty body
        if response.status_code == 204:
            return None
        return response.json()


class IntegrationManager:
    """Manages repository integration ownership"""

    def __init__(self, client: CodacyAPIClient):
        self.client = client

    def get_integration_owner(
            self,
            provider: str,
            organization: str,
            repository: str) -> Optional[str]:
        """Get the current integration owner for logging purposes"""
        try:
            integration_info = self.client.get_repository_integration_info(
                provider, organization, repository)
            if integration_info:
                return integration_info.get('integratedBy', 'Unknown')
            return None
        except Exception as e:
            print(f"Could not get integration info for {repository}: {e}")
            return None

    def reintegrate_repository(
            self,
            provider: str,
            organization: str,
            repository: str) -> bool:
        """Reintegrate a single repository to change ownership"""
        print(f"\n--- Processing repository: {repository} ---")

        # Get current integration owner for logging
        current_owner = self.get_integration_owner(
            provider, organization, repository)
        if current_owner:
            print(f"Current integration owner: {current_owner}")
        else:
            print("No existing integration found or could not determine owner")

        # Refresh the integration (this changes ownership to the token owner)
        try:
            print(f"Reintegrating {repository} with new token owner...")
            self.client.refresh_provider_integration(
                provider, organization, repository)
            print(f"✓ Successfully reintegrated {repository}")

            # Optionally show new owner for confirmation
            new_owner = self.get_integration_owner(
                provider, organization, repository)
            if new_owner and new_owner != current_owner:
                print(f"New integration owner: {new_owner}")

            return True
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to reintegrate {repository}: {e}")
            return False

    def reintegrate_all(self,
                        provider: str,
                        organization: str,
                        target_repositories: Optional[List[str]] = None) -> Dict[str,
                                                                                 bool]:
        """Reintegrate all or specified repositories in an organization"""
        print(f"Starting reintegration for organization: {organization}")
        print(f"Provider: {provider}")
        print("This will change integration ownership to the account associated with the provided token")

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
                provider, organization, repo_name)
            results[repo_name] = success

        # Summary
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        print(f"\n=== Summary ===")
        print(f"Successfully reintegrated: {successful}/{total} repositories")

        if successful < total:
            failed_repos = [repo for repo,
                            success in results.items() if not success]
            print(f"Failed repositories: {', '.join(failed_repos)}")

        return results


def main():
    print('Codacy Integration Helper - API-based version')
    print('Changes repository integration ownership to the account associated with the provided token')

    parser = argparse.ArgumentParser(
        description='Codacy Integration Helper - Changes integration ownership')
    parser.add_argument(
        '--token',
        dest='token',
        required=True,
        help='Codacy API token for the account that should own the integrations')
    parser.add_argument('--provider', dest='provider', required=True,
                        help='Git provider (gl|bb)')
    parser.add_argument('--organization', dest='organization', required=True,
                        help='Organization name')
    parser.add_argument(
        '--which',
        dest='which',
        default=None,
        help='Comma-separated list of repositories to reintegrate (default: all)')

    args = parser.parse_args()

    # Validate provider
    valid_providers = ['gl', 'bb']
    if args.provider not in valid_providers:
        print(
            f"Error: Invalid provider '{args.provider}'. Must be one of: {', '.join(valid_providers)}")
        sys.exit(1)

    # Parse target repositories
    target_repositories = None
    if args.which:
        target_repositories = [repo.strip() for repo in args.which.split(',')]

    # Initialize API client and integration manager
    try:
        client = CodacyAPIClient('https://app.codacy.com', args.token)
        manager = IntegrationManager(client)

        # Run the reintegration
        results = manager.reintegrate_all(
            args.provider, args.organization, target_repositories)

        # Exit with appropriate code
        if all(results.values()):
            print("\n✓ All repositories reintegrated successfully!")
            sys.exit(0)
        else:
            print("\n✗ Some repositories failed to reintegrate")
            sys.exit(1)

    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
