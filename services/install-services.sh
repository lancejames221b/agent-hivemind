#!/bin/bash
# Install Memory MCP Services

echo "=== Installing Memory MCP Services ==="

# Check if running as root/sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script needs to be run with sudo privileges"
    echo "Usage: sudo bash services/install-services.sh"
    exit 1
fi

# Copy service files to systemd directory
echo "📁 Copying service files..."
cp /home/lj/memory-mcp/services/memory-mcp-server.service /etc/systemd/system/
cp /home/lj/memory-mcp/services/memory-sync-service.service /etc/systemd/system/
cp /home/lj/memory-mcp/services/memory-remote-mcp.service /etc/systemd/system/

# Set correct permissions
chmod 644 /etc/systemd/system/memory-mcp-server.service
chmod 644 /etc/systemd/system/memory-sync-service.service
chmod 644 /etc/systemd/system/memory-remote-mcp.service

# Reload systemd daemon
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# Enable services for auto-start
echo "🚀 Enabling services..."
systemctl enable memory-mcp-server.service
systemctl enable memory-sync-service.service
systemctl enable memory-remote-mcp.service

# Start services
echo "▶️  Starting services..."
systemctl start memory-mcp-server.service
systemctl start memory-sync-service.service
systemctl start memory-remote-mcp.service

# Check status
echo "📊 Service Status:"
systemctl status memory-mcp-server.service --no-pager -l
echo ""
systemctl status memory-sync-service.service --no-pager -l
echo ""
systemctl status memory-remote-mcp.service --no-pager -l

echo ""
echo "✅ Memory MCP Services installed and started!"
echo ""
echo "📋 Management commands:"
echo "  sudo systemctl start memory-mcp-server"
echo "  sudo systemctl stop memory-mcp-server" 
echo "  sudo systemctl restart memory-mcp-server"
echo "  sudo systemctl status memory-mcp-server"
echo ""
echo "  sudo systemctl start memory-sync-service"
echo "  sudo systemctl stop memory-sync-service"
echo "  sudo systemctl restart memory-sync-service"
echo "  sudo systemctl status memory-sync-service"
echo ""
echo "  sudo systemctl start memory-remote-mcp"
echo "  sudo systemctl stop memory-remote-mcp"
echo "  sudo systemctl restart memory-remote-mcp"
echo "  sudo systemctl status memory-remote-mcp"
echo ""
echo "📜 View logs:"
echo "  sudo journalctl -u memory-mcp-server -f"
echo "  sudo journalctl -u memory-sync-service -f"
echo "  sudo journalctl -u memory-remote-mcp -f"
echo ""
echo "🌐 Remote MCP endpoints:"
echo "  SSE: http://lance-dev:8900/sse"
echo "  Streamable HTTP: http://lance-dev:8900/mcp"
echo "  Health: http://lance-dev:8900/health"