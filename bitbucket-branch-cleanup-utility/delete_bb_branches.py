import requests
import time
from datetime import datetime, timedelta, timezone

# --- Configuration ---
WORKSPACE = "xxxxxxxxxx"
REPO_SLUG = "xxxxxxxxxx"
USERNAME  = "xxxxxxxxxx"
API_TOKEN = "xxxxxxxxxx"  # Needs 'Repo:Write' & 'PR:Read'
DRY_RUN = True  # Set to False to actually delete branches

# --- Constants ---
BASE_URL = f"https://api.bitbucket.org/2.0/repositories/{WORKSPACE}/{REPO_SLUG}"
headers = {
  "Accept": "application/json",
  "Authorization": f"Bearer {API_TOKEN}"
}

# --- Functions ---
def get_all_paginated(url):
    """Handles Bitbucket's pagination to fetch all items."""
    items = []
    while url:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Error fetching data: {response.text}")
            break
        data = response.json()
        items.extend(data.get('values', []))
        url = data.get('next') 
    return items

def cleanup():
    # 0. Calculate Cutoff Date (6 months ago)
    # Using UTC to ensure consistency with Bitbucket's timezone format
    six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
    print(f"Cutoff date set to: {six_months_ago.strftime('%Y-%m-%d')}")
    print("Branches older than this (without PRs) will be deleted.\n")

    # 1. Get the Default Branch
    repo_info = requests.get(BASE_URL, headers=headers).json()
    default_branch = repo_info.get('mainbranch', {}).get('name')
    print(f"Default branch identified as: {default_branch}")

    # 2. Get all branches with OPEN Pull Requests
    print("Fetching branches with open Pull Requests...")
    open_prs = get_all_paginated(f"{BASE_URL}/pullrequests?state=OPEN")
    # Store source branch names
    protected_by_pr = {pr['source']['branch']['name'] for pr in open_prs if pr['source']['branch']}
    print(f"Found {len(protected_by_pr)} branches protected by open PRs.")

    # 3. Fetch ALL branches
    print("Fetching all repository branches...")
    all_branches = get_all_paginated(f"{BASE_URL}/refs/branches")
    print(f"Total branches found: {len(all_branches)}")

    # 4. Filter and Delete
    deleted_count = 0
    
    print("-" * 40)
    for branch in all_branches:
        name = branch['name']
        
        # --- Rule 1: Keep Default Branch --- this one is not deletable
        if name == default_branch:
            continue
            
        # --- Rule 2: Keep Branches with Open PRs --- you're still working on them
        if name in protected_by_pr:
            print(f"[Keep] {name:<30} | Reason: Has open PR")
            continue

        # --- Rule 3: Check Branch Age (Last Commit Date) --- 
        # The 'target' key contains the commit info, including date
        last_commit_date_str = branch.get('target', {}).get('date')
        
        if last_commit_date_str:
            # Parse the ISO 8601 date string provided by Bitbucket
            last_commit_date = datetime.fromisoformat(last_commit_date_str)
            
            # If the branch is NEWER than 6 months, keep it
            if last_commit_date > six_months_ago:
                print(f"[Keep] {name:<30} | Reason: Recent activity ({last_commit_date.strftime('%Y-%m-%d')})")
                continue
        else:
            print(f"[Skip] {name:<30} | Reason: Could not determine date")
            continue

        # --- Execution: Delete Logic ---
        # If we reached here, the branch is old and has no PR
        if DRY_RUN:
            print(f"[Dry Run] Would delete: {name:<20} | Last modified: {last_commit_date.strftime('%Y-%m-%d')}")
        else:
            delete_url = f"{BASE_URL}/refs/branches/{name}"
            resp = requests.delete(delete_url, headers=headers)
            if resp.status_code == 204:
                print(f"[Deleted] {name}")
                deleted_count += 1
            else:
                print(f"[Error] Could not delete {name}: {resp.status_code}")
            
            time.sleep(0.1)

    print("-" * 40)
    print(f"\nTask Complete. Total branches deleted: {deleted_count}")

if __name__ == "__main__":
    cleanup()