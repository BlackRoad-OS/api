# Agent Instructions for BlackRoad API

## Overview

This document provides instructions for AI agents (Claude, GitHub Actions, automated systems) working with the BlackRoad API repository system. Following these instructions ensures consistency across the "million repos" and prevents failed pull requests.

---

## Critical Rules

### 1. Never Push Directly to Main
- Always work on feature branches
- Branch naming: `claude/<feature>-<session-id>` or `feature/<description>`
- Create PRs for all changes

### 2. Always Verify Before Committing
```bash
# Run these checks before every commit
python -m py_compile <files>      # Syntax check
python -m pytest tests/ -v        # Run tests
python hashing/sha.py "test"      # Verify hashing works
```

### 3. Use Consistent State Management
- **Cloudflare KV**: Primary state storage
- **Salesforce**: CRM records and business logic
- **Git**: Source files only (no state!)

### 4. Hash Everything
- All API responses must be hashed for verification
- Use `sha256()` for simple hashes
- Use `sha_infinity()` for sensitive data
- Verify webhook signatures on all incoming requests

---

## Repository Structure

```
api/
├── agents/              # Agent instructions and configs
│   ├── AGENT_INSTRUCTIONS.md
│   └── todos/           # Agent task queues
├── config/              # Configuration files
│   └── endpoints.yaml   # All API endpoints
├── hashing/             # SHA-256 and infinity hashing
│   ├── __init__.py
│   └── sha.py
├── integrations/        # Service connectors
│   ├── cloudflare/
│   ├── salesforce/
│   ├── vercel/
│   ├── digitalocean/
│   ├── claude/
│   ├── termius/
│   ├── mobile/          # iSH, Shellfish, Working Copy, Pyto
│   └── endpoints/
├── kanban/              # Project management
│   └── project.yaml
├── state/               # State management
│   └── sync.py
└── .github/
    ├── workflows/       # CI/CD
    └── ISSUE_TEMPLATE/
```

---

## Kanban Workflow

### Card Lifecycle
1. **Backlog** → New items enter here
2. **To Do** → Prioritized and ready for work
3. **In Progress** → Actively being worked (WIP limit: 5)
4. **Review** → PR opened, awaiting approval
5. **Done** → Merged and deployed

### Creating Cards (Salesforce-style)
Cards support rich fields:
- `title` (required)
- `description` (required)
- `priority`: critical | high | medium | low
- `assignee`: GitHub username or "agent:claude"
- `linked_pr`: Auto-linked when PR opened
- `acceptance_criteria`: Checklist items

### State Synchronization
```
GitHub Project ←→ Cloudflare KV ←→ Salesforce
       ↓                ↓               ↓
    (files)          (state)         (CRM)
```

---

## API Integration Checklist

When adding or modifying integrations, verify:

- [ ] Endpoint defined in `config/endpoints.yaml`
- [ ] Auth credentials in environment variables (never in code!)
- [ ] Connector module in `integrations/<service>/`
- [ ] Webhook handler with signature verification
- [ ] State sync configured
- [ ] Tests added
- [ ] Documentation updated

---

## Preventing Failed Pull Requests

### Pre-PR Checklist
1. **Syntax Validation**
   ```bash
   find . -name "*.py" -exec python -m py_compile {} \;
   ```

2. **Type Checking** (if using mypy)
   ```bash
   mypy --ignore-missing-imports .
   ```

3. **Tests Pass**
   ```bash
   pytest tests/ -v --tb=short
   ```

4. **Lint Clean**
   ```bash
   ruff check .
   ```

5. **No Secrets in Code**
   ```bash
   git diff --cached | grep -E "(api_key|secret|password|token)" && echo "WARNING: Possible secrets!"
   ```

6. **Hash Verification**
   ```python
   from hashing import sha256
   # Verify any cached/stored data
   assert sha256(data) == expected_hash
   ```

### Common PR Failures and Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Merge conflict | Branch out of date | `git pull origin main --rebase` |
| Tests failing | Missing dependency | Check `requirements.txt` |
| Auth error | Missing env var | Add to GitHub Secrets |
| Hash mismatch | State desync | Run state sync |
| Syntax error | Typo in code | Run py_compile |

---

## Working with Mobile Tools

### iSH Shell
```bash
# Clone repo
git clone https://github.com/BlackRoad-OS/api.git
cd api
# Run Python scripts
python3 hashing/sha.py "test"
```

### Working Copy
- Use URL scheme: `working-copy://open?repo=api`
- Push via Working Copy → Confirm before push
- Pull to sync with remote

### Pyto
```python
# Import the hashing module
import sys
sys.path.insert(0, '/path/to/api')
from hashing import sha256, sha_infinity

# Use in Shortcuts
result = sha256("my data")
```

### Shellfish
- Configure SSH keys for Raspberry Pi fleet
- Use port forwarding for local APIs
- SFTP for file transfer

---

## Hashing Quick Reference

```python
from hashing import sha256, sha_infinity, verify_github_webhook

# Simple SHA-256
hash = sha256("my data")

# SHA-infinity (10000 rounds default)
secure_hash = sha_infinity("sensitive data")

# Custom rounds
custom_hash = sha_infinity("data", rounds=50000)

# Verify webhook
is_valid = verify_github_webhook(
    payload=request.body,
    signature=request.headers["X-Hub-Signature-256"],
    secret=os.environ["WEBHOOK_SECRET"]
)
```

---

## Service Endpoints Quick Reference

| Service | Base URL | Auth |
|---------|----------|------|
| Cloudflare | `api.cloudflare.com/client/v4` | Bearer token |
| Salesforce | `{instance}.salesforce.com/services/data/v59.0` | OAuth2 |
| Vercel | `api.vercel.com` | Bearer token |
| Digital Ocean | `api.digitalocean.com/v2` | Bearer token |
| Claude | `api.anthropic.com/v1` | X-API-Key |
| GitHub | `api.github.com` | Bearer token |

---

## Agent Task Queue

Tasks are stored in `agents/todos/` and synced to kanban board.

### Task Format
```yaml
id: "task-001"
title: "Implement feature X"
status: "pending"  # pending | in_progress | completed | blocked
priority: "high"
assignee: "agent:claude"
created: "2026-01-27T00:00:00Z"
hash: "<sha256 of task content>"
```

### Claiming a Task
1. Read task from `agents/todos/`
2. Update status to `in_progress`
3. Compute and verify hash
4. Sync to Cloudflare KV
5. Begin work

### Completing a Task
1. Verify all acceptance criteria
2. Run PR checklist
3. Update status to `completed`
4. Update hash
5. Sync to all systems

---

## Emergency Procedures

### State Desync
```bash
# Force sync from Cloudflare KV
python state/sync.py --force --source=cloudflare

# Rebuild from Git history
python state/sync.py --rebuild
```

### Auth Failure
1. Check env vars: `env | grep -E "TOKEN|KEY|SECRET"`
2. Verify in GitHub Secrets
3. Test endpoint manually
4. Rotate if compromised

### Hash Mismatch
```python
from hashing import StateHasher

hasher = StateHasher()
conflict = hasher.detect_conflict(local_state, remote_state, base_state)
print(conflict)
# Resolve based on conflict type
```

---

## Contact

- Repository: [BlackRoad-OS/api](https://github.com/BlackRoad-OS/api)
- Issues: Create in GitHub with `agent:claude` label for agent review
