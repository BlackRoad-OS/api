#!/usr/bin/env python3
"""
=============================================================================
BlackRoad SHA Hashing Utilities
=============================================================================
Implements SHA-256 and extensible "SHA-infinity" hashing for:
- API request/response verification
- Webhook signature validation
- State synchronization integrity
- Content-addressable storage

SHA-Infinity: Configurable multi-round hashing with salt chains for
enhanced security and verification depth.
=============================================================================
"""

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class HashAlgorithm(Enum):
    """Supported hash algorithms."""
    SHA256 = "sha256"
    SHA384 = "sha384"
    SHA512 = "sha512"
    SHA3_256 = "sha3_256"
    SHA3_512 = "sha3_512"
    BLAKE2B = "blake2b"
    BLAKE2S = "blake2s"


@dataclass
class HashResult:
    """Result of a hashing operation."""
    digest: str
    algorithm: str
    rounds: int
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "digest": self.digest,
            "algorithm": self.algorithm,
            "rounds": self.rounds,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class SHAHasher:
    """
    Core SHA hashing implementation.

    Usage:
        hasher = SHAHasher()

        # Simple SHA-256
        result = hasher.hash("my data")

        # SHA-infinity (multi-round)
        result = hasher.hash_infinity("my data", rounds=1000)

        # Verify webhook signature
        is_valid = hasher.verify_webhook_signature(
            payload=request.body,
            signature=request.headers["X-Hub-Signature-256"],
            secret=os.environ["WEBHOOK_SECRET"]
        )
    """

    def __init__(self, default_algorithm: HashAlgorithm = HashAlgorithm.SHA256):
        self.default_algorithm = default_algorithm

    def hash(
        self,
        data: Union[str, bytes],
        algorithm: Optional[HashAlgorithm] = None
    ) -> HashResult:
        """
        Compute a simple hash of the input data.

        Args:
            data: String or bytes to hash
            algorithm: Hash algorithm to use (default: SHA-256)

        Returns:
            HashResult with digest and metadata
        """
        algo = algorithm or self.default_algorithm

        if isinstance(data, str):
            data = data.encode('utf-8')

        hasher = hashlib.new(algo.value)
        hasher.update(data)

        return HashResult(
            digest=hasher.hexdigest(),
            algorithm=algo.value,
            rounds=1,
            timestamp=time.time()
        )

    def hash_infinity(
        self,
        data: Union[str, bytes],
        rounds: int = 10000,
        salt: Optional[bytes] = None,
        algorithm: Optional[HashAlgorithm] = None,
        chain_salts: bool = True
    ) -> HashResult:
        """
        SHA-Infinity: Multi-round hashing with optional salt chains.

        This provides enhanced security through:
        - Multiple hash rounds (computational cost)
        - Salt chaining (each round uses previous digest as additional salt)
        - Configurable algorithms

        Args:
            data: String or bytes to hash
            rounds: Number of hash iterations (default: 10000)
            salt: Initial salt bytes (generated if not provided)
            algorithm: Hash algorithm (default: SHA-256)
            chain_salts: Whether to chain salts between rounds

        Returns:
            HashResult with final digest and metadata
        """
        algo = algorithm or self.default_algorithm

        if isinstance(data, str):
            data = data.encode('utf-8')

        if salt is None:
            salt = os.urandom(32)

        current_hash = data
        current_salt = salt

        for i in range(rounds):
            hasher = hashlib.new(algo.value)
            hasher.update(current_salt)
            hasher.update(current_hash)
            current_hash = hasher.digest()

            if chain_salts:
                # Use hash output as next round's salt component
                current_salt = current_hash[:16] + salt[16:]

        return HashResult(
            digest=current_hash.hex(),
            algorithm=f"{algo.value}-infinity",
            rounds=rounds,
            timestamp=time.time(),
            metadata={
                "salt_prefix": salt[:8].hex(),
                "chain_salts": chain_salts
            }
        )

    def hash_json(
        self,
        obj: Any,
        algorithm: Optional[HashAlgorithm] = None,
        sort_keys: bool = True
    ) -> HashResult:
        """
        Hash a JSON-serializable object deterministically.

        Args:
            obj: Any JSON-serializable object
            algorithm: Hash algorithm
            sort_keys: Sort dictionary keys for determinism

        Returns:
            HashResult of the canonical JSON representation
        """
        canonical = json.dumps(obj, sort_keys=sort_keys, separators=(',', ':'))
        return self.hash(canonical, algorithm)

    def verify_webhook_signature(
        self,
        payload: Union[str, bytes],
        signature: str,
        secret: str,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256
    ) -> bool:
        """
        Verify a webhook signature (e.g., GitHub, Stripe).

        Args:
            payload: Raw request body
            signature: Signature header value (with or without algorithm prefix)
            secret: Webhook secret
            algorithm: Expected hash algorithm

        Returns:
            True if signature is valid
        """
        if isinstance(payload, str):
            payload = payload.encode('utf-8')

        if isinstance(secret, str):
            secret = secret.encode('utf-8')

        # Handle prefixed signatures like "sha256=abc123"
        if '=' in signature:
            prefix, signature = signature.split('=', 1)

        expected = hmac.new(secret, payload, algorithm.value).hexdigest()

        return hmac.compare_digest(expected, signature)

    def create_webhook_signature(
        self,
        payload: Union[str, bytes],
        secret: str,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256,
        include_prefix: bool = True
    ) -> str:
        """
        Create a webhook signature for outgoing requests.

        Args:
            payload: Request body
            secret: Signing secret
            algorithm: Hash algorithm
            include_prefix: Include algorithm prefix (e.g., "sha256=")

        Returns:
            Signature string
        """
        if isinstance(payload, str):
            payload = payload.encode('utf-8')

        if isinstance(secret, str):
            secret = secret.encode('utf-8')

        signature = hmac.new(secret, payload, algorithm.value).hexdigest()

        if include_prefix:
            return f"{algorithm.value}={signature}"
        return signature


