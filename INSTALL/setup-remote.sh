#!/bin/bash
# Memory MCP Server - Remote Machine Setup Script
# Usage: bash setup-remote.sh

echo "=== Memory MCP Remote Setup ==="
echo

# Check if npm is available
if ! command -v npm &> /dev/null; then
    echo "❌ npm not found. Please install Node.js first."
    exit 1
fi

# Install HTTP MCP server if not already installed
echo "📦 Installing @modelcontextprotocol/server-http..."
npm install -g @modelcontextprotocol/server-http

# Test connection to lance-dev
echo
echo "🔗 Testing connection to memory server..."

# Try Tailscale hostname first
if curl -s --connect-timeout 5 http://lance-dev:8899/api/status > /dev/null; then
    ENDPOINT="http://lance-dev:8899"
    echo "✅ Connected via Tailscale: lance-dev"
# Try external IP as fallback  
elif curl -s --connect-timeout 5 http://34.72.136.20:8899/api/status > /dev/null; then
    ENDPOINT="http://34.72.136.20:8899"
    echo "✅ Connected via external IP: 34.72.136.20"
else
    echo "❌ Cannot connect to memory server"
    echo "   Check network connectivity and ensure lance-dev services are running"
    exit 1
fi

# Create .mcp.json file
echo
echo "📄 Creating .mcp.json configuration..."

cat > .mcp.json << EOF
{
  "mcpServers": {
    "remote-memory": {
      "command": "npx",
      "args": [
        "@modelcontextprotocol/server-http",
        "${ENDPOINT}"
      ],
      "env": {
        "HTTP_TIMEOUT": "30000"
      }
    }
  }
}
EOF

echo "✅ Created .mcp.json in current directory"

# Test the configuration
echo
echo "🧪 Testing MCP configuration..."
SERVER_STATUS=$(curl -s ${ENDPOINT}/api/status)
if [ $? -eq 0 ]; then
    echo "✅ Memory server is responding"
    echo "   Machine: $(echo $SERVER_STATUS | jq -r '.machine_id' 2>/dev/null || echo 'lance-dev')"
    echo "   Available machines: $(echo $SERVER_STATUS | jq -r '.known_machines[]' 2>/dev/null | tr '\n' ' ' || echo 'N/A')"
else
    echo "❌ Server test failed"
fi

echo
echo "🎉 Setup complete!"
echo "   The memory MCP server is now available to Claude Code"
echo "   Available tools: store_memory, search_memories, retrieve_memory, get_recent_memories, get_memory_stats"
echo
echo "💡 To verify: Start Claude Code and check if memory tools are available"