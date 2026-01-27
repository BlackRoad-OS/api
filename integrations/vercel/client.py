"""
Vercel API Integration

Handles:
- Project deployments
- Environment variables
- Domain management
"""

import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from integrations.base import BaseIntegration
from hashing import sha256


@dataclass
class VercelConfig:
    """Vercel configuration."""
    token: str
    team_id: Optional[str] = None


class VercelClient(BaseIntegration):
    """
    Vercel API client.

    Environment variables:
    - VERCEL_TOKEN: API token
    - VERCEL_TEAM_ID: Team ID (optional)
    """

    BASE_URL = "https://api.vercel.com"

    def __init__(self):
        super().__init__("vercel")
        self.config = VercelConfig(
            token=os.environ.get("VERCEL_TOKEN", ""),
            team_id=os.environ.get("VERCEL_TEAM_ID"),
        )
        self._headers = {}

    def authenticate(self) -> bool:
        if not self.config.token:
            print("[vercel] ERROR: VERCEL_TOKEN not set")
            return False

        self._headers = {
            "Authorization": f"Bearer {self.config.token}",
            "Content-Type": "application/json",
        }
        self._authenticated = True
        return True

    def health_check(self) -> bool:
        return bool(self.config.token)

    def get_state(self) -> Dict[str, Any]:
        return {
            "service": "vercel",
            "authenticated": self._authenticated,
            "team_id": self.config.team_id,
        }

    def list_projects(self) -> List[Dict]:
        """List all projects."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")
        print("[vercel] LIST PROJECTS")
        return []

    def get_deployments(self, project_id: str, limit: int = 10) -> List[Dict]:
        """Get recent deployments for a project."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")
        print(f"[vercel] GET DEPLOYMENTS project={project_id}")
        return []

    def create_deployment(self, project_id: str, target: str = "production") -> Optional[Dict]:
        """Trigger a new deployment."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")
        print(f"[vercel] CREATE DEPLOYMENT project={project_id} target={target}")
        return {"id": "dpl_xxx", "url": "https://xxx.vercel.app"}

    def get_env_vars(self, project_id: str) -> List[Dict]:
        """Get environment variables for a project."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")
        print(f"[vercel] GET ENV VARS project={project_id}")
        return []

    def set_env_var(self, project_id: str, key: str, value: str, target: List[str] = None) -> bool:
        """Set an environment variable."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated")
        target = target or ["production", "preview", "development"]
        print(f"[vercel] SET ENV VAR project={project_id} key={key}")
        return True
