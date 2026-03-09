# Agent Task Queue

This directory contains task files for automated agents (Claude, GitHub Actions, etc.).

## Task Format

Tasks are stored as YAML files with the following structure:

```yaml
id: "task-001"
title: "Implement feature X"
description: "Detailed description of the task"
status: "pending"  # pending | in_progress | completed | blocked
priority: "high"   # critical | high | medium | low
assignee: "agent:claude"
created: "2026-01-27T00:00:00Z"
updated: "2026-01-27T00:00:00Z"
hash: "<sha256 of task content>"

# Optional fields
labels:
  - "type:feature"
  - "priority:high"

acceptance_criteria:
  - "Criteria 1"
  - "Criteria 2"

linked_pr: null
linked_issue: null

metadata:
  source: "github_issue"
  source_id: "123"
```

## Task Lifecycle

1. **Created**: Task file added to `pending/` directory
2. **Claimed**: Agent moves task to `in_progress/`, updates status
3. **Working**: Agent updates task file with progress
4. **Review**: Agent creates PR, updates `linked_pr`
5. **Completed**: Task moved to `completed/`, status updated

## Directories

- `pending/` - Tasks waiting to be claimed
- `in_progress/` - Tasks currently being worked on
- `completed/` - Finished tasks (auto-archived after 14 days)
- `blocked/` - Tasks that cannot proceed

## Claiming a Task

Agents should:

1. Check `pending/` for available tasks
2. Verify hash matches content (integrity check)
3. Move task file to `in_progress/`
4. Update status and timestamp
5. Recompute and update hash

## Completing a Task

Agents should:

1. Verify all acceptance criteria met
2. Ensure PR passes all checks
3. Update task with `linked_pr`
4. Move to `completed/`
5. Update hash

## Hash Verification

Every task file includes a SHA-256 hash of its content (excluding the hash field itself).
This ensures:

- Task integrity during sync
- Detection of unauthorized modifications
- Audit trail for changes

```python
from hashing import sha256
import yaml

# Load task (excluding hash field)
with open("task.yaml") as f:
    task = yaml.safe_load(f)

stored_hash = task.pop("hash", "")
computed_hash = sha256(yaml.dump(task, sort_keys=True))

assert stored_hash == computed_hash, "Task integrity check failed!"
```

## Sync with Kanban Board

Tasks are automatically synced to:
- GitHub Projects (via GraphQL API)
- Cloudflare KV (state storage)
- Salesforce (CRM records)

The sync process is managed by `state/sync.py`.
