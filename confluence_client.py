import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

def _get_creds(creds: dict | None):
    if creds:
        return creds["jira_url"], (creds["jira_email"], creds["jira_api_token"])
    return os.getenv("JIRA_URL"), (os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN"))


def get_confluence_spaces(creds: dict | None = None):
    base_url, auth = _get_creds(creds)
    url = f"{base_url}/wiki/rest/api/space"
    response = requests.get(url, auth=auth)
    spaces = []
    for space in response.json().get("results", []):
        if not space["key"].startswith("~"):
            spaces.append({
                "key": space["key"],
                "name": space["name"],
                "type": space["type"]
            })
    return spaces


def get_confluence_pages(space_keys=None, creds: dict | None = None):
    base_url, auth = _get_creds(creds)

    if not space_keys:
        all_spaces = get_confluence_spaces(creds=creds)
        space_keys = [s["key"] for s in all_spaces]

    if isinstance(space_keys, str):
        space_keys = [space_keys]

    all_pages = []
    for space_key in space_keys:
        print(f"Fetching pages from space: {space_key}")
        url = f"{base_url}/wiki/rest/api/content"
        params = {
            "type": "page",
            "spaceKey": space_key,
            "expand": "body.storage,space",
            "limit": 50
        }
        response = requests.get(url, auth=auth, params=params)
        for page in response.json().get("results", []):
            body = page.get("body", {}).get("storage", {}).get("value", "")
            clean_text = re.sub(r'<[^>]+>', ' ', body).strip()
            clean_text = re.sub(r'\s+', ' ', clean_text)
            if clean_text:
                all_pages.append({
                    "id": page["id"],
                    "title": page["title"],
                    "space_key": space_key,
                    "space_name": page["space"]["name"],
                    "content": clean_text,
                    "url": f"{base_url}/wiki{page['_links']['webui']}"
                })

    return all_pages
