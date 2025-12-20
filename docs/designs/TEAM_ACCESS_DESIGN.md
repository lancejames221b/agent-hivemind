# Team Access & Vaults Design Document

**Author:** Claude Design Agent
**Date:** 2025-12-19
**Status:** Draft
**Branch:** `claude/design-team-access-vaults-TxiQc`

---

## Executive Summary

This document proposes a comprehensive team access system for hAIveMind that enables:
- **Solo Mode**: Private individual work with personal vaults
- **Vaults**: Secure, isolated storage spaces with fine-grained access control
- **Team Mode**: Collaborative workspaces with shared memories and coordinated agents
- **Context Signaling**: A mechanism to communicate access mode/intent to LLMs via MCP

---

## 1. Problem Statement

Currently, hAIveMind has:
- Machine-based access control (allowed_machines)
- Project-scoped memories
- Agent registration without team awareness
- No concept of personal vaults vs team spaces

**What's Missing:**
1. Clear separation between personal and team work
2. Private vaults that are truly isolated
3. Team membership and role management
4. A way to signal "mode" or "intent" to the LLM so it knows which context to use

---

## 2. Core Concepts

### 2.1 Access Modes

```
┌─────────────────────────────────────────────────────────────────┐
│                        ACCESS MODES                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   SOLO MODE          VAULT MODE           TEAM MODE             │
│   ┌─────────┐        ┌─────────┐          ┌─────────┐           │
│   │ Personal│        │ Private │          │ Shared  │           │
│   │ Memories│        │ Secrets │          │ Memory  │           │
│   │         │        │ & Data  │          │ Space   │           │
│   └─────────┘        └─────────┘          └─────────┘           │
│   - Only you         - Encrypted          - Team-wide           │
│   - Local context    - Explicit access    - Role-based          │
│   - No sharing       - Audit logging      - Shared context      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Vault Hierarchy

```
Organization (optional)
    └── Teams
            └── Team Vaults (shared secrets, configs)
    └── Users
            └── Personal Vaults (private to individual)
            └── Project Vaults (project-specific secrets)
```

---

## 3. Data Model Extensions

### 3.1 Team Model

```python
@dataclass
class Team:
    team_id: str              # Unique identifier (e.g., "team_design_001")
    name: str                 # Human readable name
    description: str          # Team purpose
    owner_id: str             # Team owner (user_id)
    created_at: datetime
    settings: Dict[str, Any]  # Team-specific settings
    metadata: Dict[str, Any]  # Custom metadata

@dataclass
class TeamMember:
    team_id: str
    user_id: str              # User/agent identifier
    role: TeamRole            # admin, member, readonly
    joined_at: datetime
    invited_by: str
    capabilities: List[str]   # What this member can do in team context

class TeamRole(Enum):
    OWNER = "owner"           # Full control, can delete team
    ADMIN = "admin"           # Manage members, settings
    MEMBER = "member"         # Read/write access
    READONLY = "readonly"     # Read-only access
    GUEST = "guest"           # Limited temporary access
```

### 3.2 Vault Model

```python
@dataclass
class Vault:
    vault_id: str             # Unique identifier
    name: str
    vault_type: VaultType     # personal, team, project, shared
    owner_id: str             # User or team_id
    encryption_key_id: str    # Reference to encryption key
    created_at: datetime
    access_policy: AccessPolicy
    metadata: Dict[str, Any]

class VaultType(Enum):
    PERSONAL = "personal"     # Private to one user
    TEAM = "team"             # Shared by team members
    PROJECT = "project"       # Project-scoped vault
    SHARED = "shared"         # Cross-team shared vault

@dataclass
class AccessPolicy:
    default_access: AccessLevel   # none, read, write, admin
    explicit_grants: List[AccessGrant]
    require_mfa: bool
    audit_all_access: bool
    expiry: Optional[datetime]
