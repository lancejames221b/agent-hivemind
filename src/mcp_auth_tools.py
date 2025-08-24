#!/usr/bin/env python3
"""
MCP Authentication Management Tools
Provides MCP tools for managing authentication, users, API keys, and security
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from mcp_auth_manager import MCPAuthManager, ServerAuthConfig

logger = logging.getLogger(__name__)

class MCPAuthTools:
    """MCP tools for authentication and security management"""
    
    def __init__(self, config: Dict[str, Any], memory_storage=None):
        self.config = config
        self.memory_storage = memory_storage
        self.auth_manager = MCPAuthManager(config, memory_storage)
    
    async def create_user_account(self, username: str, password: str, role: str = 'user',
                                permissions: List[str] = None) -> str:
        """Create a new user account with specified role and permissions"""
        try:
            if not permissions:
                permissions = []
            
            result = await self.auth_manager.create_user(username, password, role, permissions)
            
            if result['success']:
                # Store user creation in hAIveMind
                if self.memory_storage:
                    await self.memory_storage.store_memory(
                        content=f"New user account created: {username}",
                        category='security',
                        metadata={
                            'event_type': 'user_account_created',
                            'user_id': result['user_id'],
                            'username': username,
                            'role': role,
                            'permissions': permissions,
                            'timestamp': time.time()
                        },
                        scope='hive-shared'
                    )
                
                return f"✅ **User Account Created Successfully**\n\n" \
                       f"**Username**: {username}\n" \
                       f"**User ID**: {result['user_id']}\n" \
                       f"**Role**: {role}\n" \
                       f"**Permissions**: {', '.join(permissions) if permissions else 'None'}\n\n" \
                       f"The user can now log in with their username and password."
            else:
                return f"❌ **Failed to Create User Account**\n\n" \
                       f"**Error**: {result['error']}"
        
        except Exception as e:
            logger.error(f"Error creating user account: {e}")
            return f"❌ **Error Creating User Account**: {str(e)}"
    
    async def create_api_key(self, user_id: str, key_name: str, role: str = None,
                           permissions: List[str] = None, server_access: Dict[str, List[str]] = None,
                           expires_days: int = None) -> str:
        """Create a new API key for a user with specified permissions"""
        try:
            result = await self.auth_manager.create_api_key(
                user_id=user_id,
                name=key_name,
                role=role,
                permissions=permissions,
                server_access=server_access,
                expires_days=expires_days
            )
            
            if result['success']:
                # Store API key creation in hAIveMind
                if self.memory_storage:
                    await self.memory_storage.store_memory(
                        content=f"API key created: {key_name} for user {user_id}",
                        category='security',
                        metadata={
                            'event_type': 'api_key_created',
                            'key_id': result['key_id'],
                            'key_name': key_name,
                            'user_id': user_id,
                            'role': result['role'],
                            'expires_days': expires_days,
                            'timestamp': time.time()
                        },
                        scope='hive-shared'
                    )
                
                expiry_info = ""
                if result.get('expires_at'):
                    expiry_date = datetime.fromtimestamp(result['expires_at'])
                    expiry_info = f"**Expires**: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
                
                return f"✅ **API Key Created Successfully**\n\n" \
                       f"**Key Name**: {key_name}\n" \
                       f"**Key ID**: {result['key_id']}\n" \
                       f"**Role**: {result['role']}\n" \
                       f"{expiry_info}" \
                       f"**API Key**: `{result['api_key']}`\n\n" \
                       f"⚠️ **Important**: Save this API key securely. It will not be shown again!\n\n" \
                       f"Use this key in the Authorization header: `Bearer {result['api_key']}`"
            else:
                return f"❌ **Failed to Create API Key**\n\n" \
                       f"**Error**: {result['error']}"
        
        except Exception as e:
            logger.error(f"Error creating API key: {e}")
            return f"❌ **Error Creating API Key**: {str(e)}"
    
    async def configure_server_authentication(self, server_id: str, auth_required: bool = True,
                                            allowed_roles: List[str] = None,
                                            allowed_users: List[str] = None,
                                            tool_permissions: Dict[str, List[str]] = None,
                                            rate_limits: Dict[str, int] = None,
                                            audit_level: str = "standard") -> str:
        """Configure authentication settings for a specific MCP server"""
        try:
            # Convert lists to sets for the config
            config = ServerAuthConfig(
                server_id=server_id,
                auth_required=auth_required,
                allowed_roles=set(allowed_roles) if allowed_roles else None,
                allowed_users=set(allowed_users) if allowed_users else None,
                tool_permissions=tool_permissions or {},
                rate_limits=rate_limits or {},
                audit_level=audit_level
            )
            
            success = await self.auth_manager.configure_server_auth(server_id, config)
            
            if success:
                # Store configuration in hAIveMind
                if self.memory_storage:
                    await self.memory_storage.store_memory(
                        content=f"Server authentication configured: {server_id}",
                        category='security',
                        metadata={
                            'event_type': 'server_auth_configured',
                            'server_id': server_id,
                            'auth_required': auth_required,
                            'allowed_roles': allowed_roles,
                            'audit_level': audit_level,
                            'timestamp': time.time()
                        },
                        scope='hive-shared'
                    )
                
                roles_info = f"**Allowed Roles**: {', '.join(allowed_roles)}\n" if allowed_roles else ""
                users_info = f"**Allowed Users**: {', '.join(allowed_users)}\n" if allowed_users else ""
                
                tool_perms_info = ""
                if tool_permissions:
                    tool_perms_info = "**Tool Permissions**:\n"
                    for tool, roles in tool_permissions.items():
                        tool_perms_info += f"  • {tool}: {', '.join(roles)}\n"
                
                rate_limits_info = ""
                if rate_limits:
                    rate_limits_info = "**Rate Limits**:\n"
                    for role, limit in rate_limits.items():
                        rate_limits_info += f"  • {role}: {limit} requests/minute\n"
                
                return f"✅ **Server Authentication Configured**\n\n" \
                       f"**Server ID**: {server_id}\n" \
                       f"**Authentication Required**: {'Yes' if auth_required else 'No'}\n" \
                       f"{roles_info}" \
                       f"{users_info}" \
                       f"**Audit Level**: {audit_level}\n" \
                       f"{tool_perms_info}" \
                       f"{rate_limits_info}"
            else:
                return f"❌ **Failed to Configure Server Authentication**\n\n" \
                       f"**Server ID**: {server_id}"
        
        except Exception as e:
            logger.error(f"Error configuring server authentication: {e}")
            return f"❌ **Error Configuring Server Authentication**: {str(e)}"
    
    async def list_users(self, active_only: bool = True) -> str:
        """List all user accounts with their roles and status"""
        try:
            with self.auth_manager._get_db_connection() as conn:
                query = '''
                    SELECT user_id, username, role, permissions, created_at, last_login, active
                    FROM users
                '''
                if active_only:
                    query += ' WHERE active = 1'
                query += ' ORDER BY created_at DESC'
                
                cursor = conn.execute(query)
                users = cursor.fetchall()
            
            if not users:
                return "📋 **No Users Found**\n\nNo user accounts are currently registered."
            
            result = f"👥 **User Accounts** ({len(users)} total)\n\n"
            
            for user in users:
                user_id, username, role, permissions_json, created_at, last_login, active = user
                
                permissions = json.loads(permissions_json) if permissions_json else []
                created_date = datetime.fromtimestamp(created_at).strftime('%Y-%m-%d')
                
                last_login_str = "Never"
                if last_login:
                    last_login_str = datetime.fromtimestamp(last_login).strftime('%Y-%m-%d %H:%M')
                
                status_emoji = "✅" if active else "❌"
                
                result += f"{status_emoji} **{username}**\n" \
                         f"   ID: `{user_id}`\n" \
                         f"   Role: {role}\n" \
                         f"   Permissions: {', '.join(permissions) if permissions else 'None'}\n" \
                         f"   Created: {created_date}\n" \
                         f"   Last Login: {last_login_str}\n\n"
            
            return result
        
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return f"❌ **Error Listing Users**: {str(e)}"
    
    async def list_api_keys(self, user_id: str = None, active_only: bool = True) -> str:
        """List API keys, optionally filtered by user"""
        try:
            with self.auth_manager._get_db_connection() as conn:
                query = '''
                    SELECT ak.key_id, ak.user_id, ak.name, ak.role, ak.created_at, 
                           ak.expires_at, ak.last_used, ak.active, u.username
                    FROM api_keys ak
                    JOIN users u ON ak.user_id = u.user_id
                '''
                params = []
                
                conditions = []
                if user_id:
                    conditions.append('ak.user_id = ?')
                    params.append(user_id)
                
                if active_only:
                    conditions.append('ak.active = 1')
                
                if conditions:
                    query += ' WHERE ' + ' AND '.join(conditions)
                
                query += ' ORDER BY ak.created_at DESC'
                
                cursor = conn.execute(query, params)
                keys = cursor.fetchall()
            
            if not keys:
                filter_info = f" for user {user_id}" if user_id else ""
                return f"🔑 **No API Keys Found**\n\nNo API keys are currently registered{filter_info}."
            
            result = f"🔑 **API Keys** ({len(keys)} total)\n\n"
            
            for key in keys:
                (key_id, user_id, name, role, created_at, expires_at, 
                 last_used, active, username) = key
                
                created_date = datetime.fromtimestamp(created_at).strftime('%Y-%m-%d')
                
                expires_str = "Never"
                if expires_at:
                    expires_date = datetime.fromtimestamp(expires_at)
                    expires_str = expires_date.strftime('%Y-%m-%d')
                    if expires_date < datetime.now():
                        expires_str += " (EXPIRED)"
                
                last_used_str = "Never"
                if last_used:
                    last_used_str = datetime.fromtimestamp(last_used).strftime('%Y-%m-%d %H:%M')
                
                status_emoji = "✅" if active else "❌"
                
                result += f"{status_emoji} **{name}**\n" \
                         f"   Key ID: `{key_id}`\n" \
                         f"   User: {username} ({user_id})\n" \
                         f"   Role: {role}\n" \
                         f"   Created: {created_date}\n" \
                         f"   Expires: {expires_str}\n" \
                         f"   Last Used: {last_used_str}\n\n"
            
            return result
        
        except Exception as e:
            logger.error(f"Error listing API keys: {e}")
            return f"❌ **Error Listing API Keys**: {str(e)}"
    
    async def get_security_analytics(self, days: int = 7) -> str:
        """Get security analytics and insights for the specified period"""
        try:
            analytics = await self.auth_manager.get_security_analytics(days)
            
            if 'error' in analytics:
                return f"❌ **Error Getting Security Analytics**: {analytics['error']}"
            
            # Format the analytics report
            result = f"📊 **Security Analytics Report** ({days} days)\n\n"
            
            result += f"**Authentication Summary**:\n" \
                     f"• Failed Login Attempts: {analytics['failed_authentications']}\n" \
                     f"• High-Risk Events: {analytics['high_risk_events']}\n" \
                     f"• Rate Limit Violations: {analytics['rate_limit_violations']}\n\n"
            
            if analytics['top_users']:
                result += "**Most Active Users**:\n"
                for user in analytics['top_users'][:5]:
                    result += f"• {user['user_id']}: {user['event_count']} events\n"
                result += "\n"
            
            if analytics['top_tools']:
                result += "**Most Used Tools**:\n"
                for tool in analytics['top_tools'][:5]:
                    result += f"• {tool['tool_name']}: {tool['execution_count']} executions\n"
                result += "\n"
            
            # Security recommendations
            recommendations = []
            if analytics['failed_authentications'] > 10:
                recommendations.append("High number of failed authentications detected - review access logs")
            if analytics['high_risk_events'] > 0:
                recommendations.append("High-risk security events detected - immediate review recommended")
            if analytics['rate_limit_violations'] > 5:
                recommendations.append("Multiple rate limit violations - consider adjusting limits or investigating abuse")
            
            if recommendations:
                result += "**Security Recommendations**:\n"
                for i, rec in enumerate(recommendations, 1):
                    result += f"{i}. {rec}\n"
                result += "\n"
            
            result += f"**Report Generated**: {analytics['generated_at']}"
            
            return result
        
        except Exception as e:
            logger.error(f"Error getting security analytics: {e}")
            return f"❌ **Error Getting Security Analytics**: {str(e)}"
    
    async def revoke_api_key(self, key_id: str) -> str:
        """Revoke an API key"""
        try:
            with self.auth_manager._get_db_connection() as conn:
                # Get key info before revoking
                cursor = conn.execute('''
                    SELECT ak.name, ak.user_id, u.username
                    FROM api_keys ak
                    JOIN users u ON ak.user_id = u.user_id
                    WHERE ak.key_id = ?
                ''', (key_id,))
                
                key_info = cursor.fetchone()
                if not key_info:
                    return f"❌ **API Key Not Found**\n\nKey ID: {key_id}"
                
                key_name, user_id, username = key_info
                
                # Revoke the key
                conn.execute('UPDATE api_keys SET active = 0 WHERE key_id = ?', (key_id,))
                
                # Store revocation in hAIveMind
                if self.memory_storage:
                    await self.memory_storage.store_memory(
                        content=f"API key revoked: {key_name}",
                        category='security',
                        metadata={
                            'event_type': 'api_key_revoked',
                            'key_id': key_id,
                            'key_name': key_name,
                            'user_id': user_id,
                            'timestamp': time.time()
                        },
                        scope='hive-shared'
                    )
                
                return f"✅ **API Key Revoked Successfully**\n\n" \
                       f"**Key Name**: {key_name}\n" \
                       f"**Key ID**: {key_id}\n" \
                       f"**User**: {username}\n\n" \
                       f"This API key is now inactive and cannot be used for authentication."
        
        except Exception as e:
            logger.error(f"Error revoking API key: {e}")
            return f"❌ **Error Revoking API Key**: {str(e)}"
    
    async def audit_security_events(self, event_type: str = None, user_id: str = None,
                                  hours: int = 24, risk_level: str = None) -> str:
        """Get detailed audit log of security events"""
        try:
            cutoff_time = int(time.time()) - (hours * 3600)
            
            with self.auth_manager._get_db_connection() as conn:
                query = '''
                    SELECT timestamp, event_type, user_id, server_id, tool_name, 
                           client_ip, success, details, risk_level
                    FROM audit_events
                    WHERE timestamp > ?
                '''
                params = [cutoff_time]
                
                if event_type:
                    query += ' AND event_type = ?'
                    params.append(event_type)
                
                if user_id:
                    query += ' AND user_id = ?'
                    params.append(user_id)
                
                if risk_level:
                    query += ' AND risk_level = ?'
                    params.append(risk_level)
                
                query += ' ORDER BY timestamp DESC LIMIT 100'
                
                cursor = conn.execute(query, params)
                events = cursor.fetchall()
            
            if not events:
                return f"📋 **No Security Events Found**\n\n" \
                       f"No events matching the criteria in the last {hours} hours."
            
            result = f"🔍 **Security Audit Log** ({len(events)} events, last {hours}h)\n\n"
            
            for event in events:
                (timestamp, event_type, user_id, server_id, tool_name, 
                 client_ip, success, details_json, risk_level) = event
                
                event_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                success_emoji = "✅" if success else "❌"
                
                risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk_level, "⚪")
                
                details = json.loads(details_json) if details_json else {}
                
                result += f"{success_emoji} {risk_emoji} **{event_type}**\n" \
                         f"   Time: {event_time}\n" \
                         f"   User: {user_id}\n" \
                         f"   IP: {client_ip}\n"
                
                if server_id:
                    result += f"   Server: {server_id}\n"
                if tool_name:
                    result += f"   Tool: {tool_name}\n"
                
                if details:
                    key_details = []
                    for key, value in details.items():
                        if key not in ['timestamp', 'user_id']:  # Skip redundant info
                            key_details.append(f"{key}: {value}")
                    if key_details:
                        result += f"   Details: {', '.join(key_details[:3])}\n"  # Limit details
                
                result += "\n"
            
            return result
        
        except Exception as e:
            logger.error(f"Error getting audit events: {e}")
            return f"❌ **Error Getting Audit Events**: {str(e)}"
    
    def _get_db_connection(self):
        """Get database connection - helper method"""
        return self.auth_manager._get_db_connection()

# Helper method for auth manager
def _get_db_connection(self):
    """Get database connection"""
    import sqlite3
    return sqlite3.connect(self.db_path)

# Monkey patch the method
MCPAuthManager._get_db_connection = _get_db_connection