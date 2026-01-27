#!/usr/bin/env python3
"""
=============================================================================
BlackRoad State Synchronization System
=============================================================================
Manages state across multiple systems:
- GitHub (files/code)
- Cloudflare KV (primary state)
- Salesforce (CRM records)

Architecture:
    GitHub ←→ Cloudflare KV ←→ Salesforce
     (files)     (state)        (CRM)

The goal is to keep state consistent and detect conflicts early
to prevent failed pull requests.
=============================================================================
"""

import os
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hashing import sha256, StateHasher, SHAHasher


class SyncSource(Enum):
    """State synchronization sources."""
    GITHUB = "github"
    CLOUDFLARE = "cloudflare"
    SALESFORCE = "salesforce"
    LOCAL = "local"


class ConflictResolution(Enum):
    """Conflict resolution strategies."""
    LAST_WRITE_WINS = "last_write_wins"
    SOURCE_PRIORITY = "source_priority"
    MANUAL = "manual"
    MERGE = "merge"


@dataclass
class SyncState:
    """Represents synchronized state."""
    key: str
    value: Dict[str, Any]
    hash: str
    source: SyncSource
    timestamp: float = field(default_factory=time.time)
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "hash": self.hash,
            "source": self.source.value,
            "timestamp": self.timestamp,
            "version": self.version,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyncState":
        return cls(
            key=data["key"],
            value=data["value"],
            hash=data["hash"],
            source=SyncSource(data["source"]),
            timestamp=data.get("timestamp", time.time()),
            version=data.get("version", 1),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SyncConflict:
    """Represents a synchronization conflict."""
    key: str
    local_state: SyncState
    remote_state: SyncState
    detected_at: float = field(default_factory=time.time)
    resolved: bool = False
    resolution: Optional[str] = None


class StateManager:
    """
    Central state management for BlackRoad systems.

    This is the core component that keeps state synchronized
    across GitHub, Cloudflare, and Salesforce.

    Usage:
        manager = StateManager()

        # Store state
        manager.put("kanban:card:123", {"status": "in_progress", "title": "Feature X"})

        # Get state
        state = manager.get("kanban:card:123")

        # Sync to all systems
        manager.sync_all()

        # Check for conflicts
        conflicts = manager.detect_conflicts()
    """

    def __init__(
        self,
        primary_source: SyncSource = SyncSource.CLOUDFLARE,
        conflict_resolution: ConflictResolution = ConflictResolution.LAST_WRITE_WINS
    ):
        self.primary_source = primary_source
        self.conflict_resolution = conflict_resolution
        self.hasher = StateHasher()
        self._local_cache: Dict[str, SyncState] = {}
        self._pending_syncs: List[str] = []
        self._conflicts: List[SyncConflict] = []

        # Initialize backends (in production, these would be real clients)
        self._backends: Dict[SyncSource, Any] = {}

    def get(self, key: str) -> Optional[SyncState]:
        """
        Get state by key.

        Checks local cache first, then primary source.
        """
        # Check local cache
        if key in self._local_cache:
            return self._local_cache[key]

        # Fetch from primary source
        state = self._fetch_from_source(key, self.primary_source)
        if state:
            self._local_cache[key] = state

        return state

    def put(
        self,
        key: str,
        value: Dict[str, Any],
        source: Optional[SyncSource] = None
    ) -> SyncState:
        """
        Store state.

        Computes hash, stores locally, and queues for sync.
        """
        source = source or SyncSource.LOCAL

        # Compute hash of value
        value_hash = self.hasher.hash_state(value)

        # Get existing state for version increment
        existing = self._local_cache.get(key)
        version = (existing.version + 1) if existing else 1

        state = SyncState(
            key=key,
            value=value,
            hash=value_hash,
            source=source,
            version=version,
            metadata={"updated_by": "state_manager"},
        )

        self._local_cache[key] = state
        self._pending_syncs.append(key)

        return state

    def delete(self, key: str) -> bool:
        """Delete state by key."""
        if key in self._local_cache:
            del self._local_cache[key]
            # Queue deletion sync
            self._pending_syncs.append(f"DELETE:{key}")
            return True
        return False

    def _fetch_from_source(self, key: str, source: SyncSource) -> Optional[SyncState]:
        """Fetch state from a specific source."""
        print(f"[state] FETCH {key} from {source.value}")
        # In production, this would call the actual backend
        return None

    def _push_to_source(self, state: SyncState, source: SyncSource) -> bool:
        """Push state to a specific source."""
        print(f"[state] PUSH {state.key} to {source.value} (hash: {state.hash[:16]}...)")
        # In production, this would call the actual backend
        return True

    # -------------------------------------------------------------------------
    # Synchronization
    # -------------------------------------------------------------------------

    def sync_all(self) -> Dict[str, Any]:
        """
        Synchronize all pending changes to all backends.

        Returns sync results summary.
        """
        results = {
            "synced": [],
            "failed": [],
            "conflicts": [],
        }

        for key in self._pending_syncs[:]:  # Copy to allow modification
            state = self._local_cache.get(key)
            if not state:
                continue

            # Sync to all sources
            for source in [SyncSource.CLOUDFLARE, SyncSource.SALESFORCE]:
                try:
                    success = self._push_to_source(state, source)
                    if success:
                        results["synced"].append(f"{key}@{source.value}")
                    else:
                        results["failed"].append(f"{key}@{source.value}")
                except Exception as e:
                    results["failed"].append(f"{key}@{source.value}: {str(e)}")

            self._pending_syncs.remove(key)

        return results

    def sync_from_primary(self, keys: Optional[List[str]] = None) -> int:
        """
        Pull state from primary source.

        Args:
            keys: Specific keys to sync, or None for all

        Returns:
            Number of items synced
        """
        count = 0
        keys_to_sync = keys or list(self._local_cache.keys())

        for key in keys_to_sync:
            remote_state = self._fetch_from_source(key, self.primary_source)
            if remote_state:
                # Check for conflicts
                local_state = self._local_cache.get(key)
                if local_state and local_state.hash != remote_state.hash:
                    self._conflicts.append(SyncConflict(
                        key=key,
                        local_state=local_state,
                        remote_state=remote_state,
                    ))
                else:
                    self._local_cache[key] = remote_state
                    count += 1

        return count

    def detect_conflicts(self) -> List[SyncConflict]:
        """
        Detect conflicts between local and remote state.

        Returns list of unresolved conflicts.
        """
        conflicts = []

        for key, local_state in self._local_cache.items():
            remote_state = self._fetch_from_source(key, self.primary_source)
            if remote_state and local_state.hash != remote_state.hash:
                # Check if it's a real conflict or just a version difference
                if local_state.version >= remote_state.version:
                    # Local is newer, not a conflict
                    continue

                conflicts.append(SyncConflict(
                    key=key,
                    local_state=local_state,
                    remote_state=remote_state,
                ))

        self._conflicts.extend(conflicts)
        return conflicts

    def resolve_conflict(
        self,
        conflict: SyncConflict,
        resolution: ConflictResolution,
        merged_value: Optional[Dict[str, Any]] = None
    ) -> SyncState:
        """
        Resolve a synchronization conflict.

        Args:
            conflict: The conflict to resolve
            resolution: Resolution strategy
            merged_value: Merged value if using MERGE resolution

        Returns:
            Resolved state
        """
        if resolution == ConflictResolution.LAST_WRITE_WINS:
            # Use whichever has the later timestamp
            if conflict.local_state.timestamp > conflict.remote_state.timestamp:
                winner = conflict.local_state
            else:
                winner = conflict.remote_state
        elif resolution == ConflictResolution.SOURCE_PRIORITY:
            # Primary source wins
            winner = conflict.remote_state
        elif resolution == ConflictResolution.MERGE:
            if not merged_value:
                raise ValueError("merged_value required for MERGE resolution")
            winner = self.put(conflict.key, merged_value)
        else:
            raise ValueError(f"Cannot auto-resolve with {resolution}")

        conflict.resolved = True
        conflict.resolution = resolution.value

        self._local_cache[conflict.key] = winner
        self._pending_syncs.append(conflict.key)

        return winner

    # -------------------------------------------------------------------------
    # Kanban-specific Operations
    # -------------------------------------------------------------------------

    def get_kanban_card(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Get a kanban card by ID."""
        state = self.get(f"kanban:card:{card_id}")
        return state.value if state else None

    def update_kanban_card(
        self,
        card_id: str,
        updates: Dict[str, Any]
    ) -> SyncState:
        """Update a kanban card."""
        existing = self.get_kanban_card(card_id) or {}
        merged = {**existing, **updates}
        return self.put(f"kanban:card:{card_id}", merged)

    def move_kanban_card(self, card_id: str, new_status: str) -> SyncState:
        """Move a kanban card to a new column."""
        return self.update_kanban_card(card_id, {
            "status": new_status,
            "status_changed_at": time.time(),
        })

    def list_kanban_cards(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List kanban cards, optionally filtered by status."""
        cards = []
        for key, state in self._local_cache.items():
            if key.startswith("kanban:card:"):
                if status is None or state.value.get("status") == status:
                    cards.append({
                        "id": key.split(":")[-1],
                        **state.value,
                        "_hash": state.hash,
                    })
        return cards

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def save_local(self, path: Optional[str] = None) -> str:
        """Save local cache to disk."""
        path = path or str(Path.home() / ".blackroad" / "state.json")
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": 1,
            "timestamp": time.time(),
            "states": {k: v.to_dict() for k, v in self._local_cache.items()},
            "pending_syncs": self._pending_syncs,
        }

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

        return path

    def load_local(self, path: Optional[str] = None) -> int:
        """Load local cache from disk."""
        path = path or str(Path.home() / ".blackroad" / "state.json")

        try:
            with open(path) as f:
                data = json.load(f)

            for key, state_dict in data.get("states", {}).items():
                self._local_cache[key] = SyncState.from_dict(state_dict)

            self._pending_syncs = data.get("pending_syncs", [])

            return len(self._local_cache)
        except FileNotFoundError:
            return 0


# =============================================================================
# CLI Interface
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BlackRoad State Sync")
    parser.add_argument("command", choices=["sync", "status", "conflicts", "rebuild"])
    parser.add_argument("--source", choices=["cloudflare", "salesforce", "local"])
    parser.add_argument("--force", action="store_true")

    args = parser.parse_args()

    manager = StateManager()

    if args.command == "sync":
        results = manager.sync_all()
        print(f"Synced: {len(results['synced'])}")
        print(f"Failed: {len(results['failed'])}")
        print(f"Conflicts: {len(results['conflicts'])}")

    elif args.command == "status":
        print(f"Local cache: {len(manager._local_cache)} items")
        print(f"Pending syncs: {len(manager._pending_syncs)}")
        print(f"Conflicts: {len(manager._conflicts)}")

    elif args.command == "conflicts":
        conflicts = manager.detect_conflicts()
        for c in conflicts:
            print(f"CONFLICT: {c.key}")
            print(f"  Local hash:  {c.local_state.hash[:16]}...")
            print(f"  Remote hash: {c.remote_state.hash[:16]}...")

    elif args.command == "rebuild":
        if args.force:
            manager.sync_from_primary()
            print("State rebuilt from primary source")
        else:
            print("Use --force to rebuild state")