class ContentAddressableStorage:
    """
    Content-addressable storage using SHA-256 hashes.

    Used for:
    - Deduplicating API responses
    - Caching state snapshots
    - Verifying data integrity
    """

    def __init__(self, hasher: Optional[SHAHasher] = None):
        self.hasher = hasher or SHAHasher()
        self._store: Dict[str, bytes] = {}

    def put(self, data: Union[str, bytes]) -> str:
        """Store data and return its content hash."""
        if isinstance(data, str):
            data = data.encode('utf-8')

        result = self.hasher.hash(data)
        self._store[result.digest] = data
        return result.digest

    def get(self, hash_key: str) -> Optional[bytes]:
        """Retrieve data by its content hash."""
        return self._store.get(hash_key)

    def exists(self, hash_key: str) -> bool:
        """Check if content exists by hash."""
        return hash_key in self._store

    def verify(self, hash_key: str, data: Union[str, bytes]) -> bool:
        """Verify that data matches the expected hash."""
        if isinstance(data, str):
            data = data.encode('utf-8')

        result = self.hasher.hash(data)
        return result.digest == hash_key


class StateHasher:
    """
    Specialized hasher for state synchronization.

    Used to detect changes and conflicts when syncing state between:
    - GitHub Projects
    - Salesforce records
    - Cloudflare KV
    """

    def __init__(self):
        self.hasher = SHAHasher()

    def hash_state(self, state: Dict[str, Any]) -> str:
        """
        Create a deterministic hash of application state.

        Normalizes the state before hashing to ensure consistent
        results across different systems.
        """
        # Normalize: sort keys, remove volatile fields
        normalized = self._normalize_state(state)
        result = self.hasher.hash_json(normalized)
        return result.digest

    def _normalize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Remove volatile fields and normalize structure."""
        volatile_fields = {'updated_at', 'last_modified', 'etag', '_metadata'}

        def clean(obj):
            if isinstance(obj, dict):
                return {
                    k: clean(v)
                    for k, v in sorted(obj.items())
                    if k not in volatile_fields
                }
            elif isinstance(obj, list):
                return [clean(item) for item in obj]
            return obj

        return clean(state)

    def detect_conflict(
        self,
        local_state: Dict[str, Any],
        remote_state: Dict[str, Any],
        base_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect conflicts between local and remote state.

        Returns:
            Dict with conflict information
        """
        local_hash = self.hash_state(local_state)
        remote_hash = self.hash_state(remote_state)

        result = {
            "has_conflict": local_hash != remote_hash,
            "local_hash": local_hash,
            "remote_hash": remote_hash
        }

        if base_state:
            base_hash = self.hash_state(base_state)
            result["base_hash"] = base_hash
            result["local_changed"] = local_hash != base_hash
            result["remote_changed"] = remote_hash != base_hash

        return result


# =============================================================================
# Convenience Functions
# =============================================================================

def sha256(data: Union[str, bytes]) -> str:
    """Quick SHA-256 hash."""
    return SHAHasher().hash(data).digest


def sha_infinity(data: Union[str, bytes], rounds: int = 10000) -> str:
    """Quick SHA-infinity hash."""
    return SHAHasher().hash_infinity(data, rounds=rounds).digest


def verify_github_webhook(payload: bytes, signature: str, secret: str) -> bool:
    """Verify a GitHub webhook signature."""
    return SHAHasher().verify_webhook_signature(payload, signature, secret)


def hash_for_cache(obj: Any) -> str:
    """Create a cache key from any JSON-serializable object."""
    return SHAHasher().hash_json(obj).digest


# =============================================================================
# CLI Interface
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python sha.py <data> [--rounds N] [--algorithm ALGO]")
        print("\nAlgorithms: sha256, sha384, sha512, sha3_256, sha3_512, blake2b, blake2s")
        sys.exit(1)

    data = sys.argv[1]
    rounds = 1
    algo = HashAlgorithm.SHA256

    # Parse arguments
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--rounds" and i + 1 < len(args):
            rounds = int(args[i + 1])
            i += 2
        elif args[i] == "--algorithm" and i + 1 < len(args):
            algo = HashAlgorithm(args[i + 1])
            i += 2
        else:
            i += 1

    hasher = SHAHasher(algo)

    if rounds > 1:
        result = hasher.hash_infinity(data, rounds=rounds)
    else:
        result = hasher.hash(data)

    print(f"Algorithm: {result.algorithm}")
    print(f"Rounds: {result.rounds}")
    print(f"Digest: {result.digest}")
