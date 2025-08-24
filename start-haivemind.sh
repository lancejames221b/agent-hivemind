#!/bin/bash
# hAIveMind Unified Startup Script
# Starts all hAIveMind services with proper configuration

set -e

echo "🧠 Starting hAIveMind Collective Intelligence Network"
echo "==================================================="

# Change to hAIveMind directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Kill any existing servers
echo "🛑 Stopping any existing hAIveMind services..."
pkill -f "memory_server.py" 2>/dev/null || true
pkill -f "remote_mcp_server.py" 2>/dev/null || true  
pkill -f "sync_service.py" 2>/dev/null || true
sleep 2

# Check if Redis is running
echo "🔍 Checking Redis status..."
if ! redis-cli ping >/dev/null 2>&1; then
    echo "⚠️  Redis not running. Starting Redis..."
    sudo systemctl start redis-server || {
        echo "❌ Failed to start Redis. Please start manually: sudo systemctl start redis-server"
        exit 1
    }
fi

# Ensure Python virtual environment is available
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run: python -m venv venv && venv/bin/pip install -r requirements.txt"
    exit 1
fi

PYTHON="$SCRIPT_DIR/venv/bin/python"

echo ""
echo "🚀 Starting hAIveMind services..."

# Start Memory Server (stdio MCP)
echo "  📡 Starting Memory Server (stdio MCP)..."
nohup $PYTHON src/memory_server.py > logs/memory_server.log 2>&1 &
MEMORY_PID=$!
echo "    ✅ Memory Server started (PID: $MEMORY_PID)"

# Start Remote MCP Server (HTTP/SSE) 
echo "  🌐 Starting Remote MCP Server (HTTP/SSE on port 8900)..."
mkdir -p logs
nohup $PYTHON src/remote_mcp_server.py --host 0.0.0.0 --port 8900 > logs/remote_mcp_server.log 2>&1 &
REMOTE_PID=$!
echo "    ✅ Remote MCP Server started (PID: $REMOTE_PID)"

# Start Sync Service
echo "  🔄 Starting Sync Service (API on port 8899)..."
nohup $PYTHON src/sync_service.py --port 8899 > logs/sync_service.log 2>&1 &
SYNC_PID=$!
echo "    ✅ Sync Service started (PID: $SYNC_PID)"

# Give services time to start
echo ""
echo "⏳ Waiting for services to initialize..."
sleep 5

# Verify services are running
echo ""
echo "🔍 Verifying service status..."

# Check Memory Server (no HTTP endpoint, just check process)
if kill -0 $MEMORY_PID 2>/dev/null; then
    echo "  ✅ Memory Server: Running (PID: $MEMORY_PID)"
else
    echo "  ❌ Memory Server: Failed to start"
fi

# Check Remote MCP Server
if curl -s http://localhost:8900/health >/dev/null 2>&1; then
    echo "  ✅ Remote MCP Server: Running on http://localhost:8900"
else
    echo "  ❌ Remote MCP Server: Not responding on port 8900"
fi

# Check Sync Service  
if curl -s http://localhost:8899/api/status >/dev/null 2>&1; then
    echo "  ✅ Sync Service: Running on http://localhost:8899"
else
    echo "  ❌ Sync Service: Not responding on port 8899"
fi

echo ""
echo "🎉 hAIveMind Startup Complete!"
echo ""
echo "📋 Service Information:"
echo "  • Memory Server (stdio MCP): Ready for local Claude Code connections"
echo "  • Remote MCP Server: http://lance-dev:8900 (for remote agents)"
echo "  • Sync Service API: http://lance-dev:8899 (for machine-to-machine sync)"
echo "  • Admin Interface: http://lance-dev:8900/admin (login: admin/Unit221B)"
echo ""
echo "🔧 Connection Commands:"
echo "  • Local Claude Code: Already configured via .mcp.json"
echo "  • Remote Claude Code: claude mcp add --transport sse haivemind http://lance-dev:8900/sse"
echo "  • Install commands: run install_agent_commands or /hv-install"
echo ""
echo "📊 Monitor Services:"
echo "  • Memory Server logs: tail -f logs/memory_server.log"
echo "  • Remote MCP logs: tail -f logs/remote_mcp_server.log" 
echo "  • Sync Service logs: tail -f logs/sync_service.log"
echo ""
echo "🧠 Welcome to the hAIveMind collective intelligence network!"
echo ""
echo "PIDs: Memory=$MEMORY_PID, Remote=$REMOTE_PID, Sync=$SYNC_PID"