```

### 3.3 Extended Memory Metadata

Add to existing memory documents:

```python
# New metadata fields for memories
{
    "memory_id": "...",
    "content": "...",

    # Existing fields
    "machine_id": "lance-dev",
    "project_path": "/home/user/project",
    "scope": "team-global",

    # NEW: Access context fields
    "access_mode": "team",           # solo | vault | team
    "team_id": "team_design_001",    # If team mode
    "vault_id": "vault_personal_123", # If vault mode
    "owner_id": "user_alice",
    "visibility": "team",            # private | vault | team | public
    "access_grants": ["user_bob", "team_design_001"],
}
```

### 3.4 Agent Registry Extension

```python
# Extended agent registration (Redis)
{
    "agent_id": "lance-dev-alice-1234",
    "machine_id": "lance-dev",
    "user": "alice",

    # NEW: Access context
    "current_mode": "team",          # Current operating mode
    "team_id": "team_design_001",    # Active team context
    "vault_id": null,                # Active vault (if vault mode)
    "available_teams": ["team_design_001", "team_devops"],
    "available_vaults": ["vault_personal_alice", "vault_team_design"],

    # Permissions derived from mode
    "active_permissions": ["read", "write", "share"],
}
```

---

## 4. Mode Signaling to LLM

### 4.1 The Challenge

MCP tools don't have built-in "mode" or "session state" - each tool call is independent. We need to:
1. Tell the LLM what mode we're in
2. Have the LLM respect that mode in its operations
3. Allow easy mode switching

### 4.2 Solution: Context Injection + Mode Tools

**Approach A: System Context Injection**

Every MCP tool response includes a context header:

```python
# In every tool response
{
    "result": {...},
    "_context": {
        "mode": "team",
        "team_id": "team_design_001",
        "team_name": "Design Team",
        "permissions": ["read", "write"],
        "vault_access": ["vault_team_design"],
        "hint": "You are operating in TEAM mode. Memories stored will be visible to team members."
    }
}
```

**Approach B: Dedicated Mode Tools**

```python
# MCP Tools for mode management
@mcp.tool()
async def get_current_mode() -> Dict:
    """Get current operating mode and context"""
    return {
        "mode": "team",
        "team": {"id": "...", "name": "...", "role": "member"},
        "vault": None,
        "hint": "Currently in team mode..."
    }

@mcp.tool()
async def set_mode(
    mode: str,                    # "solo" | "vault" | "team"
    team_id: Optional[str],       # Required for team mode
    vault_id: Optional[str],      # Required for vault mode
) -> Dict:
    """Switch operating mode"""
    # Validates access, updates agent registry
    ...

@mcp.tool()
async def list_available_modes() -> Dict:
    """List all modes and contexts available to current user"""
    return {
        "modes": [
            {"mode": "solo", "description": "Personal work, private memories"},
            {"mode": "vault", "vaults": [...]},
            {"mode": "team", "teams": [...]},
        ]
    }
```

**Approach C: Smart Defaults with Override (Recommended)**

Combine implicit defaults with explicit control:

```python
# Default mode inference
def _infer_mode(tool_params: Dict) -> AccessContext:
    """
    Infer mode from:
    1. Explicit mode parameter (if provided)
    2. Active session mode (from agent registry)
    3. Content analysis (secrets → vault, team mentions → team)
    4. Default to solo for safety
    """
    if "mode" in tool_params:
        return tool_params["mode"]

    session = get_agent_session()
    if session.current_mode:
        return session.current_mode

    # Content-based hints
    if contains_secrets(tool_params.get("content", "")):
        return "vault"  # Suggest vault for sensitive content

    return "solo"  # Safe default

# Tool with optional mode override
@mcp.tool()
async def store_memory(
    content: str,
    category: str,
    tags: List[str] = [],
    # NEW: Optional mode override
    mode: Optional[str] = None,      # Override current mode
    team_id: Optional[str] = None,   # Override active team
    vault_id: Optional[str] = None,  # Store in specific vault
) -> Dict:
    """
    Store a memory with access control.

    Mode behavior:
    - solo: Memory is private to you only
    - vault: Memory stored in encrypted vault
    - team: Memory shared with team members

    If mode not specified, uses your current session mode.
    """
    context = _infer_mode(locals())
    ...
