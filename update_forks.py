#!/usr/bin/env python3
import configparser
import os
import requests
import subprocess
import sys
import tempfile
import time

# GitHub API endpoint
GITHUB_API = "https://api.github.com"

def get_headers(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def fork_exists(own_repo, headers):
    url = f"{GITHUB_API}/repos/{own_repo}"
    response = requests.get(url, headers=headers)
    return response.status_code == 200

def create_fork(remote_repo, headers):
    url = f"{GITHUB_API}/repos/{remote_repo}/forks"
    response = requests.post(url, headers=headers)
    if response.status_code in (202, 201):
        print(f"Fork creation initiated for {remote_repo}")
    else:
        print(f"Failed to create fork for {remote_repo}: {response.status_code} {response.text}")

def sync_fork(remote_repo, own_repo, branch, token):
    # Construct URLs. When cloning, we embed the token to allow push access.
    fork_url = f"https://{token}:x-oauth-basic@github.com/{own_repo}.git"
    upstream_url = f"https://github.com/{remote_repo}.git"

    # Create a temporary directory to clone the fork
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = os.path.join(tmpdir, own_repo.split('/')[-1])
        print(f"Cloning fork {own_repo} into {repo_dir}")
        subprocess.run(["git", "clone", fork_url, repo_dir], check=True)

        # Change directory to the cloned repository
        os.chdir(repo_dir)

        # Add the upstream remote (if not already added)
        subprocess.run(["git", "remote", "add", "upstream", upstream_url], check=False)
        print(f"Fetching upstream from {remote_repo}")
        subprocess.run(["git", "fetch", "upstream"], check=True)

        # Checkout the branch and reset it to match upstream
        subprocess.run(["git", "checkout", branch], check=True)
        subprocess.run(["git", "reset", "--hard", f"upstream/{branch}"], check=True)

        # Push the updated branch to the fork (force update)
        subprocess.run(["git", "push", "origin", branch, "--force"], check=True)
        print(f"Synchronized fork {own_repo} with upstream {remote_repo} on branch {branch}")

def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set.")
        sys.exit(1)

    headers = get_headers(token)

    # Parse the configuration file (repo.conf should be in the root of your repository)
    config = configparser.ConfigParser()
    config.read("repo.conf")

    for section in config.sections():
        remote_repo = config[section].get("remote_repo")
        own_repo = config[section].get("own_repo")
        branch = config[section].get("branch", "master")
        if not remote_repo or not own_repo:
            print(f"Skipping section {section} due to missing remote_repo or own_repo")
            continue

        print(f"\nProcessing {section}: {remote_repo} -> {own_repo} on branch {branch}")
        if not fork_exists(own_repo, headers):
            print(f"Fork {own_repo} does not exist. Creating fork...")
            create_fork(remote_repo, headers)
            # Wait a short time for GitHub to create the fork
            time.sleep(10)
        try:
            sync_fork(remote_repo, own_repo, branch, token)
        except subprocess.CalledProcessError as e:
            print(f"Error syncing fork {own_repo}: {e}")

if __name__ == "__main__":
    main()
