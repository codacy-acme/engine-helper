import os
import requests
import time
import argparse
import logging
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration (Loaded from Environment) ---
WORKSPACE = os.getenv("BITBUCKET_WORKSPACE")
USERNAME  = os.getenv("BITBUCKET_USERNAME")
REPO_SLUG = os.getenv("BITBUCKET_REPO_SLUG")
ACCESS_TOKEN = os.getenv("BITBUCKET_ACCESS_TOKEN")

# Default Config (Can be overridden via arguments)
DEFAULT_CUT_OFF_DAYS = 180
WHITELIST = ['develop', 'production']

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- Constants ---
BASE_URL = f"https://api.bitbucket.org/2.0/repositories/{WORKSPACE}/{REPO_SLUG}"
HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

def get_all_paginated(url):
    """Handles Bitbucket's pagination to fetch all items."""
    items = []
    while url:
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
            items.extend(data.get('values', []))
            url = data.get('next')
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch data from {url}: {e}")
            return []
    return items

def cleanup(dry_run=True, days=DEFAULT_CUT_OFF_DAYS):
    if not all([WORKSPACE, USERNAME, REPO_SLUG, ACCESS_TOKEN]):
        logger.error("Missing configuration. Please ensure .env file contains WORKSPACE, USERNAME, REPO_SLUG, and ACCESS_TOKEN.")
        return

    logger.info(f"Starting cleanup for {WORKSPACE}/{REPO_SLUG}")
    logger.info(f"Mode: {'DRY RUN (No changes)' if dry_run else 'DESTRUCTIVE (Will delete)'}")

    # 0. Calculate Cutoff Date
    cut_off_date = datetime.now(timezone.utc) - timedelta(days=days)
    logger.info(f"Cutoff date: {cut_off_date.strftime('%Y-%m-%d')} ({days} days ago)")

    # 1. Get the Default Branch
    try:
        repo_info = requests.get(BASE_URL, headers=HEADERS, timeout=10).json()
        default_branch = repo_info.get('mainbranch', {}).get('name')
        logger.info(f"Default branch: {default_branch}")
    except Exception as e:
        logger.error(f"Could not fetch repository info: {e}")
        return

    # 2. Get all branches with OPEN Pull Requests
    logger.info("Fetching open Pull Requests...")
    open_prs = get_all_paginated(f"{BASE_URL}/pullrequests?state=OPEN")
    protected_by_pr = {pr['source']['branch']['name'] for pr in open_prs if pr['source']['branch']}
    logger.info(f"Branches protected by open PRs: {len(protected_by_pr)}")

    # 3. Fetch ALL branches
    logger.info("Fetching all repository branches...")
    all_branches = get_all_paginated(f"{BASE_URL}/refs/branches")
    logger.info(f"Total branches found: {len(all_branches)}")

    deleted_count = 0
    
    print("-" * 60)
    for branch in all_branches:
        name = branch['name']
        
        # Rule 1: Default or Whitelisted
        if name == default_branch or name in WHITELIST:
            logger.info(f"[KEEP] {name:<30} | Whitelisted/Default")
            continue
            
        # Rule 2: Open PRs
        if name in protected_by_pr:
            logger.info(f"[KEEP] {name:<30} | Has Open PR")
            continue

        # Rule 3: Branch Age
        last_commit_date_str = branch.get('target', {}).get('date')
        if not last_commit_date_str:
            logger.warning(f"[KEEP] {name:<30} | No date found")
            continue

        last_commit_date = datetime.fromisoformat(last_commit_date_str)

        if last_commit_date > cut_off_date:
            logger.info(f"[KEEP] {name:<30} | Active ({last_commit_date.strftime('%Y-%m-%d')})")
            continue

        # Rule 4: Deletion
        if dry_run:
            logger.info(f"[DRY-RUN DELETE] {name:<20} | Inactive since {last_commit_date.strftime('%Y-%m-%d')}")
        else:
            delete_url = f"{BASE_URL}/refs/branches/{name}"
            try:
                resp = requests.delete(delete_url, headers=HEADERS, timeout=10)
                if resp.status_code == 204:
                    logger.info(f"[DELETED] {name}")
                    deleted_count += 1
                else:
                    logger.error(f"[ERROR] Failed to delete {name}: {resp.status_code}")
            except Exception as e:
                logger.error(f"[ERROR] Exception deleting {name}: {e}")
            
            time.sleep(0.2) # Rate limit protection

    print("-" * 60)
    logger.info(f"Cleanup Complete. Total branches deleted: {deleted_count}")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Bitbucket Branch Cleanup Utility")
    
    # Arguments
    parser.add_argument('--force', action='store_true', help="Execute actual deletion (Disable Dry Run)")
    parser.add_argument('--days', type=int, default=DEFAULT_CUT_OFF_DAYS, help="Days of inactivity before deletion (default: 180)")
    
    args = parser.parse_args()
    
    # Logic inversion for clarity: The function expects `dry_run=True` by default.
    # Passing --force makes dry_run=False.
    cleanup(dry_run=not args.force, days=args.days)