```

### 4.3 LLM Guidance via Tool Descriptions

Tool descriptions should educate the LLM:

```python
@mcp.tool()
async def store_memory(
    content: str,
    mode: str = "solo",
    ...
) -> Dict:
    """
    Store a memory in the hAIveMind knowledge base.

    ACCESS MODES:
    - "solo": Private memory, only you can access (DEFAULT - safest)
    - "vault": Encrypted storage in a vault (for secrets, credentials)
    - "team": Shared with your current team (for collaborative work)

    IMPORTANT:
    - When storing sensitive data (API keys, passwords, personal info), use mode="vault"
    - When working on team tasks, use mode="team" to share knowledge
    - When unsure, use mode="solo" - you can always share later

    Examples:
    - Personal note: mode="solo"
    - Database password: mode="vault", vault_id="vault_prod_secrets"
    - Team decision: mode="team", team_id="team_design"
    """
```

### 4.4 Mode Indicator in Responses

Every response should remind the LLM of context:

```python
# Response format
{
    "success": True,
    "memory_id": "mem_abc123",
    "stored_in": {
        "mode": "team",
        "team_name": "Design Team",
        "visibility": "team_members_only"
    },
    "_mode_reminder": "Memory stored in TEAM mode. 5 team members can access this."
}
```

---

## 5. MCP Tool Specifications

### 5.1 Mode Management Tools

```python
@mcp.tool()
async def get_mode() -> Dict:
    """
    Get your current operating mode and context.

    Returns:
    - mode: Current mode (solo/vault/team)
    - context: Active team or vault details
    - permissions: What you can do in this mode
    - available_modes: All modes you can switch to
    """

@mcp.tool()
async def set_mode(
    mode: Literal["solo", "vault", "team"],
    context_id: Optional[str] = None,  # team_id or vault_id
) -> Dict:
    """
    Switch your operating mode.

    - "solo": Work privately (default)
    - "vault": Access a specific vault (requires context_id=vault_id)
    - "team": Work with a team (requires context_id=team_id)

    Your mode persists across tool calls until changed.
    """

@mcp.tool()
async def get_mode_hint(
    content: str,
    operation: str,  # "store", "search", "share"
) -> Dict:
    """
    Get a recommendation for which mode to use.

    Analyzes content and operation to suggest the best mode.
    Useful before storing sensitive or collaborative content.
    """
```

### 5.2 Team Management Tools

```python
@mcp.tool()
async def create_team(
    name: str,
    description: str,
    initial_members: List[str] = [],
) -> Dict:
    """Create a new team"""

@mcp.tool()
async def list_teams(
    include_membership: bool = True,
) -> Dict:
    """List teams you belong to"""

@mcp.tool()
async def get_team(
    team_id: str,
) -> Dict:
    """Get team details including members and settings"""

@mcp.tool()
async def add_team_member(
    team_id: str,
    user_id: str,
    role: Literal["admin", "member", "readonly"] = "member",
) -> Dict:
    """Add a member to a team (requires admin role)"""

@mcp.tool()
async def remove_team_member(
    team_id: str,
    user_id: str,
) -> Dict:
    """Remove a member from a team (requires admin role)"""

@mcp.tool()
async def get_team_activity(
    team_id: str,
    hours: int = 24,
) -> Dict:
    """Get recent team activity and shared memories"""
```

### 5.3 Vault Management Tools

```python
@mcp.tool()
async def create_vault(
    name: str,
    vault_type: Literal["personal", "team", "project"] = "personal",
    team_id: Optional[str] = None,  # Required for team vaults
) -> Dict:
    """Create a new vault for secure storage"""

@mcp.tool()
async def list_vaults() -> Dict:
    """List all vaults you have access to"""

@mcp.tool()
async def store_in_vault(
    vault_id: str,
    key: str,           # Secret name/identifier
    value: str,         # Secret value (will be encrypted)
    metadata: Dict = {},
) -> Dict:
    """Store a secret in a vault"""

@mcp.tool()
async def retrieve_from_vault(
    vault_id: str,
    key: str,
    audit_reason: str,  # Required for audit trail
) -> Dict:
    """Retrieve a secret from a vault (logged)"""

@mcp.tool()
async def share_vault(
    vault_id: str,
    share_with: str,    # user_id or team_id
    access_level: Literal["read", "write", "admin"] = "read",
    expires: Optional[str] = None,
) -> Dict:
    """Share vault access with a user or team"""

