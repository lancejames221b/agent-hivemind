# MCP Session Troubleshooting Guide

## Overview
This guide helps troubleshoot and resolve session-related issues with the hAIveMind MCP server, particularly the "Could not find session" error.

## Common Issues

### 1. Session Not Found (HTTP 404)

**Symptoms:**
- Error message: "Error POSTing to endpoint (HTTP 404): Could not find session"
- MCP tools fail to execute
- Server logs show: `POST /messages/?session_id=XXX HTTP/1.1" 404 Not Found`

**Root Causes:**
- Session expired due to inactivity
- Server restart cleared active sessions
- Client-server session synchronization issues
- FastMCP session manager not properly initialized

**Solutions:**

#### Quick Fix - Manual Session Refresh
```bash
# Get JWT token for admin API
TOKEN=$(curl -s -X POST http://localhost:8900/admin/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | jq -r '.token')

# Check session health
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8900/admin/api/sessions/health

# Force refresh all sessions
curl -H "Authorization: Bearer $TOKEN" \
  -X POST http://localhost:8900/admin/api/sessions/refresh \
  -H "Content-Type: application/json" -d '{}'
```

#### Debug Session State
```bash
# Get detailed debug information
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8900/admin/api/sessions/debug

# Cleanup terminated sessions
curl -H "Authorization: Bearer $TOKEN" \
  -X POST http://localhost:8900/admin/api/sessions/cleanup
```

### 2. Session Timeout Issues

**Prevention:**
1. **Increase timeout in .mcp.json:**
   ```json
   {
     "mcpServers": {
       "haivemind": {
         "env": {
           "HTTP_TIMEOUT": "60000",
           "KEEP_ALIVE": "true"
         }
       }
     }
   }
   ```

2. **Enable session persistence:**
   - Server now maintains `active_sessions` and `session_last_activity` stores
   - Sessions are tracked across requests
   - Automatic cleanup of terminated sessions

### 3. Server Restart Recovery

**When server restarts:**
1. All active sessions are lost
2. Clients need to reconnect to establish new sessions
3. Use session health check to verify connectivity

**Recovery Steps:**
1. Restart the hAIveMind server
2. Wait for full initialization (check logs for "Session management endpoints registered")
3. Test connectivity with session health endpoint
4. If issues persist, clean up old session state

## Monitoring Session Health

### Automated Health Checks
```bash
#!/bin/bash
# Add to cron for automated monitoring

TOKEN=$(curl -s -X POST http://localhost:8900/admin/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | jq -r '.token')

HEALTH=$(curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8900/admin/api/sessions/health | jq -r '.status')

if [ "$HEALTH" != "healthy" ]; then
    echo "$(date): Session health check failed" >> /var/log/haivemind-sessions.log
    # Trigger cleanup
    curl -s -H "Authorization: Bearer $TOKEN" \
      -X POST http://localhost:8900/admin/api/sessions/cleanup
fi
```

### Key Metrics to Monitor
- Active session count
- Session creation/termination rate
- Average session lifetime
- Failed connection attempts

## Best Practices

### For Development
1. **Always check session health after server restarts**
2. **Use debug endpoints to understand session state**
3. **Monitor server logs for session-related errors**
4. **Keep backup of working .mcp.json configuration**

### For Production
1. **Implement session health monitoring**
2. **Set up automated session cleanup**
3. **Configure appropriate timeout values**
4. **Log session lifecycle events**
5. **Have rollback plan for configuration changes**

## Technical Details

### Session Lifecycle
1. **Connection:** Client connects to SSE endpoint `/sse`
2. **Session Creation:** FastMCP creates new session with UUID
3. **Tool Execution:** Client sends requests to `/messages/?session_id=XXX`
4. **Session Tracking:** Server maintains session state in memory
5. **Cleanup:** Terminated sessions removed from active pool

### FastMCP Configuration
```python
self.mcp = FastMCP(
    name="hAIveMind Collective Memory",
    host=self.host,
    port=self.port,
    sse_path="/sse",
    message_path="/messages/",
    mount_path="/",
    stateless_http=False  # Key: Enable stateful sessions
)
```

## Recovery Procedures

### Complete Session Reset
```bash
# 1. Stop hAIveMind server
kill $(pgrep -f remote_mcp_server.py)

# 2. Clear any cached client connections
# (Restart Claude Code if needed)

# 3. Start server with clean state
cd /home/lj/memory-mcp
source venv/bin/activate
python src/remote_mcp_server.py --host 0.0.0.0 --port 8900

# 4. Verify health
curl http://localhost:8900/health
```

### Emergency Troubleshooting
If all else fails:
1. Check server process is running: `pgrep -f remote_mcp_server.py`
2. Verify port is listening: `netstat -tlnp | grep 8900`
3. Check logs for errors: `tail -f logs/haivemind.log`
4. Test basic connectivity: `curl http://localhost:8900/health`
5. Restart with debug logging enabled

## Future Improvements

### Planned Enhancements
- [ ] Automatic session recovery on client reconnect
- [ ] Session persistence across server restarts
- [ ] Connection pooling and load balancing
- [ ] Advanced retry logic with exponential backoff
- [ ] Session metrics and alerting
- [ ] Database-backed session storage

### Configuration Tuning
- Optimize timeout values based on usage patterns
- Implement session cleanup schedules
- Add circuit breaker patterns for failed connections
- Configure session affinity for multi-server setups

---

**Last Updated:** $(date)
**Version:** 1.0
**Status:** Active troubleshooting procedures