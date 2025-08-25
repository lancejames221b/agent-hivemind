# Dashboard Port Configuration Migration

## Overview
This document describes the migration of the dashboard from port 8901 to port 8900, integrating it with the remote MCP server to resolve port conflicts and provide unified access.

## Changes Made

### 1. Port Configuration Updates
- **Before**: Dashboard on port 8901, MCP server on port 8900
- **After**: Both dashboard and MCP server on port 8900

### 2. Files Updated
The following files were updated to change port references from 8901 to 8900:

#### Source Code Files:
- `src/workflow_integration.py`
- `src/workflow_dashboard.py` 
- `src/rules_dashboard_integration.py`
- `src/dashboard_server.py`
- `src/remote_mcp_server.py` (enhanced with dashboard functionality)

#### Scripts:
- `scripts/reset_admin_password.py`
- `scripts/get_admin_creds.py`

#### Documentation:
- `docs/MCP_REGISTRY_ARCHITECTURE.md`
- `WORKFLOW_AUTOMATION_SUMMARY.md`
- `WORKFLOW_AUTOMATION_GUIDE.md`
- `STORY_3C_IMPLEMENTATION_SUMMARY.md`

#### Configuration:
- `config/config.json` (updated discovery ports)

### 3. Integration Changes

#### Remote MCP Server Enhancements:
- Added `_init_dashboard_functionality()` method
- Integrated dashboard database and configuration generator
- Added enhanced dashboard routes:
  - `/admin/api/dashboard-stats` - Enhanced statistics
  - `/admin/api/devices` - Device management
  - `/admin/api/config/generate` - Configuration generation
- Added proper admin root route handling for `/admin/` and `/admin`

#### Route Structure:
- **Root Admin**: `http://localhost:8900/admin/` → dashboard.html
- **Dashboard**: `http://localhost:8900/admin/dashboard.html`
- **MCP SSE**: `http://localhost:8900/sse`
- **Health Check**: `http://localhost:8900/health`
- **API Routes**: `http://localhost:8900/admin/api/*`

## Benefits

### 1. Unified Access
- Single port (8900) for both MCP and dashboard functionality
- Simplified configuration and deployment
- Reduced port conflicts

### 2. Better Integration
- Dashboard can directly access MCP server functionality
- Shared authentication and security context
- Consistent logging and monitoring

### 3. Improved User Experience
- No confusion about which port to use
- Unified documentation and URLs
- Simplified setup instructions

## Access URLs

After migration, all access is through port 8900:

```bash
# Dashboard
http://localhost:8900/admin/

# Specific admin pages
http://localhost:8900/admin/dashboard.html
http://localhost:8900/admin/memory.html
http://localhost:8900/admin/mcp_servers.html

# MCP Server endpoints
http://localhost:8900/sse          # SSE transport
http://localhost:8900/mcp          # HTTP transport  
http://localhost:8900/health       # Health check

# API endpoints
http://localhost:8900/admin/api/stats
http://localhost:8900/admin/api/login
http://localhost:8900/admin/api/devices
```

## Testing

The integration was tested to verify:
- ✅ Health endpoint accessible
- ✅ Dashboard HTML pages load correctly
- ✅ MCP SSE endpoint remains functional
- ✅ Admin routes work properly
- ✅ No port conflicts

## Migration Impact

### Backward Compatibility
- Old port 8901 references updated throughout codebase
- Documentation updated to reflect new URLs
- Scripts and tools updated to use port 8900

### Configuration Changes
- Discovery ports updated in `config.json`
- MCP registry architecture updated
- Workflow automation guides updated

## Troubleshooting

If you encounter issues after migration:

1. **Check port availability**:
   ```bash
   netstat -tlnp | grep 8900
   ```

2. **Verify server startup**:
   ```bash
   python3 src/remote_mcp_server.py --port 8900
   ```

3. **Test endpoints**:
   ```bash
   curl http://localhost:8900/health
   curl http://localhost:8900/admin/dashboard.html
   ```

## Future Considerations

- Consider adding SSL/TLS support for production deployments
- Monitor performance impact of unified server
- Evaluate need for load balancing if traffic increases
- Consider containerization for easier deployment

## Conclusion

The dashboard port migration successfully resolves the port conflict while maintaining full functionality of both the MCP server and dashboard. Users now have a unified access point at port 8900 for all hAIveMind functionality.