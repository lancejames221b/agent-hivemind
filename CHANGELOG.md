# Changelog

All notable changes to hAIveMind MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-01-12

### HTTP Vault Sync for Cross-Machine Synchronization

This release adds HTTP-based vault synchronization endpoints, enabling cross-machine command and config sync via Tailscale without requiring SSH key setup.

### Added

#### HTTP Vault Sync Endpoints - PR #10
- **New REST API endpoints** for vault synchronization over HTTP:
  - `GET /vault/list` - List all vault files (skills, configs, docs)
  - `GET /vault/manifest` - Get vault manifest with sync timestamps
  - `GET /vault/download.zip` - Download entire vault as ZIP archive
  - `GET /vault/skills/{filename}` - Download individual skill file
  - `GET /vault/configs/{filename}` - Download individual config file
  - `GET /vault/docs/{filename}` - Download individual doc file
  - `POST /vault/upload/{subdir}/{filename}` - Upload files to vault
- **Path traversal protection** on all file endpoints
- **Automatic manifest updates** on uploads with source machine tracking
- **Updated hivesink commands**:
  - `/hivesink-pull` - Now uses curl to download from HTTP endpoints
  - `/hivesink-push` - Now uses curl to upload to HTTP endpoints
  - Both support `--dry-run`, `--skills`, `--docs`, `--configs`, `--all` options

### Changed
- Vault sync no longer requires SSH key setup on client machines
- All sync operations work through Tailscale HTTP (firewall-friendly)
- Single ZIP download available for bulk sync operations

### Technical Details
- Endpoints integrated into existing FastMCP remote server (port 8900)
- Uses Starlette's `FileResponse` and `StreamingResponse` for efficient transfers
- ZIP creation uses Python's zipfile with `ZIP_DEFLATED` compression

---

## [2.0.0] - 2025-01-09

### Major Release - Production Ready

This release marks hAIveMind as production-ready with comprehensive features for distributed AI agent coordination, secure credential management, and token-optimized memory storage.

### Added

#### Token-Optimized Format System (v2) - PR #9
- **New format system** for 60-80% token reduction vs verbose prose
- Auto-teaches optimal compression on first memory access per session
- Symbol conventions: `->` (flow), `|` (or), `?` (optional), `!` (required), `::` (type)
- Tables preferred over prose for structured data
- Reference pattern: `[ID]: define -> use [ID]`
- All new memories automatically tagged with `format_version: v2`
- Legacy verbose memories flagged for potential compression
- **2 new MCP tools**:
  - `get_format_guide` - Get format guide (compact or detailed mode)
  - `get_memory_access_stats` - View session access statistics

#### Confidence System - Commit ad39c5a, 0ca3d88, ff27e97
- **Multi-dimensional confidence scoring** (0.0-1.0) based on 7 factors:
  - Freshness & Time Decay (20%) - Category-specific half-lives
  - Source Credibility (20%) - Expert vs novice, accuracy rate
  - Verification Status (15%) - Peer-verified, multi-verified, consensus
  - Consensus & Agreement (15%) - Multiple agents independently confirming
  - Contradiction Detection (10%) - Conflicting info auto-detected
  - Usage Success Rate (10%) - Track action outcomes
  - Context Relevance (10%) - Match to current project/task
- Visual confidence levels with actionable recommendations
- Risk-based action thresholds (low/medium/high/critical)
- Continuous learning from outcomes
- **8 new MCP tools**:
  - `get_memory_confidence` - Get confidence score breakdown
  - `verify_memory` - Verify memory accuracy (confirmed/outdated/incorrect)
  - `report_memory_usage` - Track usage outcomes (success/failure)
  - `search_high_confidence` - Find reliable information
  - `flag_outdated_memories` - Find stale information
  - `resolve_contradiction` - Resolve conflicting information
  - `vote_on_fact` - Vote on information accuracy
  - `get_agent_credibility` - Check agent trust level

#### Teams & Vaults System - PR #7, Commits 14b44a9, 24e5b66, 2c276b6
- **Operating modes**: Solo (private), Vault (secure secrets), Team (collaborative)
- **Team management** with role-based access control:
  - Roles: Owner, Admin, Member, Readonly, Guest
  - Activity tracking and audit logging
- **Encrypted vault storage** for credentials:
  - Vault types: Personal, Team, Project, Shared
  - XOR-based encryption (upgradeable to AES-GCM/Fernet)
  - Per-vault encryption keys
  - Complete audit trail for compliance
- **Access control** with read/write/admin permissions
- Expiration support for temporary access
- **17 new MCP tools**:
  - Mode Management (3): `get_mode`, `set_mode`, `list_available_modes`
  - Team Management (6): `create_team`, `list_teams`, `get_team`, `add_team_member`, `remove_team_member`, `get_team_activity`
  - Vault Management (8): `create_vault`, `list_vaults`, `store_in_vault`, `retrieve_from_vault`, `list_vault_secrets`, `delete_vault_secret`, `share_vault`, `vault_audit_log`

#### Audit Trail Security - PR #4
- Enhanced audit logging for all sensitive operations
- Secure storage of audit records
- Compliance-ready logging format

### Changed

- Updated README.md with comprehensive documentation
- Enhanced STARTUP_GUIDE.md with v2 format examples
- Improved MCP_INTEGRATION.md with new tool documentation
- Version bumped from 1.0.0 to 2.0.0

### Fixed

- Removed hardcoded paths from configuration files - PR #5
- WebSocket authentication fixes for reliable connections

### Technical Details

#### Tool Count Summary
- **Total MCP Tools**: 79+ tools
- Core Memory: 54 tools
- Teams & Vaults: 17 tools
- Confidence System: 8 tools

#### System Requirements
- Python 3.9+
- Redis 6.0+
- ChromaDB for vector storage
- Optional: PostgreSQL for credential vault

## [1.0.0] - 2024-08-25

### Initial Release

- Core memory storage with ChromaDB vector database
- Redis caching for performance
- Agent coordination system
- Multi-machine synchronization via Tailscale
- Basic memory operations (store, search, retrieve)
- Agent registration and task delegation
- Infrastructure state tracking
- Incident recording
- Runbook generation
- SSH config synchronization
- Playbook management
- Confluence/Jira integration
- MCP server hosting capabilities

---

## Migration Guide

### Upgrading from 1.x to 2.0

1. **Install new dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Update configuration**:
   - New sections in `config/config.json` for Teams & Vaults
   - Format system settings are automatic

3. **Database migrations**:
   - Teams & Vaults creates new SQLite tables automatically
   - Confidence system initializes its own schema
   - No manual migration required

4. **Using new features**:
   - Format v2 is opt-in: just store using new conventions
   - Teams/Vaults: create team first, then create vault
   - Confidence: scores are automatic, verify to improve

### Breaking Changes

None - 2.0 is backward compatible with 1.x stored memories.

---

## Contributors

- Lance James (Unit 221B, Inc) - Author
- Claude Code (Anthropic) - Implementation assistance

## License

MIT License - See LICENSE file for details.
