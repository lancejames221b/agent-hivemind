#!/bin/bash
# hAIveMind MCP Client Installation Script

set -e

echo "🚀 Installing hAIveMind MCP Client..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_DIR="$SCRIPT_DIR"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r "$CLIENT_DIR/requirements.txt"

# Make the standalone client executable
chmod +x "$CLIENT_DIR/src/haivemind-mcp-standalone.py"
chmod +x "$CLIENT_DIR/src/haivemind-mcp-bridge.py"

# Create symlinks in user's local bin (optional)
mkdir -p ~/.local/bin
ln -sf "$CLIENT_DIR/src/haivemind-mcp-standalone.py" ~/.local/bin/haivemind-mcp
ln -sf "$CLIENT_DIR/src/haivemind-mcp-bridge.py" ~/.local/bin/haivemind-mcp-bridge

echo "✅ hAIveMind MCP Client installed successfully!"
echo ""
echo "📋 Available configurations:"
echo "  • cursor-agent: $CLIENT_DIR/config/cursor-agent.json"
echo "  • Claude Desktop: $CLIENT_DIR/config/claude-desktop.json"
echo "  • Remote Access: $CLIENT_DIR/config/remote-access.json"
echo ""
echo "🔧 To use with cursor-agent:"
echo "  1. Copy config: cp $CLIENT_DIR/config/cursor-agent.json .cursor/mcp.json"
echo "  2. Test: cursor-agent mcp list-tools haivemind"
echo ""
echo "🔧 To use with Claude Desktop:"
echo "  1. Update path in: $CLIENT_DIR/config/claude-desktop.json"
echo "  2. Add to Claude Desktop settings"
echo ""
echo "📚 Read the documentation: $CLIENT_DIR/docs/README.md"