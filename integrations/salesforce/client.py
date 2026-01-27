"""
Salesforce API Integration

Handles:
- Kanban card CRM records
- Project status tracking
- Business logic and workflows
"""

import os
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from integrations.base import BaseIntegration, APIResponse, StateStore
from hashing import sha256


@dataclass
class SalesforceConfig:
    """Salesforce configuration."""
    client_id: str
    client_secret: str
    username: str
    password: str
    security_token: str
    instance_url: str = ""
    api_version: str = "v59.0"


class SalesforceClient(BaseIntegration):
    """
    Salesforce API client.

    Environment variables:
    - SF_CLIENT_ID: OAuth client ID
    - SF_CLIENT_SECRET: OAuth client secret
    - SF_USERNAME: Salesforce username
    - SF_PASSWORD: Salesforce password
    - SF_SECURITY_TOKEN: Security token
    - SF_INSTANCE_URL: Instance URL (optional, discovered via login)

    Usage:
        client = SalesforceClient()
        if client.authenticate():
            # Create kanban card record
            client.create_record("Kanban_Card__c", {
                "Name": "Feature X",
                "Status__c": "In Progress",
                "Priority__c": "High"
            })
    """

    LOGIN_URL = "https://login.salesforce.com/services/oauth2/token"

    def __init__(self):
        super().__init__("salesforce")
        self.config = SalesforceConfig(
            client_id=os.environ.get("SF_CLIENT_ID", ""),
            client_secret=os.environ.get("SF_CLIENT_SECRET", ""),
            username=os.environ.get("SF_USERNAME", ""),
            password=os.environ.get("SF_PASSWORD", ""),
            security_token=os.environ.get("SF_SECURITY_TOKEN", ""),
            instance_url=os.environ.get("SF_INSTANCE_URL", ""),
        )
        self._access_token = ""
        self._headers = {}

    def authenticate(self) -> bool:
        """
        Authenticate via OAuth2 password flow.

        In production, this would make an actual OAuth request.
        """
        if not all([self.config.client_id, self.config.username, self.config.password]):
            print("[salesforce] ERROR: Missing required credentials")
            return False

        # OAuth password grant flow (production would use requests)
        # POST to login.salesforce.com/services/oauth2/token
        # Body: grant_type=password&client_id=...&client_secret=...&username=...&password=...

        print("[salesforce] Authenticating...")

        # Placeholder - in production this would get real token
        self._access_token = "placeholder_token"
        self._authenticated = True

        self._headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

        return True

    def health_check(self) -> bool:
        """Verify API connectivity."""
        return bool(self.config.client_id and self.config.username)

    def get_state(self) -> Dict[str, Any]:
        """Get Salesforce state summary."""
        return {
            "service": "salesforce",
            "authenticated": self._authenticated,
            "username": self.config.username,
            "instance": self.config.instance_url or "login.salesforce.com",
            "api_version": self.config.api_version,
        }

    # -------------------------------------------------------------------------
    # CRUD Operations
    # -------------------------------------------------------------------------

    def _base_url(self) -> str:
        instance = self.config.instance_url or "https://login.salesforce.com"
        return f"{instance}/services/data/{self.config.api_version}"

    def query(self, soql: str) -> List[Dict[str, Any]]:
        """
        Execute a SOQL query.

        Args:
            soql: SOQL query string

        Returns:
            List of records
        """
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        endpoint = f"{self._base_url()}/query?q={soql}"
        print(f"[salesforce] QUERY: {soql[:50]}...")
        return []  # Placeholder

    def get_record(self, sobject: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a single record by ID."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        endpoint = f"{self._base_url()}/sobjects/{sobject}/{record_id}"
        print(f"[salesforce] GET {sobject}/{record_id}")
        return None  # Placeholder

    def create_record(self, sobject: str, data: Dict[str, Any]) -> Optional[str]:
        """
        Create a new record.

        Returns:
            Record ID if successful
        """
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        # Add hash for integrity
        data_with_hash = {
            **data,
            "Content_Hash__c": sha256(json.dumps(data, sort_keys=True)),
        }

        endpoint = f"{self._base_url()}/sobjects/{sobject}"
        print(f"[salesforce] CREATE {sobject}")
        return "placeholder_id"  # Placeholder

    def update_record(self, sobject: str, record_id: str, data: Dict[str, Any]) -> bool:
        """Update an existing record."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        data["Content_Hash__c"] = sha256(json.dumps(data, sort_keys=True))

        endpoint = f"{self._base_url()}/sobjects/{sobject}/{record_id}"
        print(f"[salesforce] UPDATE {sobject}/{record_id}")
        return True  # Placeholder

    def delete_record(self, sobject: str, record_id: str) -> bool:
        """Delete a record."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        endpoint = f"{self._base_url()}/sobjects/{sobject}/{record_id}"
        print(f"[salesforce] DELETE {sobject}/{record_id}")
        return True  # Placeholder

    # -------------------------------------------------------------------------
    # Kanban-specific Operations
    # -------------------------------------------------------------------------

    def get_kanban_cards(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get kanban cards, optionally filtered by status."""
        soql = "SELECT Id, Name, Status__c, Priority__c, Assignee__c, Content_Hash__c FROM Kanban_Card__c"
        if status:
            soql += f" WHERE Status__c = '{status}'"
        return self.query(soql)

    def sync_kanban_card(self, card_id: str, data: Dict[str, Any]) -> bool:
        """
        Sync a kanban card from GitHub/Cloudflare to Salesforce.

        Verifies hash to detect conflicts.
        """
        existing = self.get_record("Kanban_Card__c", card_id)

        if existing:
            # Check for conflicts
            existing_hash = existing.get("Content_Hash__c", "")
            new_hash = sha256(json.dumps(data, sort_keys=True))

            if existing_hash and existing_hash != new_hash:
                print(f"[salesforce] CONFLICT detected for card {card_id}")
                # In production, implement conflict resolution
                return False

            return self.update_record("Kanban_Card__c", card_id, data)
        else:
            result = self.create_record("Kanban_Card__c", data)
            return result is not None

    def get_project_metrics(self) -> Dict[str, Any]:
        """Get aggregated project metrics for dashboard."""
        return {
            "total_cards": 0,
            "by_status": {},
            "by_priority": {},
            "velocity": 0,
        }


class SalesforceStateStore(StateStore):
    """
    StateStore implementation using Salesforce custom objects.

    This is the SECONDARY/CRM state store for business logic.
    """

    def __init__(self, client: Optional[SalesforceClient] = None):
        self.client = client or SalesforceClient()
        if not self.client._authenticated:
            self.client.authenticate()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        # Key format: "sobject:id" e.g., "Kanban_Card__c:a00xxx"
        parts = key.split(":", 1)
        if len(parts) != 2:
            return None
        return self.client.get_record(parts[0], parts[1])

    def put(self, key: str, value: Dict[str, Any]) -> bool:
        parts = key.split(":", 1)
        if len(parts) != 2:
            return False

        sobject, record_id = parts
        if record_id == "new":
            result = self.client.create_record(sobject, value)
            return result is not None
        return self.client.update_record(sobject, record_id, value)

    def delete(self, key: str) -> bool:
        parts = key.split(":", 1)
        if len(parts) != 2:
            return False
        return self.client.delete_record(parts[0], parts[1])

    def list_keys(self, prefix: str = "") -> List[str]:
        # Would need to query Salesforce for this
        return []
