"""
Generic Endpoint Client

Handles arbitrary API endpoints defined in config/endpoints.yaml
"""

import os
import json
import yaml
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from integrations.base import BaseIntegration, APIResponse
from hashing import sha256, SHAHasher


@dataclass
class EndpointConfig:
    """Configuration for a generic endpoint."""
    name: str
    base_url: str
    auth_type: str
    env_key: str
    endpoints: Dict[str, str]


class GenericEndpointClient(BaseIntegration):
    """
    Generic client for any API endpoint defined in config.

    Usage:
        client = GenericEndpointClient("my_service", {
            "base_url": "https://api.example.com",
            "auth_type": "bearer",
            "env_key": "MY_API_KEY",
            "endpoints": {"users": "/users", "items": "/items"}
        })
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name)
        self.endpoint_config = EndpointConfig(
            name=name,
            base_url=config.get("base_url", ""),
            auth_type=config.get("auth_type", "bearer"),
            env_key=config.get("env_key", ""),
            endpoints=config.get("endpoints", {}),
        )
        self._token = os.environ.get(self.endpoint_config.env_key, "")
        self._headers = {}

    def authenticate(self) -> bool:
        if not self._token:
            print(f"[{self.service_name}] ERROR: {self.endpoint_config.env_key} not set")
            return False

        if self.endpoint_config.auth_type == "bearer":
            self._headers["Authorization"] = f"Bearer {self._token}"
        elif self.endpoint_config.auth_type == "x-api-key":
            self._headers["x-api-key"] = self._token
        elif self.endpoint_config.auth_type == "basic":
            import base64
            self._headers["Authorization"] = f"Basic {base64.b64encode(self._token.encode()).decode()}"

        self._headers["Content-Type"] = "application/json"
        self._authenticated = True
        return True

    def health_check(self) -> bool:
        return bool(self._token)

    def get_state(self) -> Dict[str, Any]:
        return {
            "service": self.service_name,
            "authenticated": self._authenticated,
            "base_url": self.endpoint_config.base_url,
            "endpoints": list(self.endpoint_config.endpoints.keys()),
        }

    def get_endpoint_url(self, endpoint_name: str, **kwargs) -> str:
        """Get full URL for an endpoint with parameter substitution."""
        path = self.endpoint_config.endpoints.get(endpoint_name, "")
        if kwargs:
            path = path.format(**kwargs)
        return f"{self.endpoint_config.base_url}{path}"

    def call(
        self,
        endpoint_name: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        **path_params
    ) -> APIResponse:
        """Make an API call to the specified endpoint."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        url = self.get_endpoint_url(endpoint_name, **path_params)
        print(f"[{self.service_name}] {method} {url}")

        # Placeholder - in production would make HTTP request
        return APIResponse(
            success=True,
            status_code=200,
            data={},
            hash=sha256(url + method),
        )


class EndpointManager:
    """
    Manager for all configured endpoints.

    Loads configuration from config/endpoints.yaml and creates
    clients for each defined service.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config()
        self.config: Dict[str, Any] = {}
        self.clients: Dict[str, GenericEndpointClient] = {}
        self._load_config()

    def _find_config(self) -> str:
        """Find the endpoints.yaml config file."""
        # Look in common locations
        paths = [
            Path(__file__).parent.parent.parent / "config" / "endpoints.yaml",
            Path.cwd() / "config" / "endpoints.yaml",
            Path.home() / ".blackroad" / "endpoints.yaml",
        ]
        for path in paths:
            if path.exists():
                return str(path)
        return str(paths[0])  # Default

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"[endpoints] Config not found: {self.config_path}")
            self.config = {}

    def get_client(self, category: str, service: str) -> Optional[GenericEndpointClient]:
        """
        Get or create a client for a service.

        Args:
            category: Config category (e.g., "cloud", "crm", "ai")
            service: Service name (e.g., "cloudflare", "vercel")

        Returns:
            GenericEndpointClient or None
        """
        key = f"{category}.{service}"

        if key in self.clients:
            return self.clients[key]

        service_config = self.config.get(category, {}).get(service)
        if not service_config:
            print(f"[endpoints] Service not found: {key}")
            return None

        client = GenericEndpointClient(service, service_config)
        self.clients[key] = client
        return client

    def list_services(self) -> Dict[str, List[str]]:
        """List all configured services by category."""
        result = {}
        for category in ["cloud", "crm", "ai", "infrastructure"]:
            if category in self.config:
                result[category] = list(self.config[category].keys())
        return result

    def health_check_all(self) -> Dict[str, bool]:
        """Run health check on all services."""
        results = {}
        for category, services in self.list_services().items():
            for service in services:
                client = self.get_client(category, service)
                if client:
                    if client.authenticate():
                        results[f"{category}.{service}"] = client.health_check()
                    else:
                        results[f"{category}.{service}"] = False
        return results
