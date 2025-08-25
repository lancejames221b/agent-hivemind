# WebSocket Authentication Fix

## Problem Summary

The admin dashboard was experiencing 403 Forbidden errors when trying to establish WebSocket connections. The JavaScript client was attempting to connect to `/admin/ws?token=...` but no corresponding WebSocket endpoint existed on the server.

## Root Cause Analysis

1. **Missing WebSocket Endpoint**: The `dashboard_server.py` had no WebSocket route defined for `/admin/ws`
2. **No JWT Token Validation**: No authentication mechanism for WebSocket connections
3. **Poor Error Logging**: WebSocket authentication failures were not being logged properly
4. **Missing CORS Support**: WebSocket connections might fail due to CORS issues

## Solution Implementation

### 1. Added WebSocket Endpoint

Added a new WebSocket endpoint in `src/dashboard_server.py`:

```python
@self.app.websocket("/admin/ws")
async def admin_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for admin dashboard real-time updates"""
    # JWT token validation from query parameters
    # Proper error handling and logging
    # Real-time message handling
```

### 2. JWT Token Validation

Implemented proper JWT token validation for WebSocket connections:

- Extracts token from query parameters (`?token=...`)
- Validates JWT signature and expiration
- Logs authentication attempts (success/failure)
- Closes connection with appropriate error codes for invalid tokens

### 3. Enhanced Error Logging

Added comprehensive logging for WebSocket authentication:

- Logs all connection attempts with client IP
- Records authentication failures with specific error reasons
- Uses database access logging for audit trail
- Console logging for debugging

### 4. CORS Middleware

Added CORS middleware to support WebSocket connections:

```python
self.app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 5. Enhanced Client-Side Handling

Updated `admin/static/admin.js` with better WebSocket handling:

- Proper protocol detection (ws/wss)
- Enhanced error messages and user feedback
- Automatic reconnection with exponential backoff
- Periodic ping/pong to keep connections alive
- Token masking in logs for security

## Features Added

### Real-Time Dashboard Updates

The WebSocket connection now supports:

- **Connection Status**: Real-time connection establishment confirmation
- **Stats Updates**: Live dashboard statistics updates
- **Ping/Pong**: Connection health monitoring
- **Error Handling**: Graceful error reporting and recovery

### Message Types

| Message Type | Direction | Description |
|--------------|-----------|-------------|
| `ping` | Client → Server | Keep-alive ping |
| `pong` | Server → Client | Keep-alive response |
| `get_stats` | Client → Server | Request dashboard statistics |
| `stats_update` | Server → Client | Dashboard statistics data |
| `connection_established` | Server → Client | Connection confirmation |
| `error` | Server → Client | Error notifications |

### Authentication Flow

1. Client retrieves JWT token from localStorage
2. Client connects to `/admin/ws?token=<jwt_token>`
3. Server validates JWT token
4. If valid: Connection accepted, user logged
5. If invalid: Connection closed with error code 1008

## Testing

### Automated Testing

Use the provided test script:

```bash
python scripts/test_websocket_auth.py
```

### Manual Testing

1. Open the test page: `http://localhost:8901/admin/websocket_test.html`
2. Use stored token or enter JWT manually
3. Test connection, ping, and stats requests
4. Verify error handling with invalid tokens

### Browser Testing

1. Login to admin dashboard: `http://localhost:8901/admin/dashboard.html`
2. Open browser developer tools
3. Check console for WebSocket connection messages
4. Verify real-time updates work

## Security Considerations

### Token Security

- JWT tokens are validated on every WebSocket connection
- Expired tokens are rejected immediately
- Invalid tokens are logged for security monitoring
- Tokens are masked in client-side logs

### Connection Security

- WebSocket connections require valid authentication
- Failed authentication attempts are logged
- Rate limiting can be added if needed
- CORS policies can be restricted in production

## Error Codes

| Code | Reason | Description |
|------|--------|-------------|
| 1008 | Missing authentication token | No token provided in query |
| 1008 | Token expired | JWT token has expired |
| 1008 | Invalid token | JWT token is malformed or invalid |
| 1008 | Authentication failed | General authentication error |

## Configuration

### JWT Secret

Set the JWT secret via environment variable:

```bash
export HAIVEMIND_JWT_SECRET="your-secret-key-here"
```

### CORS Origins

In production, restrict CORS origins in `dashboard_server.py`:

```python
self.app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## Monitoring

### Access Logs

WebSocket connections are logged in the database with:

- User ID (if authenticated)
- Client IP address
- Connection timestamp
- Success/failure status
- Error reason (if failed)

### Health Monitoring

The WebSocket connection includes:

- Periodic ping/pong for connection health
- Automatic reconnection on disconnect
- Connection status indicators in UI
- Error reporting and user notifications

## Future Enhancements

1. **Rate Limiting**: Add rate limiting for WebSocket connections
2. **Message Queuing**: Queue messages for disconnected clients
3. **User Presence**: Track online users in real-time
4. **Broadcast Channels**: Support for different message channels
5. **Compression**: Enable WebSocket message compression
6. **Metrics**: Add WebSocket connection metrics and monitoring

## Troubleshooting

### Common Issues

1. **403 Forbidden**: Check if JWT token is valid and not expired
2. **Connection Refused**: Ensure dashboard server is running on port 8901
3. **Token Missing**: Verify token is stored in localStorage
4. **CORS Errors**: Check CORS middleware configuration

### Debug Steps

1. Check browser console for WebSocket errors
2. Verify JWT token format and expiration
3. Check server logs for authentication failures
4. Test with the provided test tools
5. Verify network connectivity and firewall settings

### Log Analysis

Server logs will show:

```
WebSocket authentication successful for user admin from 127.0.0.1
WebSocket connection rejected from 192.168.1.100: Token expired
```

Database access logs record all authentication attempts for audit purposes.