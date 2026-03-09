"""
Mobile Development Tool Integrations

Clients for iOS development tools:
- iSH Shell
- Shellfish (SSH/SFTP)
- Working Copy (Git)
- Pyto (Python)
"""

import os
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hashing import sha256


@dataclass
class MobileToolConfig:
    """Configuration for mobile tools."""
    name: str
    sync_path: str
    url_scheme: Optional[str] = None


class iSHShell:
    """
    iSH Shell integration.

    iSH provides a Linux shell environment on iOS using Alpine Linux.

    Usage:
        ish = iSHShell()
        ish.run_command("git pull")
        ish.install_package("python3")
    """

    def __init__(self):
        self.config = MobileToolConfig(
            name="iSH",
            sync_path="/root",
        )
        self.shell = "ash"  # Alpine uses ash by default
        self.package_manager = "apk"

    def get_state(self) -> Dict[str, Any]:
        return {
            "tool": "ish",
            "shell": self.shell,
            "package_manager": self.package_manager,
            "sync_path": self.config.sync_path,
        }

    def generate_setup_script(self) -> str:
        """Generate setup script for iSH environment."""
        return """#!/bin/ash
# BlackRoad API Setup for iSH

# Update packages
apk update && apk upgrade

# Install essentials
apk add git python3 py3-pip openssh curl

# Clone the repository
cd /root
git clone https://github.com/BlackRoad-OS/api.git

# Install Python dependencies
cd api
pip3 install -r requirements.txt 2>/dev/null || true

echo "Setup complete!"
"""

    def run_command(self, command: str) -> Dict[str, Any]:
        """
        Generate command for execution in iSH.

        Note: This generates the command, actual execution happens in iSH.
        """
        return {
            "command": command,
            "shell": self.shell,
            "hash": sha256(command),
        }

    def install_package(self, package: str) -> Dict[str, Any]:
        """Generate package install command."""
        return self.run_command(f"apk add {package}")


