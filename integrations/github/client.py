"""
GitHub API Integration

Handles:
- Projects (Kanban boards)
- Issues and Pull Requests
- Webhooks
- Actions
"""

import os
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from integrations.base import BaseIntegration, WebhookHandler, WebhookEvent
from hashing import sha256, verify_github_webhook


@dataclass
class GitHubConfig:
    """GitHub configuration."""
    token: str
    owner: str = ""
    repo: str = ""


class GitHubClient(BaseIntegration):
    """
    GitHub API client.

    Environment variables:
    - GITHUB_TOKEN: Personal access token or GitHub App token
    - GITHUB_OWNER: Repository owner
    - GITHUB_REPO: Repository name

    Usage:
        client = GitHubClient()
        if client.authenticate():
            prs = client.list_pull_requests()
            client.create_issue("Bug report", "Description...")
    """

    BASE_URL = "https://api.github.com"
    GRAPHQL_URL = "https://api.github.com/graphql"

    def __init__(self):
        super().__init__("github")
        self.config = GitHubConfig(
            token=os.environ.get("GITHUB_TOKEN", ""),
            owner=os.environ.get("GITHUB_OWNER", "BlackRoad-OS"),
            repo=os.environ.get("GITHUB_REPO", "api"),
        )
        self._headers = {}

    def authenticate(self) -> bool:
        """Set up authentication headers."""
        if not self.config.token:
            print("[github] ERROR: GITHUB_TOKEN not set")
            return False

        self._headers = {
            "Authorization": f"Bearer {self.config.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self._authenticated = True
        return True

    def health_check(self) -> bool:
        """Verify API connectivity."""
        return bool(self.config.token)

    def get_state(self) -> Dict[str, Any]:
        """Get client state summary."""
        return {
            "service": "github",
            "authenticated": self._authenticated,
            "owner": self.config.owner,
            "repo": self.config.repo,
        }

    def _repo_url(self) -> str:
        return f"{self.BASE_URL}/repos/{self.config.owner}/{self.config.repo}"

    # -------------------------------------------------------------------------
    # Issues
    # -------------------------------------------------------------------------

    def list_issues(self, state: str = "open", labels: Optional[List[str]] = None) -> List[Dict]:
        """List repository issues."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        endpoint = f"{self._repo_url()}/issues?state={state}"
        if labels:
            endpoint += f"&labels={','.join(labels)}"

        print(f"[github] LIST ISSUES state={state}")
        return []  # Placeholder

    def create_issue(self, title: str, body: str, labels: Optional[List[str]] = None) -> Optional[Dict]:
        """Create a new issue."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        data = {"title": title, "body": body}
        if labels:
            data["labels"] = labels

        endpoint = f"{self._repo_url()}/issues"
        print(f"[github] CREATE ISSUE: {title}")
        return {"number": 1}  # Placeholder

    # -------------------------------------------------------------------------
    # Pull Requests
    # -------------------------------------------------------------------------

    def list_pull_requests(self, state: str = "open") -> List[Dict]:
        """List pull requests."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        endpoint = f"{self._repo_url()}/pulls?state={state}"
        print(f"[github] LIST PRs state={state}")
        return []  # Placeholder

    def get_pull_request(self, pr_number: int) -> Optional[Dict]:
        """Get a specific pull request."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        endpoint = f"{self._repo_url()}/pulls/{pr_number}"
        print(f"[github] GET PR #{pr_number}")
        return None  # Placeholder

    def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main"
    ) -> Optional[Dict]:
        """Create a pull request."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        data = {
            "title": title,
            "body": body,
            "head": head,
            "base": base,
        }

        endpoint = f"{self._repo_url()}/pulls"
        print(f"[github] CREATE PR: {title}")
        return {"number": 1, "html_url": f"https://github.com/{self.config.owner}/{self.config.repo}/pull/1"}

    def add_pr_comment(self, pr_number: int, body: str) -> bool:
        """Add a comment to a PR."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        endpoint = f"{self._repo_url()}/issues/{pr_number}/comments"
        print(f"[github] COMMENT on PR #{pr_number}")
        return True  # Placeholder

    # -------------------------------------------------------------------------
    # Projects (GraphQL)
    # -------------------------------------------------------------------------

    def graphql_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Execute a GraphQL query."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        print(f"[github] GRAPHQL query")
        return {}  # Placeholder

    def get_project_items(self, project_number: int) -> List[Dict]:
        """Get items from a GitHub Project (v2)."""
        query = """
        query($owner: String!, $number: Int!) {
            user(login: $owner) {
                projectV2(number: $number) {
                    items(first: 100) {
                        nodes {
                            id
                            content {
                                ... on Issue {
                                    title
                                    number
                                }
                                ... on PullRequest {
                                    title
                                    number
                                }
                            }
                            fieldValues(first: 10) {
                                nodes {
                                    ... on ProjectV2ItemFieldSingleSelectValue {
                                        name
                                        field { ... on ProjectV2SingleSelectField { name } }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        return self.graphql_query(query, {"owner": self.config.owner, "number": project_number})

    def move_project_item(self, item_id: str, status: str) -> bool:
        """Move an item to a different column in a project."""
        # GraphQL mutation to update project item field
        print(f"[github] MOVE PROJECT ITEM {item_id} -> {status}")
        return True  # Placeholder

    # -------------------------------------------------------------------------
    # Labels
    # -------------------------------------------------------------------------

    def ensure_labels(self, labels: List[Dict[str, str]]) -> bool:
        """Ensure required labels exist in the repository."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        for label in labels:
            print(f"[github] ENSURE LABEL: {label['name']}")

        return True  # Placeholder


