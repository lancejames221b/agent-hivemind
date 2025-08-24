"""
Vault Integration with hAIveMind Memory System
Main integration script for the Enterprise Vault Security System.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
import json
import redis
from typing import Dict, Any

from .vault.enterprise_vault_orchestrator import EnterpriseVaultOrchestrator
from .vault_mcp_tools import VaultMCPTools
from .memory_server import MemoryMCPServer


async def initialize_vault_system(config: Dict[str, Any], redis_client: redis.Redis,
                                memory_server: MemoryMCPServer) -> tuple[EnterpriseVaultOrchestrator, VaultMCPTools]:
    """Initialize the complete enterprise vault system"""
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Initializing Enterprise Vault Security System...")
        
        # Create vault orchestrator
        vault_orchestrator = EnterpriseVaultOrchestrator(config, redis_client, memory_server)
        
        # Initialize all vault components
        if not await vault_orchestrator.initialize_enterprise_vault():
            raise Exception("Failed to initialize enterprise vault")
        
        # Create MCP tools interface
        vault_tools = VaultMCPTools(vault_orchestrator, memory_server)
        
        # Store initialization success in hAIveMind
        await memory_server.store_memory(
            content=json.dumps({
                'system': 'enterprise_vault',
                'status': 'initialized',
                'timestamp': '2024-01-01T00:00:00Z',
                'components': [
                    'advanced_security_framework',
                    'shamir_secret_sharing', 
                    'multisig_approval',
                    'credential_escrow',
                    'ml_threat_detection',
                    'siem_integration',
                    'haivemind_integration'
                ],
                'features': [
                    'hsm_integration',
                    'enterprise_authentication',
                    'compliance_reporting',
                    'collaborative_threat_response',
                    'emergency_procedures',
                    'audit_trails',
                    'real_time_monitoring'
                ]
            }),
            category='infrastructure',
            subcategory='system_initialization',
            tags=['vault', 'enterprise_security', 'haivemind_integration'],
            importance=0.95
        )
        
        logger.info("Enterprise Vault Security System initialized successfully")
        return vault_orchestrator, vault_tools
        
    except Exception as e:
        logger.error(f"Failed to initialize vault system: {str(e)}")
        raise


def add_vault_tools_to_mcp_server(mcp_server, vault_tools: VaultMCPTools):
    """Add vault tools to the MCP server"""
    
    # Vault status and monitoring tools
    mcp_server.add_tool("get_vault_status", vault_tools.get_vault_status)
    mcp_server.add_tool("get_threat_summary", vault_tools.get_threat_summary)
    mcp_server.add_tool("get_siem_status", vault_tools.get_siem_status) 
    mcp_server.add_tool("get_haivemind_status", vault_tools.get_haivemind_status)
    mcp_server.add_tool("get_compliance_report", vault_tools.get_compliance_report)
    
    # Multi-signature approval tools
    mcp_server.add_tool("create_approval_request", vault_tools.create_approval_request)
    mcp_server.add_tool("approve_request", vault_tools.approve_request)
    mcp_server.add_tool("get_pending_approvals", vault_tools.get_pending_approvals)
    
    # Credential escrow and recovery tools  
    mcp_server.add_tool("escrow_credential", vault_tools.escrow_credential)
    mcp_server.add_tool("initiate_credential_recovery", vault_tools.initiate_credential_recovery)
    
    # Shamir's secret sharing tools
    mcp_server.add_tool("create_secret_shares", vault_tools.create_secret_shares)
    
    # Security framework tools
    mcp_server.add_tool("generate_hsm_key", vault_tools.generate_hsm_key)
    mcp_server.add_tool("create_security_session", vault_tools.create_security_session)
    
    # Emergency response tools
    mcp_server.add_tool("emergency_credential_revocation", vault_tools.emergency_credential_revocation)
    mcp_server.add_tool("initiate_collaborative_response", vault_tools.initiate_collaborative_response)


# Example usage and testing
async def main():
    """Example usage of the vault system"""
    
    # Load configuration
    with open('config/config.json', 'r') as f:
        base_config = json.load(f)
    
    # Load enterprise vault configuration
    with open('config/enterprise_vault_config.json', 'r') as f:
        vault_config = json.load(f)
    
    # Merge configurations
    config = {**base_config, **vault_config}
    
    # Initialize Redis
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    # Initialize memory server (would be passed from main application)
    memory_server = None  # Placeholder
    
    if memory_server:
        # Initialize vault system
        vault_orchestrator, vault_tools = await initialize_vault_system(
            config, redis_client, memory_server
        )
        
        # Example operations
        print("=== Enterprise Vault Security System Demo ===")
        
        # Get system status
        status = await vault_tools.get_vault_status()
        print(f"Vault Status: {status}")
        
        # Create approval request
        approval_result = await vault_tools.create_approval_request(
            operation_type="credential_deletion",
            operation_details={'credential_id': 'test_cred_001', 'reason': 'policy_violation'},
            requesting_user="admin@company.com"
        )
        print(f"Approval Request: {approval_result}")
        
        # Get threat summary
        threats = await vault_tools.get_threat_summary()
        print(f"Threat Summary: {threats}")
        
        # Check hAIveMind status
        haivemind_status = await vault_tools.get_haivemind_status()
        print(f"hAIveMind Status: {haivemind_status}")
        
        print("=== Demo Complete ===")
        
        # Shutdown gracefully
        await vault_orchestrator.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())