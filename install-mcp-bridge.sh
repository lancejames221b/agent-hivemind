#!/bin/bash
# hAIveMind MCP Bridge Installation Script

set -e

echo "🚀 Installing hAIveMind MCP Bridge Client..."

# Create local bin directory
mkdir -p ~/.local/bin

# Copy bridge client
cp haivemind-mcp-client ~/.local/bin/
chmod +x ~/.local/bin/haivemind-mcp-client

# Add to PATH if not already there
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    echo "📝 Added ~/.local/bin to PATH in ~/.bashrc"
fi

# Create cursor MCP configuration directory
mkdir -p .cursor

# Copy MCP configuration
cp .cursor/mcp.json .cursor/mcp.json 2>/dev/null || echo "MCP config already exists"

echo "✅ hAIveMind MCP Bridge Client installed successfully!"
echo ""
echo "Next steps:"
echo "1. Start hAIveMind services:"
echo "   python src/memory_server.py &"
echo "   python src/remote_mcp_server.py &"
echo "   python src/sync_service.py &"
echo ""
echo "2. Test the integration:"
echo "   cursor-agent mcp list-tools haivemind"
echo ""
echo "3. Read the full documentation:"
echo "   cat MCP_INTEGRATION.md"
echo ""
echo "🎉 hAIveMind MCP integration is ready!"