class GitHubWebhookHandler(WebhookHandler):
    """
    Handler for GitHub webhooks.

    Verifies signatures and processes events.
    """

    def __init__(self):
        super().__init__("GITHUB_WEBHOOK_SECRET")

    def verify_signature(self, event: WebhookEvent) -> bool:
        """Verify the webhook signature using SHA-256."""
        payload_bytes = json.dumps(event.payload).encode('utf-8')
        return verify_github_webhook(payload_bytes, event.signature, self._secret)

    def process_event(self, event: WebhookEvent) -> Dict[str, Any]:
        """Process a GitHub webhook event."""
        if not event.verified:
            if not self.verify_signature(event):
                return {"error": "Invalid signature"}
            event.verified = True

        event_type = event.event_type
        payload = event.payload

        if event_type == "push":
            return self._handle_push(payload)
        elif event_type == "pull_request":
            return self._handle_pull_request(payload)
        elif event_type == "issues":
            return self._handle_issue(payload)
        elif event_type.startswith("project"):
            return self._handle_project_event(payload)
        else:
            return {"status": "ignored", "event_type": event_type}

    def _handle_push(self, payload: Dict) -> Dict[str, Any]:
        """Handle push event."""
        return {
            "action": "push",
            "ref": payload.get("ref"),
            "commits": len(payload.get("commits", [])),
        }

    def _handle_pull_request(self, payload: Dict) -> Dict[str, Any]:
        """Handle pull request event."""
        action = payload.get("action")
        pr = payload.get("pull_request", {})

        return {
            "action": f"pr_{action}",
            "number": pr.get("number"),
            "title": pr.get("title"),
            "state": pr.get("state"),
            "merged": pr.get("merged", False),
        }

    def _handle_issue(self, payload: Dict) -> Dict[str, Any]:
        """Handle issue event."""
        action = payload.get("action")
        issue = payload.get("issue", {})

        return {
            "action": f"issue_{action}",
            "number": issue.get("number"),
            "title": issue.get("title"),
            "state": issue.get("state"),
        }

    def _handle_project_event(self, payload: Dict) -> Dict[str, Any]:
        """Handle project-related events."""
        return {
            "action": "project_update",
            "payload_hash": sha256(json.dumps(payload)),
        }
