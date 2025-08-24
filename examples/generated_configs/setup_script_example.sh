#!/bin/bash
# hAIveMind MCP Client Setup Script
# Generated for client: abc123def456
# Created: 2025-08-24T22:41:26.299268

set -e

echo '🧠 Setting up hAIveMind MCP Client...'

# Install dependencies
if ! command -v npx &> /dev/null; then
    echo 'Installing Node.js and npm...'
    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# Install MCP HTTP proxy
echo 'Installing MCP HTTP proxy...'
npm install -g @modelcontextprotocol/server-http

# Create configuration directory
mkdir -p ~/.config/claude

# Generate .mcp.json configuration
cat > .mcp.json << 'EOF'
{
  "mcpServers": {
    "aggregator": {
      "command": "npx",
      "args": [
        "@modelcontextprotocol/server-http",
        "http://0.0.0.0:8950/sse"
      ],
      "env": {
        "HTTP_TIMEOUT": "30000",
        "AUTHORIZATION": "Bearer your-auth-token-here"
      }
    },
    "memory-server": {
      "command": "npx",
      "args": [
        "@modelcontextprotocol/server-http", 
        "http://localhost:8900/sse"
      ],
      "env": {
        "HTTP_TIMEOUT": "30000",
        "AUTHORIZATION": "Bearer your-auth-token-here"
      }
    }
  }
}
EOF

echo '✅ hAIveMind MCP Client setup complete!'
echo '📋 Configuration saved to .mcp.json'

# Test connections
echo '🔍 Testing server connections...'
echo 'Testing MCP Aggregator...'
curl -s -f http://0.0.0.0:8950/health > /dev/null && echo '✅ MCP Aggregator is healthy' || echo '❌ MCP Aggregator is unreachable'
echo 'Testing hAIveMind Memory...'
curl -s -f http://localhost:8900/health > /dev/null && echo '✅ hAIveMind Memory is healthy' || echo '❌ hAIveMind Memory is unreachable'

echo '🚀 Setup complete! You can now use hAIveMind MCP tools.'