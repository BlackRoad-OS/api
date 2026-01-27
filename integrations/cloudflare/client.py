"""
Cloudflare API Integration

Handles:
- KV State Storage
- Workers
- D1 Database
- DNS Management
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
class CloudflareConfig:
    """Cloudflare configuration."""
    api_token: str
    account_id: str
    zone_id: Optional[str] = None
    kv_namespace_id: Optional[str] = None


class CloudflareClient(BaseIntegration):
    """
    Cloudflare API client.

    Environment variables:
    - CLOUDFLARE_API_TOKEN: API token
    - CLOUDFLARE_ACCOUNT_ID: Account ID
    - CLOUDFLARE_ZONE_ID: Zone ID (optional)
    - CLOUDFLARE_KV_NAMESPACE_ID: KV namespace for state storage

    Usage:
        client = CloudflareClient()
        if client.authenticate():
            state = client.kv_get("kanban:card:123")
            client.kv_put("kanban:card:123", {"status": "in_progress"})
    """

    BASE_URL = "https://api.cloudflare.com/client/v4"

    def __init__(self):
        super().__init__("cloudflare")
        self.config = CloudflareConfig(
            api_token=os.environ.get("CLOUDFLARE_API_TOKEN", ""),
            account_id=os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""),
            zone_id=os.environ.get("CLOUDFLARE_ZONE_ID"),
            kv_namespace_id=os.environ.get("CLOUDFLARE_KV_NAMESPACE_ID"),
        )
        self._headers = {}

    def authenticate(self) -> bool:
        """Set up authentication headers."""
        if not self.config.api_token:
            print("[cloudflare] ERROR: CLOUDFLARE_API_TOKEN not set")
            return False

        self._headers = {
            "Authorization": f"Bearer {self.config.api_token}",
            "Content-Type": "application/json",
        }
        self._authenticated = True
        return True

    def health_check(self) -> bool:
        """Verify API connectivity."""
        # In production, this would make an actual API call
        # For now, just verify we have credentials
        return bool(self.config.api_token and self.config.account_id)

    def get_state(self) -> Dict[str, Any]:
        """Get state summary from Cloudflare."""
        return {
            "service": "cloudflare",
            "authenticated": self._authenticated,
            "account_id": self.config.account_id[:8] + "..." if self.config.account_id else None,
            "kv_namespace": self.config.kv_namespace_id,
        }

    # -------------------------------------------------------------------------
    # KV Storage (State Management)
    # -------------------------------------------------------------------------

    def kv_get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get value from KV store.

        Args:
            key: KV key (e.g., "kanban:card:123")

        Returns:
            Parsed JSON value or None
        """
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        # Endpoint: /accounts/{account_id}/storage/kv/namespaces/{namespace_id}/values/{key_name}
        endpoint = f"/accounts/{self.config.account_id}/storage/kv/namespaces/{self.config.kv_namespace_id}/values/{key}"

        # In production, make HTTP request here
        # return self._request("GET", endpoint)
        print(f"[cloudflare] KV GET {key}")
        return None  # Placeholder

    def kv_put(self, key: str, value: Dict[str, Any], metadata: Optional[Dict] = None) -> bool:
        """
        Put value to KV store with hash verification.

        Args:
            key: KV key
            value: JSON-serializable value
            metadata: Optional KV metadata

        Returns:
            True if successful
        """
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        # Add hash to value for integrity verification
        value_with_hash = {
            **value,
            "_hash": sha256(json.dumps(value, sort_keys=True)),
            "_updated": __import__("time").time(),
        }

        endpoint = f"/accounts/{self.config.account_id}/storage/kv/namespaces/{self.config.kv_namespace_id}/values/{key}"

        # In production, make HTTP request here
        print(f"[cloudflare] KV PUT {key} (hash: {value_with_hash['_hash'][:16]}...)")
        return True  # Placeholder

    def kv_delete(self, key: str) -> bool:
        """Delete key from KV store."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        endpoint = f"/accounts/{self.config.account_id}/storage/kv/namespaces/{self.config.kv_namespace_id}/values/{key}"
        print(f"[cloudflare] KV DELETE {key}")
        return True  # Placeholder

    def kv_list(self, prefix: str = "") -> List[str]:
        """List keys in KV store."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        endpoint = f"/accounts/{self.config.account_id}/storage/kv/namespaces/{self.config.kv_namespace_id}/keys"
        if prefix:
            endpoint += f"?prefix={prefix}"

        print(f"[cloudflare] KV LIST prefix={prefix}")
        return []  # Placeholder

    # -------------------------------------------------------------------------
    # Workers
    # -------------------------------------------------------------------------

    def deploy_worker(self, script_name: str, script_content: str) -> bool:
        """Deploy a Cloudflare Worker script."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        endpoint = f"/accounts/{self.config.account_id}/workers/scripts/{script_name}"
        print(f"[cloudflare] DEPLOY WORKER {script_name}")
        return True  # Placeholder

    # -------------------------------------------------------------------------
    # DNS
    # -------------------------------------------------------------------------

    def list_dns_records(self, zone_id: Optional[str] = None) -> List[Dict]:
        """List DNS records for a zone."""
        zone = zone_id or self.config.zone_id
        if not zone:
            raise ValueError("Zone ID required")

        endpoint = f"/zones/{zone}/dns_records"
        print(f"[cloudflare] LIST DNS zone={zone}")
        return []  # Placeholder


class CloudflareKVStore(StateStore):
    """
    StateStore implementation using Cloudflare KV.

    This is the PRIMARY state store for the kanban system.
    """

    def __init__(self, client: Optional[CloudflareClient] = None):
        self.client = client or CloudflareClient()
        if not self.client._authenticated:
            self.client.authenticate()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self.client.kv_get(key)

    def put(self, key: str, value: Dict[str, Any]) -> bool:
        return self.client.kv_put(key, value)

    def delete(self, key: str) -> bool:
        return self.client.kv_delete(key)

    def list_keys(self, prefix: str = "") -> List[str]:
        return self.client.kv_list(prefix)