class Shellfish:
    """
    Shellfish SSH/SFTP client integration.

    Shellfish is an iOS SSH client with Mosh support.

    Usage:
        sf = Shellfish()
        config = sf.generate_host_config("pi@raspberrypi.local")
    """

    def __init__(self):
        self.config = MobileToolConfig(
            name="Shellfish",
            sync_path="iCloud/Shellfish",
            url_scheme="shellfish://",
        )
        self.protocols = ["ssh", "sftp", "mosh"]

    def get_state(self) -> Dict[str, Any]:
        return {
            "tool": "shellfish",
            "protocols": self.protocols,
            "url_scheme": self.config.url_scheme,
        }

    def generate_host_config(
        self,
        host: str,
        user: str = "pi",
        port: int = 22,
        identity_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate SSH host configuration."""
        config = {
            "host": host,
            "user": user,
            "port": port,
        }
        if identity_file:
            config["identity_file"] = identity_file

        return {
            "config": config,
            "hash": sha256(json.dumps(config)),
        }

    def generate_url(self, host: str, user: str = "root") -> str:
        """Generate Shellfish URL scheme for quick connect."""
        return f"{self.config.url_scheme}connect?host={host}&user={user}"


class WorkingCopy:
    """
    Working Copy Git client integration.

    Working Copy is a full Git client for iOS with Shortcuts support.

    Usage:
        wc = WorkingCopy()
        url = wc.generate_clone_url("BlackRoad-OS/api")
    """

    def __init__(self):
        self.config = MobileToolConfig(
            name="Working Copy",
            sync_path="iCloud/Working Copy",
            url_scheme="working-copy://",
        )

    def get_state(self) -> Dict[str, Any]:
        return {
            "tool": "working_copy",
            "url_scheme": self.config.url_scheme,
            "features": ["git_lfs", "ssh_keys", "shortcuts"],
        }

    def generate_clone_url(self, repo: str, branch: Optional[str] = None) -> str:
        """Generate Working Copy URL to clone a repository."""
        url = f"{self.config.url_scheme}clone?remote=https://github.com/{repo}.git"
        if branch:
            url += f"&branch={branch}"
        return url

    def generate_open_url(self, repo: str, path: Optional[str] = None) -> str:
        """Generate URL to open a repository or file."""
        url = f"{self.config.url_scheme}open?repo={repo}"
        if path:
            url += f"&path={path}"
        return url

    def generate_commit_url(self, repo: str, message: str) -> str:
        """Generate URL to create a commit."""
        import urllib.parse
        encoded_message = urllib.parse.quote(message)
        return f"{self.config.url_scheme}commit?repo={repo}&message={encoded_message}"

    def generate_push_url(self, repo: str) -> str:
        """Generate URL to push changes."""
        return f"{self.config.url_scheme}push?repo={repo}"


class Pyto:
    """
    Pyto Python IDE integration.

    Pyto is a Python IDE for iOS with pip support and Shortcuts integration.

    Usage:
        pyto = Pyto()
        script = pyto.generate_hash_script("my data")
    """

    def __init__(self):
        self.config = MobileToolConfig(
            name="Pyto",
            sync_path="iCloud/Pyto",
            url_scheme="pyto://",
        )
        self.python_version = "3.11"

    def get_state(self) -> Dict[str, Any]:
        return {
            "tool": "pyto",
            "python_version": self.python_version,
            "url_scheme": self.config.url_scheme,
        }

    def generate_hash_script(self, data: str) -> str:
        """Generate a Python script to hash data."""
        return f'''#!/usr/bin/env python3
"""
BlackRoad SHA-256 Hash Script
Generated for Pyto on iOS
"""

import hashlib
import sys

def sha256(data: str) -> str:
    """Compute SHA-256 hash."""
    return hashlib.sha256(data.encode()).hexdigest()

def sha_infinity(data: str, rounds: int = 10000) -> str:
    """Compute SHA-infinity (multi-round) hash."""
    current = data.encode()
    for _ in range(rounds):
        current = hashlib.sha256(current).digest()
    return current.hex()

if __name__ == "__main__":
    data = """{data}"""
    print(f"Data: {{data}}")
    print(f"SHA-256: {{sha256(data)}}")
    print(f"SHA-infinity (10000 rounds): {{sha_infinity(data)}}")
'''

    def generate_api_script(self, endpoint: str, method: str = "GET") -> str:
        """Generate a Python script to call an API."""
        return f'''#!/usr/bin/env python3
"""
BlackRoad API Client Script
Generated for Pyto on iOS
"""

import json
import urllib.request

def call_api(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """Make an API call."""
    req = urllib.request.Request(endpoint, method=method)
    req.add_header("Content-Type", "application/json")

    if data:
        req.data = json.dumps(data).encode()

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())

if __name__ == "__main__":
    result = call_api("{endpoint}", "{method}")
    print(json.dumps(result, indent=2))
'''

    def generate_run_url(self, script_name: str) -> str:
        """Generate URL to run a script in Pyto."""
        return f"{self.config.url_scheme}run?script={script_name}"


class MobileToolManager:
    """
    Manager for all mobile development tools.

    Provides unified interface for mobile tool operations.
    """

    def __init__(self):
        self.ish = iSHShell()
        self.shellfish = Shellfish()
        self.working_copy = WorkingCopy()
        self.pyto = Pyto()

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get state of all mobile tools."""
        return {
            "ish": self.ish.get_state(),
            "shellfish": self.shellfish.get_state(),
            "working_copy": self.working_copy.get_state(),
            "pyto": self.pyto.get_state(),
        }

    def generate_full_setup(self) -> Dict[str, str]:
        """Generate setup scripts/URLs for all tools."""
        return {
            "ish_setup": self.ish.generate_setup_script(),
            "working_copy_clone": self.working_copy.generate_clone_url("BlackRoad-OS/api"),
            "shellfish_pi": self.shellfish.generate_url("raspberrypi.local", "pi"),
        }
