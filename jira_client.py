import requests
import os
from dotenv import load_dotenv

load_dotenv()

def _get_creds(creds: dict | None):
    """Fall back to .env if no user credentials passed (for local dev)."""
    if creds:
        return creds["jira_url"], (creds["jira_email"], creds["jira_api_token"])
    return os.getenv("JIRA_URL"), (os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN"))


def get_jira_projects(creds: dict | None = None):
    base_url, auth = _get_creds(creds)
    url = f"{base_url}/rest/api/3/project"
    response = requests.get(url, auth=auth)
    projects = []
    for project in response.json():
        projects.append({
            "key": project["key"],
            "name": project["name"]
        })
    return projects


def get_jira_tickets(max_results=5, project_key=None, creds: dict | None = None):
    base_url, auth = _get_creds(creds)
    key = project_key or os.getenv("JIRA_PROJECT_KEY", "")
    url = f"{base_url}/rest/api/3/search/jql"
    params = {
        "jql": f"project={key} ORDER BY created DESC",
        "maxResults": max_results,
        "fields": "summary,description,priority,status"
    }
    response = requests.get(url, auth=auth, params=params)
    tickets = []
    for issue in response.json().get("issues", []):
        fields = issue.get("fields") or {}

        description = ""
        desc_field = fields.get("description")
        if desc_field and "content" in desc_field:
            for block in desc_field["content"]:
                for inline in block.get("content", []):
                    if inline.get("type") == "text":
                        description += inline.get("text", "")

        priority_field = fields.get("priority") or {}
        status_field = fields.get("status") or {}

        tickets.append({
            "id": issue.get("key", "UNKNOWN"),
            "summary": fields.get("summary", "No summary"),
            "description": description or "No description",
            "priority": priority_field.get("name", "Unknown"),
            "status": status_field.get("name", "Unknown")
        })
    return tickets
