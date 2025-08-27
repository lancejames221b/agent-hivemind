# hv-sync-hooks

Automated ticket-memory synchronization with pre/post work hooks integration.

## Usage

```
/hv-sync-hooks status
/hv-sync-hooks trigger <event_type> [ticket_id] [project_id]
/hv-sync-hooks sync-with-hooks [command_type] [--force] [--verbose]
```

## Commands

### Status Check
```
/hv-sync-hooks status
```
Get current status of registered sync hooks, protocol version, and execution history.

### Manual Hook Trigger
```
/hv-sync-hooks trigger pre_work WEBTESTS-1 memory-mcp-project
/hv-sync-hooks trigger post_work WEBTESTS-1 memory-mcp-project --results "Completed web testing setup"
```
Manually trigger sync hooks for testing or recovery purposes.

### Sync with Hooks
```
/hv-sync-hooks sync-with-hooks install_sync --verbose
/hv-sync-hooks sync-with-hooks install_commands --force
```
Execute sync commands with automated pre/post hooks integration.

## Features

- **Automated Pre-Work Hooks**: Capture ticket context, check related memories, store work intentions
- **Automated Post-Work Hooks**: Store completion results, document lessons learned, broadcast discoveries
- **Network Sync Integration**: Hooks automatically integrate with existing install_sync and install_commands
- **Zero Manual Overhead**: Hooks trigger automatically on ticket status changes (when configured)
- **hAIveMind Knowledge Sharing**: Results automatically shared across the collective intelligence network

## Integration with Existing Commands

The sync hooks system integrates seamlessly with existing hAIveMind commands:

- **hv-sync**: Now includes automatic pre/post hooks when used with --hooks flag
- **hv-install**: Command installation now triggers knowledge synchronization hooks  
- **hv-broadcast**: Hook results can be automatically broadcast to the collective
- **hv-delegate**: Task delegation can trigger coordination hooks

## Configuration

Sync protocol is configured via `sync-protocol.json`:

```json
{
  "protocol_version": "1.0",
  "compliance_level": "REQUIRED",
  "auto_remind": true,
  "pre_sync_checklist": [
    "Read ticket description and current status",
    "Check hAIveMind memory for related context",
    "Store work intention with expected outcomes"
  ],
  "post_sync_checklist": [
    "Update ticket status with detailed completion notes", 
    "Store comprehensive results in hAIveMind memory",
    "Document lessons learned and troubleshooting solutions"
  ]
}
```

## Memory Categories

Hooks automatically categorize stored information:

- `workflow` - Ticket synchronization events and work tracking
- `lessons_learned` - Key insights from completed work
- `troubleshooting` - Solutions to common problems discovered during work
- `dependencies` - Cross-ticket relationships and coordination info
- `agent_coordination` - Multi-agent collaboration and task delegation

This command provides the automation layer that makes knowledge capture and sharing effortless across the hAIveMind collective.