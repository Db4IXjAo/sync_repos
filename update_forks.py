#!/usr/bin/env python3
import configparser
import subprocess
import sys
import time

def run_command(cmd, cwd=None):
    print("Running command:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"Command {' '.join(cmd)} failed with exit code {result.returncode}")
        sys.exit(result.returncode)

def fork_exists(own_repo):
    # Check if the fork exists using gh repo view
    result = subprocess.run(["gh", "repo", "view", own_repo],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode == 0

def create_fork(remote_repo):
    # Create fork using gh; this command creates the fork in your account.
    cmd = ["gh", "repo", "fork", remote_repo, "--clone=false", "--remote"]
    run_command(cmd)
    print(f"Fork creation initiated for {remote_repo}")

def sync_fork(own_repo, branch):
    # Sync the fork with upstream using gh repo sync.
    cmd = ["gh", "repo", "sync", own_repo, "--branch", branch, "--force"]
    run_command(cmd)
    print(f"Synced fork {own_repo} on branch {branch}")

def main():
    config = configparser.ConfigParser()
    config.read("repo.conf")
    
    for section in config.sections():
        remote_repo = config[section].get("remote_repo")
        own_repo = config[section].get("own_repo")
        branch = config[section].get("branch", "master")
        if not remote_repo or not own_repo:
            print(f"Skipping section {section} (missing remote_repo or own_repo)")
            continue

        print(f"\nProcessing {section}: {remote_repo} -> {own_repo} (branch: {branch})")
        
        if not fork_exists(own_repo):
            print(f"Fork {own_repo} does not exist. Creating fork...")
            create_fork(remote_repo)
            # Wait briefly for GitHub to create the fork.
            time.sleep(10)
        else:
            print(f"Fork {own_repo} already exists.")

        sync_fork(own_repo, branch)

if __name__ == "__main__":
    main()
