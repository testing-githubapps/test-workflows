from github import Github
from git import Repo, GitCommandError
import os, logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Define environment variables
base_ghes_hostname = os.environ['BASE_GHES_HOSTNAME']
ghes_pat = os.environ['PAT_GHE']
ghec_pat = os.environ['PAT_GH']
source_repo = os.environ['SOURCE_REPO']
target_repo = os.environ['TARGET_REPO']
ghes_org = os.environ['GHES_ORG']

def clone_repo(repo_url, local_path):
    if not os.path.exists(local_path):
        logging.info(f"Cloning repository from {repo_url}")
        Repo.clone_from(repo_url, local_path)

def fetch_branch(repo, branch_name):
    repo.git.fetch('origin', branch_name)

def checkout_branch(repo, branch_name):
    if repo.is_dirty():
        logging.info(f"Uncommitted changes found in {branch_name}. Stashing changes.")
        repo.git.stash()

    if branch_name in repo.heads:
        # If the branch already exists, do a regular checkout
        logging.info(f"Branch {branch_name} already exists. Checking out.")
        repo.git.checkout(branch_name)
    else:
        # If the branch doesn't exist, create it and track the remote branch
        logging.info(f"Branch {branch_name} doesn't exist. Creating and checking out.")
        repo.git.checkout('-b', branch_name, '--track', f'origin/{branch_name}')

def push_branch(repo, remote_name, branch_name):
    if remote_name not in [remote.name for remote in repo.remotes]:
        repo.create_remote(remote_name, target_repo.clone_url)
        logging.info(f"Target repository set to {target_repo.clone_url}")
    logging.info(f"Pushing branch {branch_name} to target repository {target_repo.clone_url}")
    repo.git.push(remote_name, branch_name)

def cherry_pick_commits(repo, commits):
    for commit in commits:
        try:
            logging.info(f"Cherry-picking commit {commit}")
            repo.git.cherry_pick(commit)
        except GitCommandError:
            logging.warning(f"Conflict occurred while cherry-picking commit {commit}")
            conflicted_files = repo.git.diff('--name-only', '--diff-filter=U')
            conflicted_files = conflicted_files.split('\n')
            for file in conflicted_files:
                if not file:
                    continue
                repo.git.checkout('--theirs', file)
                repo.git.add(file)

def create_pull_request(repo, source_pr, base, head):
    body = source_pr.body if source_pr.body is not None else ""
    repo.create_pull(title=source_pr.title, body=body, base=base, head=head)

def migrate_comments(source_pr, target_pr):
    logging.info(f"Migrating comments for pull request {source_pr.number}")
    for comment in source_pr.get_issue_comments():
        target_pr.create_issue_comment(comment.body)

def migrate_reviewers(source_pr, target_pr):
    for reviewer in source_pr.get_review_requests()[0]:
        try:
            target_pr.create_review_request(reviewers=[reviewer.login])
        except:
            logging.warning(f"Unable to add reviewer {reviewer.login}")

# Create a Github instance with your GitHub Enterprise Server URL
ge = Github(base_url=f"https://{base_ghes_hostname}/api/v3", login_or_token=ghes_pat)
ghes_repo_url = f"https://{ghes_pat}@{base_ghes_hostname}/{source_repo}.git"

# Create a Github Cloud instance
g = Github(ghec_pat)

# Get the source and target repositories
source_repo = ge.get_repo(f"{source_repo}")
target_repo = g.get_repo(f"{target_repo}")

# Local path to clone the source and target repository
local_source_repo_path = f"../{source_repo.name}"
local_target_repo_path = f"../{target_repo.name}"

# Clone the source and target repository if they're not already cloned
clone_repo(ghes_repo_url, local_source_repo_path)
clone_repo(target_repo.clone_url, local_target_repo_path)

# Create a Repo object for the source and target repository
local_source_repo = Repo(local_source_repo_path)
local_target_repo = Repo(local_target_repo_path)

# Fetch all branches from the source repository
source_branches = [ref.name for ref in source_repo.get_branches()]

# Get the branches of the target repository
target_branches = [branch.name for branch in target_repo.get_branches()]

# For each branch
for branch_name in source_branches:
    # Skip the branch if it already exists in the target repository
    if branch_name in target_branches:
        logging.info(f"Branch {branch_name} already exists in target repository. Skipping.")
        continue

    # Fetch the branch from the source repository
    fetch_branch(local_source_repo, branch_name)

    # Checkout the branch
    checkout_branch(local_source_repo, branch_name)

    # Add the target repository as a remote
    if 'target' not in [remote.name for remote in local_source_repo.remotes]:
        local_source_repo.create_remote('target', target_repo.clone_url)
        logging.info(f"Target repository set to {target_repo.clone_url}")

    # Push the branch to the target repository
    push_branch(local_source_repo, 'target', branch_name)

    # Get the default branch of the source repository
    default_branch = source_repo.default_branch

# Set the default branch of the target repository
target_repo.edit(default_branch=default_branch)

# Fetch all pull requests from the source repository
source_prs = source_repo.get_pulls(state='open')

# For each pull request
for source_pr in source_prs:
    # Get the commits from the pull request
    commits = [commit.sha for commit in source_pr.get_commits()]

    # Get the branch name
    branch_name = f"{source_pr.head.ref}"
    logging.info(f"Processing branch {branch_name}")

    # Fetch the remote changes
    fetch_branch(local_target_repo, branch_name)

    # Check for uncommitted changes and stash them if any
    checkout_branch(local_target_repo, branch_name)

    # Cherry-pick the commits
    cherry_pick_commits(local_target_repo, commits)

    # Create a new pull request in the target repository
    logging.info(f"Creating pull request for branch {branch_name}")
    target_pr = create_pull_request(target_repo, source_pr, 'main', branch_name)
