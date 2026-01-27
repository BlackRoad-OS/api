"""
Termius Integration

Handles SSH host management and team access.
Termius doesn't have a public API, so this provides
configuration file management and sync helpers.
"""

import os
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hashing import sha256


@dataclass
class SSHHost:
    """SSH host configuration."""
    name: str
    hostname: str
    username: str = "root"
    port: int = 22
    identity_file: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        self.tags = self.tags or []


class TermiusConfig:
    """
    Termius configuration manager.

    Since Termius doesn't have a public API, this manages
    SSH config files that can be imported into Termius.

    Usage:
        config = TermiusConfig()
        config.add_host(SSHHost(
            name="Pi-1",
            hostname="192.168.1.100",
            username="pi"
        ))
        config.export_ssh_config()
    """

    def __init__(self):
        self.hosts: List[SSHHost] = []
        self.groups: Dict[str, List[str]] = {}

    def add_host(self, host: SSHHost) -> None:
        """Add a host to the configuration."""
        self.hosts.append(host)

    def add_group(self, name: str, host_names: List[str]) -> None:
        """Create a host group."""
        self.groups[name] = host_names

    def get_state(self) -> Dict[str, Any]:
        """Get configuration state."""
        return {
            "tool": "termius",
            "hosts_count": len(self.hosts),
            "groups_count": len(self.groups),
            "hosts": [h.name for h in self.hosts],
        }

    def export_ssh_config(self) -> str:
        """
        Export configuration as SSH config format.

        This can be imported into Termius or used with standard SSH.
        """
        lines = ["# BlackRoad SSH Configuration", "# Import into Termius or use with SSH", ""]

        for host in self.hosts:
            lines.append(f"Host {host.name}")
            lines.append(f"    HostName {host.hostname}")
            lines.append(f"    User {host.username}")
            lines.append(f"    Port {host.port}")

            if host.identity_file:
                lines.append(f"    IdentityFile {host.identity_file}")

            if host.tags:
                lines.append(f"    # Tags: {', '.join(host.tags)}")

            lines.append("")

        return "\n".join(lines)

    def export_json(self) -> str:
        """Export configuration as JSON for programmatic use."""
        data = {
            "hosts": [
                {
                    "name": h.name,
                    "hostname": h.hostname,
                    "username": h.username,
                    "port": h.port,
                    "identity_file": h.identity_file,
                    "tags": h.tags,
                }
                for h in self.hosts
            ],
            "groups": self.groups,
            "hash": sha256(json.dumps([h.hostname for h in self.hosts])),
        }
        return json.dumps(data, indent=2)

    def load_json(self, json_str: str) -> None:
        """Load configuration from JSON."""
        data = json.loads(json_str)
        self.hosts = [
            SSHHost(
                name=h["name"],
                hostname=h["hostname"],
                username=h.get("username", "root"),
                port=h.get("port", 22),
                identity_file=h.get("identity_file"),
                tags=h.get("tags", []),
            )
            for h in data.get("hosts", [])
        ]
        self.groups = data.get("groups", {})


# Pre-configured Raspberry Pi fleet
def create_pi_fleet(count: int = 4, base_ip: str = "192.168.1") -> TermiusConfig:
    """
    Create a pre-configured Raspberry Pi fleet.

    Args:
        count: Number of Pis
        base_ip: Base IP prefix (e.g., "192.168.1")

    Returns:
        TermiusConfig with Pi hosts
    """
    config = TermiusConfig()

    for i in range(1, count + 1):
        config.add_host(SSHHost(
            name=f"pi-{i}",
            hostname=f"{base_ip}.{100 + i}",
            username="pi",
            port=22,
            tags=["raspberry-pi", "edge", f"node-{i}"],
        ))

    config.add_group("raspberry-pi-fleet", [f"pi-{i}" for i in range(1, count + 1)])

    return config
