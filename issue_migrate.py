from github import Github, GithubObject, Auth
from dotenv import load_dotenv
import os

# Load the environment variables from the .env file
load_dotenv()

source_auth = Auth.Token(os.getenv("GHES_TOKEN"))
dest_auth = Auth.Token(os.getenv("GHEC_TOKEN"))

# Create a PyGithub instance by providing an access token or username/password
source_github = Github(base_url=os.getenv("GHES_HOST") + "/api/v3", auth=source_auth)
dest_github = Github(auth=dest_auth)

# create a function to filter assignees and add it to the body the issue
def filter_assignees(dest_repo, assignees, body):
  assignees_list = []
  body = body +  "\n\n**Assignees:**" if body else "**Assignees:**" if assignees else ""
  for assignee in assignees:
    try:
      dest_repo.get_user(assignee.login)
      print({assignee.login} + " exists")
      assignees_list.append(assignee.login)
    except:
      body = body + f"\nUsername: {assignee.login} {'Email: ' + assignee.email if assignee.email else ''}"
      print(f"{assignee.login} does not exist adding to description of issue")
  return assignees_list, body

def migrate_issues(source_name, dest_name):
  # Get the repository object
  source_repo = source_github.get_repo(source_name)
  dest_repo = dest_github.get_repo(dest_name)

  # Get the list of issues from the repository
  source_issues = source_repo.get_issues()

  # add issues to new repo and verify if component are existant
  for issue in source_issues:
    try:
      filtered_assignees, body = filter_assignees(dest_repo, issue.assignees, issue.body)
      new_issue = dest_repo.create_issue(
        title = issue.title if issue.title else GithubObject.NotSet,
        body = body if body else GithubObject.NotSet,
        labels = issue.labels if issue.labels else GithubObject.NotSet,
        milestone = issue.milestone if issue.milestone else GithubObject.NotSet,
        assignees = filtered_assignees if filtered_assignees else GithubObject.NotSet,
        )
      print(f"Created issue {issue.title} on {dest_name} as issue #{new_issue.number}")
    except Exception as error:
      print(f"Error creating issue {issue.title} on {dest_name}")
      print(error)

# Specify the repository details
source_name = "benjamins/testing-issues"
dest_name = "testing-githubapps/issue-test"

migrate_issues(source_name, dest_name)