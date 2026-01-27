"""
Claude API Integration

Handles:
- Agent task processing
- Code review assistance
- Documentation generation
"""

import os
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from integrations.base import BaseIntegration, APIResponse
from hashing import sha256


@dataclass
class ClaudeConfig:
    """Claude API configuration."""
    api_key: str
    model: str = "claude-opus-4-5-20251101"
    max_tokens: int = 4096


class ClaudeClient(BaseIntegration):
    """
    Claude API client for agent automation.

    Environment variables:
    - ANTHROPIC_API_KEY: API key

    Usage:
        client = ClaudeClient()
        if client.authenticate():
            response = client.complete(
                "Review this PR for issues: ...",
                system="You are a code reviewer."
            )
    """

    BASE_URL = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"

    AVAILABLE_MODELS = [
        "claude-opus-4-5-20251101",
        "claude-sonnet-4-20250514",
        "claude-haiku-3-5-20241022",
    ]

    def __init__(self, model: Optional[str] = None):
        super().__init__("claude")
        self.config = ClaudeConfig(
            api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            model=model or "claude-opus-4-5-20251101",
        )
        self._headers = {}

    def authenticate(self) -> bool:
        """Set up authentication headers."""
        if not self.config.api_key:
            print("[claude] ERROR: ANTHROPIC_API_KEY not set")
            return False

        self._headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": self.API_VERSION,
            "Content-Type": "application/json",
        }
        self._authenticated = True
        return True

    def health_check(self) -> bool:
        """Verify API connectivity."""
        return bool(self.config.api_key)

    def get_state(self) -> Dict[str, Any]:
        """Get client state summary."""
        return {
            "service": "claude",
            "authenticated": self._authenticated,
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
        }

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Generate a completion.

        Args:
            prompt: User message
            system: System prompt
            max_tokens: Max tokens in response
            temperature: Sampling temperature

        Returns:
            Response with content and metadata
        """
        if not self._authenticated:
            raise RuntimeError("Not authenticated")

        messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": self.config.model,
            "max_tokens": max_tokens or self.config.max_tokens,
            "messages": messages,
            "temperature": temperature,
        }

        if system:
            payload["system"] = system

        endpoint = f"{self.BASE_URL}/messages"

        # In production, make HTTP request here
        print(f"[claude] COMPLETE model={self.config.model} tokens={payload['max_tokens']}")

        # Placeholder response
        return {
            "content": "",
            "model": self.config.model,
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "hash": sha256(prompt),
        }

    # -------------------------------------------------------------------------
    # Agent-specific Operations
    # -------------------------------------------------------------------------

    def review_code(self, code: str, context: str = "") -> Dict[str, Any]:
        """
        Review code for issues.

        Args:
            code: Code to review
            context: Additional context (PR description, etc.)

        Returns:
            Review results with suggestions
        """
        system = """You are a code reviewer. Analyze the code for:
1. Bugs and potential issues
2. Security vulnerabilities
3. Performance concerns
4. Style and best practices
5. Test coverage gaps

Provide specific, actionable feedback."""

        prompt = f"""Review the following code:

```
{code}
```

Context: {context}"""

        return self.complete(prompt, system=system)

    def generate_pr_description(self, diff: str, commit_messages: List[str]) -> str:
        """Generate a PR description from diff and commits."""
        system = "Generate clear, concise PR descriptions in markdown format."

        prompt = f"""Generate a PR description for these changes:

Commits:
{chr(10).join(f'- {msg}' for msg in commit_messages)}

Diff summary:
{diff[:5000]}  # Truncate for token limits
"""

        result = self.complete(prompt, system=system)
        return result.get("content", "")

    def process_agent_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an agent task from the queue.

        Args:
            task: Task definition with type and parameters

        Returns:
            Task result
        """
        task_type = task.get("type", "")
        task_data = task.get("data", {})

        if task_type == "code_review":
            return self.review_code(task_data.get("code", ""), task_data.get("context", ""))
        elif task_type == "pr_description":
            return {"content": self.generate_pr_description(
                task_data.get("diff", ""),
                task_data.get("commits", [])
            )}
        else:
            return {"error": f"Unknown task type: {task_type}"}

    def analyze_pr_failure(self, logs: str, error_message: str) -> Dict[str, Any]:
        """
        Analyze why a PR failed and suggest fixes.

        Used to prevent recurring PR failures.
        """
        system = """You are a CI/CD expert. Analyze build/test failures and provide:
1. Root cause analysis
2. Specific fix suggestions
3. Prevention recommendations"""

        prompt = f"""A pull request failed with the following:

Error: {error_message}

Logs:
{logs[:8000]}

What went wrong and how to fix it?"""

        return self.complete(prompt, system=system)
