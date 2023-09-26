
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from dotenv import load_dotenv
import os

# Load the environment variables from the .env file
load_dotenv()

# Specify the source and destination repository details
source_token = os.getenv("GHES_TOKEN")
dest_token = os.getenv("GHEC_TOKEN")

# Specify the repository details
source_name = "benjamins/testing-issues"
dest_name = "testing-githubapps/issue-test"

# GraphQL API endpoint URLs for source and destination instances
source_endpoint = os.getenv("GHES_HOST") + "/api/graphql"
dest_endpoint = "https://api.github.com/graphql"

# Create a GraphQL client for the source and destination instances
def create_graphql_client(token, endpoint):
  transport = RequestsHTTPTransport(
    url=endpoint,
    headers={
      "Authorization": "Bearer " + token,
      "Accept": "application/vnd.github.starfire-preview+json"
    },
    use_json=True
  )
  return Client(
    transport=transport,
    fetch_schema_from_transport=True,
  )

def run_query(client, query, variables):
    return client.execute(gql(query), variable_values=variables)

source_client = create_graphql_client(source_token, source_endpoint)
dest_client = create_graphql_client(dest_token, dest_endpoint)

# Get destination repository ID
def getRepoId(client, name):
  query = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        id
      }
    }
  """

  variables = {
    "owner": name.split("/")[0],
    "name": name.split("/")[1]
  }

  return run_query(client, query, variables)

# Get the source and destination repositories

# Fetch source project(s), columns and cards and create the corresponding project(s) on the destination 
def getSourceProjects(client, name):
  query = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        projects(first: 10) {
          nodes {
            name
            body
            columns(first: 10) {
              nodes {
                name
                cards(first: 10) {
                  nodes {
                    note
                    content {
                      ... on Issue {
                        title
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  """

  variables = {
    "owner": name.split("/")[0],
    "name": name.split("/")[1]
  }

  return run_query(client, query, variables)

def createDestProject(client, repo_id, name, body):
  create_project_mutation = """
  mutation createProject($name: String!, $ownerId: ID!) {
    createProject(input: {name: $name, ownerId: $ownerId}) {
      project {
        id
        name
      }
    }
  }
  """

  variables = {
    "name": name,
    "ownerId": repo_id
  }

  return run_query(client, create_project_mutation, variables)

def create_column(client, project_id, name):
  create_column_mutation = """
  mutation createColumn($projectId: ID!, $columnName: String!) {
    addProjectColumn(input: {projectId: $projectId, name: $columnName}) {
      columnEdge {
        node {
          id
          name
        }
      }
    }
  }
  """


  variables = {
    "projectId": project_id,
    "columnName": name
  }

  return run_query(client, create_column_mutation, variables)

def create_card(client, column_id, note):
  create_card_mutation = """
  mutation createCard($columnId: ID!, $note: String!) {
    addProjectCard(input: {projectColumnId: $columnId, note: $note}) {
      projectColumn{
        cards{
          nodes{
            id
          }
        }
      }
    }
  }
  """

  variables = {
    "columnId": column_id,
    "note": note
  }

  return run_query(client, create_card_mutation, variables)

# validate card if issue or note
def validate_card(card):
  if card["note"] == None:
    card["note"] = card["content"]["title"]
  return card

def migrate_projects(source_name, dest_name):
  # Get the list of issues from the repository
  source_projects = getSourceProjects(source_client, source_name)

  # add issues to new repo and verify if component are existant
  for project in source_projects["repository"]["projects"]["nodes"]:
    try:
      dest_repo_id = getRepoId(dest_client, dest_name)
      dest_project = createDestProject(dest_client, dest_repo_id["repository"]["id"], project["name"], project["body"])
      print(f"Created project {project['name']} on {dest_name} as project #{dest_project['createProject']['project']['id']}")
      for column in project["columns"]["nodes"]:
        dest_column = create_column(dest_client, dest_project["createProject"]["project"]["id"], column["name"])
        print(f"Created column {column['name']} on {dest_name} as column #{dest_column['addProjectColumn']['columnEdge']['node']['id']}")
        for card in column["cards"]["nodes"]:
          card = validate_card(card)
          dest_card = create_card(dest_client, dest_column["addProjectColumn"]["columnEdge"]["node"]["id"], card["note"])
          print(f"Created card {card['note']} on {dest_name} as card #{dest_card['addProjectCard']['projectColumn']['cards']['nodes'][0]['id']}")
    except Exception as error:
      print(f"Error creating project {project['name']} on {dest_name}")
      print(error)

# Specify the repository details
source_name = "benjamins/testing-issues"
dest_name = "testing-githubapps/issue-test"

migrate_projects(source_name, dest_name)