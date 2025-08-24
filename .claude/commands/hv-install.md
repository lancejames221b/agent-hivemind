---
description: Install or update hAIveMind commands and configuration
allowed-tools: ["mcp__haivemind__*", "Write", "Read", "Edit", "LS", "Bash"]
argument-hint: Optional: target (personal/project) or clean
---

Install/update hAIveMind commands and configuration.

$ARGUMENTS

Options:
- `personal` - Install to personal commands (~/.claude/commands/)
- `project` - Install to project commands (.claude/commands/)
- `clean` - Remove and reinstall all commands
- (no args) - Smart install based on context

This command performs:
1. **Location Detection**: Determine best install location (personal vs project)
2. **Version Check**: Compare installed vs available command versions
3. **Command Installation**: Copy/update hv-* commands from collective
4. **CLAUDE.md Integration**: Inject hAIveMind sections into CLAUDE.md
5. **Agent Registration**: Register this agent with the collective
6. **Permissions Setup**: Ensure proper tool access permissions

First-time setup will:
- Create command directories if needed
- Install all hv-* commands
- Configure agent identity and capabilities
- Establish connection to collective memory
- Set up automatic sync preferences

Updates will only modify changed commands and configurations.