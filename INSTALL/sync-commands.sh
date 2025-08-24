#!/bin/bash
# hAIveMind Command Sync Script
# Installs hv-* commands to Claude Code and syncs agent configuration

set -e

echo "🧠 hAIveMind Agent Command Sync"
echo "================================"

# Check if we're in the right directory
if [ ! -f "src/memory_server.py" ]; then
    echo "❌ Error: Please run this script from the agent-hivemind directory"
    exit 1
fi

# Detect Claude directory
CLAUDE_DIR=""
if [ -d ".claude" ]; then
    CLAUDE_DIR=".claude/commands"
    echo "📁 Found project Claude directory: $CLAUDE_DIR"
elif [ -d "$HOME/.claude" ]; then
    CLAUDE_DIR="$HOME/.claude/commands"  
    echo "📁 Found personal Claude directory: $CLAUDE_DIR"
else
    echo "❓ Claude directory not found. Creating personal commands directory..."
    CLAUDE_DIR="$HOME/.claude/commands"
    mkdir -p "$CLAUDE_DIR"
fi

# Create commands directory if needed
mkdir -p "$CLAUDE_DIR"

# Copy hv-* commands
echo "📦 Installing hAIveMind commands..."
command_count=0
for cmd_file in commands/hv-*.md; do
    if [ -f "$cmd_file" ]; then
        cmd_name=$(basename "$cmd_file")
        cp "$cmd_file" "$CLAUDE_DIR/"
        echo "  ✅ Installed: $cmd_name"
        ((command_count++))
    fi
done

echo ""
echo "🎉 Installation Complete!"
echo "   📦 Installed $command_count hv-* commands"
echo "   📁 Location: $CLAUDE_DIR"
echo ""
echo "Next steps:"
echo "1. Ensure hAIveMind MCP server is running"
echo "2. Connect Claude Code to hAIveMind via MCP"
echo "3. Run: /hv-install to complete agent setup"
echo "4. Run: /hv-status to check collective status"
echo ""
echo "🧠 Welcome to the hAIveMind collective intelligence network!"