@mcp.tool()
async def vault_audit_log(
    vault_id: str,
    hours: int = 24,
) -> Dict:
    """Get vault access audit log"""
```

### 5.4 Updated Memory Tools

```python
@mcp.tool()
async def store_memory(
    content: str,
    category: str,
    tags: List[str] = [],
    # Access control
    mode: Optional[Literal["solo", "vault", "team"]] = None,
    vault_id: Optional[str] = None,
    team_id: Optional[str] = None,
    share_with: List[str] = [],     # Explicit sharing
) -> Dict:
    """
    Store a memory with mode-aware access control.

    MODE BEHAVIOR:
    - solo (default): Private to you only
    - vault: Stored encrypted in specified vault
    - team: Shared with current/specified team

    If mode is not specified, uses your current session mode.
    """

@mcp.tool()
async def search_memories(
    query: str,
    # Access scope
    mode: Optional[Literal["solo", "vault", "team", "all"]] = None,
    include_team_memories: bool = True,
    include_vault_memories: bool = False,
    team_id: Optional[str] = None,
    # Existing params...
) -> Dict:
    """
    Search memories with access-aware filtering.

    By default, searches your accessible memories based on current mode.
    Set mode="all" to search everything you have access to.
    """
```

---

## 6. Storage Architecture

### 6.1 ChromaDB Collections

```
chroma/
├── solo/                      # Per-user private collections
│   └── user_{user_id}/        # User's solo memories
├── vaults/                    # Vault-stored secrets
│   └── vault_{vault_id}/      # Encrypted vault storage
├── teams/                     # Team-shared collections
│   └── team_{team_id}/        # Team memories
└── shared/                    # Cross-team/public
    └── global/                # Globally accessible
```

### 6.2 Redis Keys

```
# Mode/Session State
session:{agent_id}:mode         → {"mode": "team", "context_id": "..."}
session:{agent_id}:permissions  → ["read", "write", "share"]

# Teams
team:{team_id}                  → {name, owner, settings, ...}
team:{team_id}:members          → SET of user_ids
team:{team_id}:activity         → Recent activity stream

# Vaults
vault:{vault_id}:meta           → {name, type, owner, ...}
vault:{vault_id}:access         → {user_id: access_level, ...}
vault:{vault_id}:audit          → Audit log entries

# User lookups
user:{user_id}:teams            → SET of team_ids
user:{user_id}:vaults           → SET of vault_ids
user:{user_id}:default_mode     → Default operating mode
```

### 6.3 SQLite Tables

```sql
-- Teams
CREATE TABLE teams (
    team_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    owner_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settings JSON,
    metadata JSON
);

