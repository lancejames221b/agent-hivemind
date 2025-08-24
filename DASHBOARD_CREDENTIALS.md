# hAIveMind Control Dashboard Credentials

## Access Information
- **URL**: http://localhost:8901/admin/dashboard.html
- **Username**: admin  
- **Password**: admin123
- **API Docs**: http://localhost:8901/docs

## Dashboard Features
- **User Management**: Create accounts, assign roles (admin/operator/viewer/agent)
- **Device Management**: Register devices, approve connections, manage device groups
- **API Key Management**: Generate keys with scoped permissions, download MCP configs
- **IP Whitelisting**: Access control and security settings
- **Activity Monitoring**: Complete audit logs and access tracking
- **MCP Configuration Generation**: Automatic .mcp.json files for Claude Desktop/Code

## Utilities
- **Password Reset**: `/home/lj/memory-mcp/reset_admin_password.py <new_password>`
- **Get Credentials**: `/home/lj/memory-mcp/get_admin_creds.py`

## Notes
- Change the default password immediately after first login
- Dashboard runs on port 8901
- Database stored at `/home/lj/memory-mcp/data/control.db`