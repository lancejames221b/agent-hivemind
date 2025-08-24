---
description: Sync hAIveMind commands and configuration from collective
allowed-tools: ["mcp__haivemind__*", "Write", "Read", "Edit"]
argument-hint: Optional: force, status, or verbose
---

Sync the latest hAIveMind commands and configuration from the collective:

$ARGUMENTS

Available options:
- `force` - Force full resync even if up to date
- `status` - Show current sync status only  
- `verbose` - Show detailed step-by-step sync progress

This command will:
1. Check for command updates from hAIveMind collective
2. Update all hv-* commands to latest versions  
3. Sync CLAUDE.md instructions specific to this agent/project
4. Register/update this agent in the collective registry
5. Report sync status and any changes made

The sync process pulls from the centralized command templates and CLAUDE.md configurations stored in the hAIveMind collective memory system.

Use `verbose` for detailed real-time progress during sync operations.