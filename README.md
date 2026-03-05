# BlackRoad API Integration Hub

Central API coordination for all BlackRoad repositories. This system provides:

- **Kanban Project Management** - Salesforce-style project boards in GitHub
- **Multi-Service Integrations** - Cloudflare, Salesforce, Vercel, Digital Ocean, Claude, and more
- **State Synchronization** - Keep state consistent across GitHub, Cloudflare KV, and Salesforce
- **SHA-256 & SHA-Infinity Hashing** - Secure verification for all API operations
- **Agent Task System** - Automated task queue for Claude and other agents

## Architecture

```
GitHub (files) <--> Cloudflare KV (state) <--> Salesforce (CRM)
      |                    |                        |
      +--------------------+------------------------+
                           |
                    State Manager
                           |
            +------+-------+-------+------+
            |      |       |       |      |
         Vercel   DO    Claude  Termius  Mobile
```

## Quick Start

```bash
# Clone the repository
git clone https://github.com/BlackRoad-OS/api.git
cd api

# Set up environment variables (see .env.example)
cp .env.example .env

# Test hashing
python hashing/sha.py "test data"

# Check integrations
python -c "from integrations.endpoints import EndpointManager; print(EndpointManager().list_services())"
```

## Directory Structure

```
api/
├── agents/              # Agent instructions and task queue
│   ├── AGENT_INSTRUCTIONS.md
│   └── todos/           # Task files for automated agents
├── config/
│   └── endpoints.yaml   # All API endpoint configurations
├── hashing/             # SHA-256 and SHA-infinity hashing
│   ├── __init__.py
│   └── sha.py
├── integrations/        # Service connectors
│   ├── cloudflare/      # Cloudflare (KV, Workers, DNS)
│   ├── salesforce/      # Salesforce CRM
│   ├── github/          # GitHub (Projects, Issues, PRs)
│   ├── claude/          # Claude API
│   ├── vercel/          # Vercel deployments
│   ├── digitalocean/    # Digital Ocean infrastructure
│   ├── termius/         # SSH/Termius config
│   ├── mobile/          # iOS tools (iSH, Shellfish, Working Copy, Pyto)
│   └── endpoints/       # Generic endpoint client
├── kanban/
│   └── project.yaml     # Kanban board configuration
├── state/               # State synchronization
│   └── sync.py
└── .github/
    ├── workflows/       # CI/CD pipelines
    └── ISSUE_TEMPLATE/  # Issue templates
```

## Integrations

| Service | Status | Description |
|---------|--------|-------------|
| Cloudflare | Ready | KV state storage, Workers, DNS |
| Salesforce | Ready | CRM records, business logic |
| GitHub | Ready | Projects, Issues, PRs, Webhooks |
| Vercel | Ready | Deployments, Environment vars |
| Digital Ocean | Ready | Droplets, K8s, Databases |
| Claude | Ready | AI agent automation |
| Termius | Ready | SSH configuration |
| Raspberry Pi | Ready | Edge computing fleet |
| iSH | Ready | iOS Linux shell |
| Shellfish | Ready | iOS SSH client |
| Working Copy | Ready | iOS Git client |
| Pyto | Ready | iOS Python IDE |

## Hashing

### SHA-256

```python
from hashing import sha256

hash = sha256("my data")
# '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08'
```

### SHA-Infinity (Multi-round)

```python
from hashing import sha_infinity

# Default: 10,000 rounds
secure_hash = sha_infinity("sensitive data")

# Custom rounds
extra_secure = sha_infinity("data", rounds=50000)
```

### Webhook Verification

```python
from hashing import verify_github_webhook

is_valid = verify_github_webhook(
    payload=request.body,
    signature=request.headers["X-Hub-Signature-256"],
    secret=os.environ["WEBHOOK_SECRET"]
)
```

## State Management

State is synchronized across multiple backends:

```python
from state import StateManager

manager = StateManager()

# Store state (syncs to Cloudflare KV + Salesforce)
manager.put("kanban:card:123", {
    "title": "Feature X",
    "status": "in_progress",
    "priority": "high"
})

# Retrieve state
state = manager.get("kanban:card:123")

# Sync all pending changes
manager.sync_all()

# Detect conflicts
conflicts = manager.detect_conflicts()
```

## Kanban Board

Projects are managed using a Salesforce-style kanban system:

- **Backlog** - New items
- **To Do** - Prioritized and ready
- **In Progress** - Actively being worked (WIP limit: 5)
- **Review** - PR opened, awaiting approval
- **Done** - Merged and deployed

### Cards sync to:
1. GitHub Projects (visual board)
2. Cloudflare KV (state storage)
3. Salesforce (CRM records)

## Agent Instructions

Agents (Claude, GitHub Actions) should follow the instructions in `agents/AGENT_INSTRUCTIONS.md`:

1. Never push directly to main
2. Always verify before committing
3. Use consistent state management
4. Hash everything
5. Follow the PR checklist to prevent failures

## Environment Variables

```bash
# Cloud Services
CLOUDFLARE_API_TOKEN=
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_KV_NAMESPACE_ID=
VERCEL_TOKEN=
DIGITALOCEAN_TOKEN=

# Salesforce
SF_CLIENT_ID=
SF_CLIENT_SECRET=
SF_USERNAME=
SF_PASSWORD=
SF_SECURITY_TOKEN=

# AI
ANTHROPIC_API_KEY=

# GitHub
GITHUB_TOKEN=
GITHUB_WEBHOOK_SECRET=
```

## Preventing Failed PRs

This system is designed to prevent failed pull requests by:

1. **Pre-commit validation** - Syntax, types, tests
2. **Hash verification** - Content integrity checks
3. **State consistency** - Detect conflicts before merge
4. **Automated checks** - CI/CD validates all changes
5. **Agent instructions** - Clear guidelines for automation

See `agents/AGENT_INSTRUCTIONS.md` for the complete checklist.

## Mobile Development

Works with iOS development tools:

- **iSH**: Run Python scripts and git commands
- **Working Copy**: Clone, commit, push via URL schemes
- **Shellfish**: SSH to Raspberry Pi fleet
- **Pyto**: Run hashing and API scripts

```python
from integrations.mobile import WorkingCopy, Pyto

# Generate clone URL for Working Copy
wc = WorkingCopy()
url = wc.generate_clone_url("BlackRoad-OS/api")
# working-copy://clone?remote=https://github.com/BlackRoad-OS/api.git

# Generate hash script for Pyto
pyto = Pyto()
script = pyto.generate_hash_script("my data")
```

## Contributing

1. Read `agents/AGENT_INSTRUCTIONS.md`
2. Create a feature branch
3. Follow the PR checklist
4. Ensure all checks pass
5. Request review

## License

MIT
