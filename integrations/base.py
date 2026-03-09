"""
Base integration classes for BlackRoad API connectors.
"""

import os
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

# Add parent dir to path for hashing import
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hashing import SHAHasher, sha256


class AuthType(Enum):
    BEARER = "bearer"
    API_KEY = "x-api-key"
    OAUTH2 = "oauth2"
    BASIC = "basic"


@dataclass
class APIResponse:
    """Standardized API response wrapper."""
    success: bool
    status_code: int
    data: Any
    headers: Dict[str, str] = field(default_factory=dict)
    hash: str = ""
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.hash and self.data:
            self.hash = sha256(json.dumps(self.data, sort_keys=True))


@dataclass
class WebhookEvent:
    """Standardized webhook event."""
    source: str
    event_type: str
    payload: Dict[str, Any]
    signature: str
    timestamp: float = field(default_factory=time.time)
    verified: bool = False
    hash: str = ""


class BaseIntegration(ABC):
    """
    Abstract base class for all service integrations.

    All integrations must implement:
    - authenticate(): Set up authentication
    - health_check(): Verify connectivity
    - get_state(): Get current service state
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.hasher = SHAHasher()
        self._authenticated = False
        self._last_response_hash: Optional[str] = None

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the service."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the service is reachable and working."""
        pass

    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """Get current state from the service."""
        pass

    def verify_response(self, response: APIResponse, expected_hash: Optional[str] = None) -> bool:
        """Verify response integrity using hash."""
        if expected_hash:
            return response.hash == expected_hash
        return bool(response.hash)

    def log_request(self, method: str, endpoint: str, response: APIResponse):
        """Log API request for debugging."""
        print(f"[{self.service_name}] {method} {endpoint} -> {response.status_code} (hash: {response.hash[:16]}...)")


class WebhookHandler(ABC):
    """Base class for webhook handlers."""

    def __init__(self, secret_env_var: str):
        self.hasher = SHAHasher()
        self._secret = os.environ.get(secret_env_var, "")

    @abstractmethod
    def verify_signature(self, event: WebhookEvent) -> bool:
        """Verify the webhook signature."""
        pass

    @abstractmethod
    def process_event(self, event: WebhookEvent) -> Dict[str, Any]:
        """Process the webhook event."""
        pass


class StateStore(ABC):
    """Abstract state storage interface."""

    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get state by key."""
        pass

    @abstractmethod
    def put(self, key: str, value: Dict[str, Any]) -> bool:
        """Store state."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete state."""
        pass

    @abstractmethod
    def list_keys(self, prefix: str = "") -> List[str]:
        """List all keys with optional prefix."""
        pass
