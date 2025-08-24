#!/bin/bash
# hAIveMind Command Sync Script
# Installs hv-* commands to Claude Code and syncs agent configuration

set -e

echo "🧠 hAIveMind Agent Command Sync"
echo "================================"

# Expected command files
EXPECTED_COMMANDS=("hv-broadcast.md" "hv-delegate.md" "hv-install.md" "hv-query.md" "hv-status.md" "hv-sync.md")
EXPECTED_COUNT=${#EXPECTED_COMMANDS[@]}

# Check if we're in the right directory
if [ ! -f "src/memory_server.py" ]; then
    echo "❌ Error: Please run this script from the memory-mcp directory"
    exit 1
fi

# Check if commands directory exists
if [ ! -d "commands" ]; then
    echo "❌ Error: commands directory not found"
    exit 1
fi

# Verify all expected command files exist
echo "🔍 Verifying command files..."
missing_commands=()
for cmd in "${EXPECTED_COMMANDS[@]}"; do
    if [ ! -f "commands/$cmd" ]; then
        missing_commands+=("$cmd")
    fi
done

if [ ${#missing_commands[@]} -gt 0 ]; then
    echo "❌ Error: Missing command files:"
    for cmd in "${missing_commands[@]}"; do
        echo "   - $cmd"
    done
    exit 1
fi
echo "  ✅ All $EXPECTED_COUNT expected command files found"

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
    if ! mkdir -p "$CLAUDE_DIR"; then
        echo "❌ Error: Failed to create Claude commands directory: $CLAUDE_DIR"
        exit 1
    fi
fi

# Create commands directory if needed
if ! mkdir -p "$CLAUDE_DIR"; then
    echo "❌ Error: Failed to create commands directory: $CLAUDE_DIR"
    exit 1
fi

# Copy hv-* commands with error checking
echo "📦 Installing hAIveMind commands..."
command_count=0
failed_commands=()

for cmd_file in commands/hv-*.md; do
    if [ -f "$cmd_file" ]; then
        cmd_name=$(basename "$cmd_file")
        if cp "$cmd_file" "$CLAUDE_DIR/" 2>/dev/null; then
            echo "  ✅ Installed: $cmd_name"
            command_count=$((command_count + 1))
        else
            echo "  ❌ Failed to install: $cmd_name"
            failed_commands+=("$cmd_name")
        fi
    fi
done

# Check if any commands failed to install
if [ ${#failed_commands[@]} -gt 0 ]; then
    echo ""
    echo "⚠️  Installation completed with errors:"
    echo "   ❌ Failed to install: ${#failed_commands[@]} commands"
    for cmd in "${failed_commands[@]}"; do
        echo "      - $cmd"
    done
    echo "   ✅ Successfully installed: $command_count commands"
    echo "   📁 Location: $CLAUDE_DIR"
    echo ""
    echo "❌ Please resolve the errors and run the script again"
    exit 1
fi

# Verify all expected commands were installed
echo ""
if [ $command_count -eq $EXPECTED_COUNT ]; then
    echo "🎉 Installation Complete!"
    echo "   ✅ Successfully installed all $command_count hv-* commands"
    echo "   📁 Location: $CLAUDE_DIR"
    
    # Final verification - check that files actually exist in destination
    echo ""
    echo "🔍 Final verification..."
    verification_failed=()
    for cmd in "${EXPECTED_COMMANDS[@]}"; do
        if [ ! -f "$CLAUDE_DIR/$cmd" ]; then
            verification_failed+=("$cmd")
        fi
    done
    
    if [ ${#verification_failed[@]} -gt 0 ]; then
        echo "❌ Verification failed! Missing commands in destination:"
        for cmd in "${verification_failed[@]}"; do
            echo "   - $cmd"
        done
        exit 1
    else
        echo "  ✅ All commands verified in destination directory"
    fi
    
    echo ""
    echo "Next steps:"
    echo "1. Ensure hAIveMind MCP server is running"
    echo "2. Connect Claude Code to hAIveMind via MCP"
    echo "3. Run: /hv-install to complete agent setup"
    echo "4. Run: /hv-status to check collective status"
    echo ""
    echo "🧠 Welcome to the hAIveMind collective intelligence network!"
else
    echo "❌ Installation incomplete!"
    echo "   Expected: $EXPECTED_COUNT commands"
    echo "   Installed: $command_count commands"
    echo "   Missing: $((EXPECTED_COUNT - command_count)) commands"
    exit 1
fi