-- Team Members
CREATE TABLE team_members (
    team_id TEXT,
    user_id TEXT,
    role TEXT CHECK(role IN ('owner', 'admin', 'member', 'readonly', 'guest')),
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    invited_by TEXT,
    PRIMARY KEY (team_id, user_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

-- Vaults
CREATE TABLE vaults (
    vault_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    vault_type TEXT CHECK(vault_type IN ('personal', 'team', 'project', 'shared')),
    owner_id TEXT NOT NULL,
    team_id TEXT,
    encryption_key_ref TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_policy JSON,
    metadata JSON,
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

-- Vault Access Grants
CREATE TABLE vault_access (
    vault_id TEXT,
    grantee_id TEXT,           -- user_id or team_id
    grantee_type TEXT CHECK(grantee_type IN ('user', 'team')),
    access_level TEXT CHECK(access_level IN ('read', 'write', 'admin')),
    granted_by TEXT,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    PRIMARY KEY (vault_id, grantee_id),
    FOREIGN KEY (vault_id) REFERENCES vaults(vault_id)
);

-- Vault Audit Log
CREATE TABLE vault_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vault_id TEXT,
    actor_id TEXT,
    action TEXT,               -- read, write, share, access_granted, etc.
    key_accessed TEXT,
    reason TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON,
    FOREIGN KEY (vault_id) REFERENCES vaults(vault_id)
);
```

---

## 7. Security Considerations

### 7.1 Vault Encryption

```python
# Encryption architecture
class VaultEncryption:
    """
    - Each vault has a unique encryption key
    - Keys stored encrypted with master key
    - Master key derived from user credentials + hardware key
    - All vault operations require authentication
    """

    def encrypt_secret(self, vault_id: str, plaintext: str) -> bytes:
        vault_key = self._get_vault_key(vault_id)
        return self._aes_gcm_encrypt(plaintext, vault_key)

    def decrypt_secret(self, vault_id: str, ciphertext: bytes) -> str:
        vault_key = self._get_vault_key(vault_id)
        return self._aes_gcm_decrypt(ciphertext, vault_key)
```

### 7.2 Access Control Checks

```python
def check_access(
    actor: str,           # user_id or agent_id
    resource: str,        # memory_id, vault_id, team_id
    action: str,          # read, write, delete, share
    context: AccessContext
) -> bool:
    """
    Access check order:
    1. Is resource in actor's current mode context?
    2. Does actor have explicit grant for resource?
    3. Is actor member of team that owns resource?
    4. Is resource publicly accessible?
    """
```

### 7.3 Audit Trail

All sensitive operations logged:
- Vault access (read/write)
- Mode changes
- Team membership changes
- Secret sharing
- Permission grants

---

## 8. User Experience Flow

### 8.1 First Time Setup

```
User: Help me set up my workspace

Claude: I'll help you set up your hAIveMind workspace.

Current setup:
- Mode: solo (private, only you)
- Personal Vault: vault_personal_alice (empty)
- Teams: None

Would you like to:
1. Stay in solo mode (private work)
2. Create a new team
3. Join an existing team
```

### 8.2 Mode Switching

```
User: Let's work on the design team project

Claude: Switching to team mode for "Design Team"...

[set_mode(mode="team", context_id="team_design_001")]

Now in TEAM mode:
- Team: Design Team (3 members)
- Your role: Member
- Shared memories: 47
- Recent activity: @bob added notes on API design

Anything I store will be visible to team members.
How can I help with the project?
```

### 8.3 Vault Access

```
User: I need to store the production database password

Claude: That's sensitive data - I'll store it securely in a vault.

[get_mode_hint(content="production database password", operation="store")]
→ Recommendation: Use vault mode with production vault

[store_in_vault(vault_id="vault_prod_secrets", key="db_password", value="***",
                metadata={"type": "database", "environment": "production"})]

Stored in Production Secrets vault.
Access: Only you and @alice have access
Audit: All access is logged
```

---

## 9. Web Management Interface (Tailscale-Style Admin Console)

The existing hAIveMind admin dashboard (`admin/`) will be extended with a Teams & Access management interface, similar to Tailscale's admin console.

### 9.1 Navigation Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  hAIveMind Admin                                          [alice@dev] [⚙]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Dashboard | Memory | Agents | Teams | Vaults | Access | Settings          │
│                        ^^^^    ^^^^^   ^^^^^^   ^^^^^^                      │
│                        NEW     NEW     NEW      NEW                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Teams Management Page (`admin/teams.html`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Teams                                              [+ Create Team]         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  🏢 Design Team                                    [Admin] [Active] │    │
│  │  5 members • 147 shared memories • Created Jan 15                   │    │
│  │  ───────────────────────────────────────────────────────────────── │    │
│  │  Members: @alice (owner), @bob, @charlie, @dave, @eve              │    │
│  │  Recent: @bob stored "API Design Notes" 2 hours ago                 │    │
│  │                                              [Manage] [Settings]    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  🔧 DevOps Team                                   [Member] [Active] │    │
│  │  8 members • 892 shared memories • Created Dec 3                    │    │
│  │  ───────────────────────────────────────────────────────────────── │    │
│  │  Members: @ops-lead (owner), @alice, +6 more                        │    │
│  │  Recent: @sentinel stored "Incident Report" 30 min ago             │    │
│  │                                                         [View]      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Team Detail View

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ← Back to Teams                                                             │
│                                                                              │
│  🏢 Design Team                                          [⚙ Settings]       │
│  Building the next generation of hAIveMind UI                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [Members]  [Memories]  [Activity]  [Vaults]  [Settings]                    │
│                                                                              │
│  Members (5)                                         [+ Invite Member]       │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │  👤 alice@dev          Owner      Joined Jan 15    [...]          │      │
│  │  👤 bob@dev            Admin      Joined Jan 16    [...]          │      │
│  │  👤 charlie@dev        Member     Joined Jan 20    [...]          │      │
│  │  👤 dave@laptop        Member     Joined Feb 1     [...]          │      │
│  │  👤 eve@remote         Readonly   Joined Feb 10    [...]          │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  Pending Invites (1)                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │  ✉️  frank@new         Invited by @alice    Expires in 6 days     │      │
│  │                                        [Resend] [Revoke]          │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.3 Vaults Management Page (`admin/vaults.html`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Vaults                                              [+ Create Vault]        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  My Vaults                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  🔐 Personal Vault                              [Personal] [Locked]  │    │
│  │  12 secrets • Last accessed today                                    │    │
│  │                                              [Unlock] [Settings]     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Team Vaults                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  🔐 Design Team Secrets                      [Team: Design] [Locked] │    │
│  │  8 secrets • Shared with 5 members                                   │    │
│  │                                              [Unlock] [Settings]     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  🔐 Production Credentials                 [Team: DevOps] [Unlocked] │    │
│  │  45 secrets • Read access only                                       │    │
│  │                                                     [View] [Lock]    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Vault Detail View (Unlocked)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔐 Production Credentials                    🟢 Unlocked    [Lock Now]     │
│  Team: DevOps • 45 secrets                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [Secrets]  [Access]  [Audit Log]  [Settings]                               │
│                                                                              │
│  Search: [________________________] [🔍]     [+ Add Secret]                 │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │  🔑 db_production_password                                         │      │
│  │  Type: Database • Environment: production • Updated: 2 days ago   │      │
│  │                                        [Copy] [View] [Edit] [...]  │      │
│  ├───────────────────────────────────────────────────────────────────┤      │
│  │  🔑 api_stripe_key                                                 │      │
│  │  Type: API Key • Environment: production • Updated: 1 week ago    │      │
│  │                                        [Copy] [View] [Edit] [...]  │      │
│  ├───────────────────────────────────────────────────────────────────┤      │
│  │  🔑 ssh_deploy_key                                                 │      │
│  │  Type: SSH Key • Environment: production • Updated: 1 month ago   │      │
│  │                                        [Copy] [View] [Edit] [...]  │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  ⚠️  3 secrets expiring within 30 days                    [View Expiring]   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.4 Access Control Page (`admin/access.html`)

Tailscale-style ACL editor for fine-grained permissions:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Access Control                                          [Save Changes]     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [Visual Editor]  [JSON/YAML]  [Test Access]                                │
│                                                                              │
│  Access Policies                                         [+ Add Policy]     │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │  Policy: design-team-access                                        │      │
│  │  ─────────────────────────────────────────────────────────────── │      │
│  │  WHO:    members of team:design                                   │      │
│  │  CAN:    read, write                                               │      │
│  │  WHAT:   memories where team_id = "design"                        │      │
│  │          vaults tagged "design-*"                                  │      │
│  │                                                    [Edit] [Delete] │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │  Policy: production-vault-read                                     │      │
│  │  ─────────────────────────────────────────────────────────────── │      │
│  │  WHO:    role:senior-dev OR team:devops                           │      │
│  │  CAN:    read                                                      │      │
│  │  WHAT:   vault:production-credentials                              │      │
│  │  REQUIRE: audit_reason                                             │      │
│  │                                                    [Edit] [Delete] │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  Test Access                                                                 │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │  User: [@alice____________]  Resource: [vault:prod-creds____]     │      │
│  │  Action: [read ▼]                                                  │      │
│  │                                                                    │      │
│  │  Result: ✅ ALLOWED by policy "production-vault-read"             │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.5 Mode Switcher (Global Header Component)

A persistent mode indicator/switcher in the header, visible on all pages:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  hAIveMind Admin            Mode: [🔒 Solo ▼]              alice@dev [⚙]   │
│                                   ┌──────────────────────┐                  │
│                                   │ 🔒 Solo (Private)    │ ← Current       │
│                                   │ 🔐 Vault: Personal   │                  │
│                                   │ 👥 Team: Design      │                  │
│                                   │ 👥 Team: DevOps      │                  │
│                                   │ ─────────────────── │                  │
│                                   │ ⚙️  Manage modes...   │                  │
│                                   └──────────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

When in team mode, the header reflects this:

```
│  hAIveMind Admin           Mode: [👥 Design Team ▼]        alice@dev [⚙]  │
```

### 9.6 Activity Feed (Dashboard Integration)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Activity Feed                            [All] [My Teams] [My Activity]    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Today                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │  👥 @bob stored memory "API endpoint documentation"               │      │
│  │  in Design Team • 10 minutes ago                                  │      │
│  ├───────────────────────────────────────────────────────────────────┤      │
│  │  🔐 @alice accessed secret "db_production_password"               │      │
│  │  from Production Credentials • 1 hour ago                          │      │
│  ├───────────────────────────────────────────────────────────────────┤      │
│  │  👤 @charlie joined Design Team                                    │      │
│  │  invited by @alice • 2 hours ago                                   │      │
│  ├───────────────────────────────────────────────────────────────────┤      │
│  │  🔒 @alice switched to Solo mode                                   │      │
│  │  from Design Team • 3 hours ago                                    │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.7 API Endpoints for Web Interface

```python
# Teams API
GET    /api/v1/teams                    # List user's teams
POST   /api/v1/teams                    # Create team
GET    /api/v1/teams/{team_id}          # Get team details
PUT    /api/v1/teams/{team_id}          # Update team
DELETE /api/v1/teams/{team_id}          # Delete team
GET    /api/v1/teams/{team_id}/members  # List members
POST   /api/v1/teams/{team_id}/members  # Add member
DELETE /api/v1/teams/{team_id}/members/{user_id}  # Remove member
POST   /api/v1/teams/{team_id}/invite   # Send invite
GET    /api/v1/teams/{team_id}/activity # Team activity feed
GET    /api/v1/teams/{team_id}/memories # Team memories

# Vaults API
GET    /api/v1/vaults                   # List accessible vaults
POST   /api/v1/vaults                   # Create vault
GET    /api/v1/vaults/{vault_id}        # Get vault metadata
PUT    /api/v1/vaults/{vault_id}        # Update vault settings
DELETE /api/v1/vaults/{vault_id}        # Delete vault
POST   /api/v1/vaults/{vault_id}/unlock # Unlock vault (session)
POST   /api/v1/vaults/{vault_id}/lock   # Lock vault
GET    /api/v1/vaults/{vault_id}/secrets         # List secrets (names only)
POST   /api/v1/vaults/{vault_id}/secrets         # Add secret
GET    /api/v1/vaults/{vault_id}/secrets/{key}   # Get secret value
PUT    /api/v1/vaults/{vault_id}/secrets/{key}   # Update secret
DELETE /api/v1/vaults/{vault_id}/secrets/{key}   # Delete secret
GET    /api/v1/vaults/{vault_id}/audit   # Audit log
POST   /api/v1/vaults/{vault_id}/share   # Share vault

# Access Control API
GET    /api/v1/access/policies          # List policies
POST   /api/v1/access/policies          # Create policy
PUT    /api/v1/access/policies/{id}     # Update policy
DELETE /api/v1/access/policies/{id}     # Delete policy
POST   /api/v1/access/test              # Test access

# Mode API
GET    /api/v1/mode                     # Get current mode
POST   /api/v1/mode                     # Set mode
GET    /api/v1/mode/available           # List available modes

# Activity API
GET    /api/v1/activity                 # Get activity feed
GET    /api/v1/activity/me              # My activity only
```

### 9.8 New Admin HTML Files

```
admin/
├── teams.html           # Teams list and management
├── team-detail.html     # Single team view
├── vaults.html          # Vaults list
├── vault-detail.html    # Single vault view (secrets)
├── access.html          # ACL policy editor
├── static/
│   ├── teams.js         # Teams management logic
│   ├── vaults.js        # Vault management logic
│   ├── access.js        # ACL editor logic
│   ├── mode-switcher.js # Mode switching component
│   └── activity.js      # Activity feed component
```

### 9.9 Integration with Claude Code

The web interface complements the MCP tools:

| Task | Web Interface | MCP Tool |
|------|--------------|----------|
| Create team | Click "Create Team" | `create_team()` |
| Switch mode | Mode dropdown in header | `set_mode()` |
| Store secret | Vault detail → Add Secret | `store_in_vault()` |
| View audit | Vault → Audit Log tab | `vault_audit_log()` |
| Invite member | Team → Invite Member | `add_team_member()` |

The web interface is for:
- **Visual management** - bulk operations, dashboards
- **Administration** - ACL policies, audit review
- **Onboarding** - first-time setup, inviting others

MCP tools are for:
- **In-workflow access** - storing/retrieving during work
- **Automation** - scripts and agent coordination
- **CLI users** - developers who prefer terminal

---

## 10. Implementation Plan

### Phase 1: Foundation (Core Infrastructure)
1. Add teams and vaults SQLite tables
2. Implement Team and Vault data models
3. Add mode field to agent registry
4. Create Redis key structure for sessions

### Phase 2: Mode System
1. Implement `get_mode()`, `set_mode()`, `list_available_modes()` tools
2. Add mode inference logic
3. Update tool responses to include mode context
4. Add mode parameter to `store_memory()` and `search_memories()`

### Phase 3: Team Features
1. Implement team CRUD tools
2. Add team membership management
3. Create team-scoped memory collections
4. Implement team activity feed

### Phase 4: Vault Features
1. Implement vault encryption layer
2. Create vault management tools
3. Add vault access control
4. Implement audit logging

### Phase 5: Web Admin Interface
1. Create Teams management pages (teams.html, team-detail.html)
2. Create Vaults management pages (vaults.html, vault-detail.html)
3. Create Access Control page with ACL editor (access.html)
4. Implement Mode Switcher component in global header
5. Add Activity Feed to dashboard
6. Implement all REST API endpoints for web interface

### Phase 6: Integration & Polish
1. Add mode hints to all tool descriptions
2. Implement smart defaults
3. Add comprehensive audit trail
4. Sync MCP tools with web interface state
5. Add real-time updates via WebSocket for team activity

---

## 11. Open Questions

1. **Default Mode**: Should new users start in solo mode (safe) or team mode (collaborative)?
   - Recommendation: Solo mode as default for safety

2. **Mode Persistence**: How long should mode persist?
   - Recommendation: Per-session, reset on new session

3. **Cross-team Access**: Can users share memories across multiple teams?
   - Recommendation: Yes, with explicit share_with parameter

4. **Vault Rotation**: How to handle encryption key rotation?
   - Recommendation: Implement key versioning with gradual re-encryption

5. **Guest Access**: Should there be temporary access for external collaborators?
   - Recommendation: Yes, via time-limited guest tokens

---

## 12. Appendix: Tool Hierarchy

```
Mode Tools
├── get_mode()
├── set_mode()
└── list_available_modes()

Team Tools
├── create_team()
├── list_teams()
├── get_team()
├── add_team_member()
├── remove_team_member()
└── get_team_activity()

Vault Tools
├── create_vault()
├── list_vaults()
├── store_in_vault()
├── retrieve_from_vault()
├── share_vault()
└── vault_audit_log()

Memory Tools (updated)
├── store_memory(mode=...)
├── search_memories(mode=...)
├── get_recent_memories(mode=...)
└── delete_memory(mode=...)
```

---

## 13. Summary

This design provides:

1. **Clear Separation**: Solo/Vault/Team modes with distinct behaviors
2. **LLM Communication**: Mode signaling via tool responses, descriptions, and context hints
3. **Secure Vaults**: Encrypted storage with audit trails
4. **Team Collaboration**: Shared workspaces with role-based access
5. **Smart Defaults**: Inference-based mode selection with safe fallbacks
6. **Extensibility**: Foundation for future features (organizations, SSO, etc.)

The key insight is that MCP tools must both **signal context to the LLM** (via response metadata and tool descriptions) and **accept context from the LLM** (via optional mode parameters) to create a seamless experience.
