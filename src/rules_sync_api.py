#!/usr/bin/env python3
"""
hAIveMind Rules Sync API - REST endpoints for rules synchronization
Provides HTTP API for rules sync operations, conflict resolution, and network governance

Author: Lance James, Unit 221B Inc
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from .rules_sync_service import RulesSyncService, RuleSyncOperation, RuleSyncPriority

logger = logging.getLogger(__name__)

# Pydantic models for API
class RuleSyncRequest(BaseModel):
    rule_id: str
    operation: str
    priority: str = "normal"
    target_machines: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class BulkSyncRequest(BaseModel):
    rule_ids: Optional[List[str]] = None
    target_machines: Optional[List[str]] = None
    priority: str = "background"

class EmergencyUpdateRequest(BaseModel):
    rule_id: str
    rule_data: Dict[str, Any]
    reason: str
    target_machines: Optional[List[str]] = None

class ConflictResolutionRequest(BaseModel):
    conflict_id: str
    resolution: str  # use_local, use_remote, merge
    resolved_by: str

class RulesSyncAPI:
    """FastAPI router for rules synchronization endpoints"""
    
    def __init__(self, sync_service: RulesSyncService):
        self.sync_service = sync_service
        self.router = APIRouter(prefix="/api/rules", tags=["rules-sync"])
        self.security = HTTPBearer()
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.router.post("/sync")
        async def sync_rule(request: RuleSyncRequest, _: str = Depends(self._verify_token)):
            """Sync a specific rule to the network"""
            try:
                operation = RuleSyncOperation(request.operation)
                priority = RuleSyncPriority[request.priority.upper()]
                
                sync_id = await self.sync_service.sync_rule_to_network(
                    rule_id=request.rule_id,
                    operation=operation,
                    priority=priority,
                    target_machines=request.target_machines,
                    metadata=request.metadata
                )
                
                return {
                    "success": True,
                    "sync_id": sync_id,
                    "message": f"Rule sync initiated for {request.rule_id}"
                }
                
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid request: {e}")
            except Exception as e:
                logger.error(f"Rule sync error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/bulk-sync")
        async def bulk_sync_rules(request: BulkSyncRequest, _: str = Depends(self._verify_token)):
            """Perform bulk synchronization of rules"""
            try:
                priority = RuleSyncPriority[request.priority.upper()]
                
                sync_id = await self.sync_service.bulk_sync_rules(
                    rule_ids=request.rule_ids,
                    target_machines=request.target_machines,
                    priority=priority
                )
                
                return {
                    "success": True,
                    "sync_id": sync_id,
                    "message": f"Bulk sync initiated for {len(request.rule_ids) if request.rule_ids else 'all'} rules"
                }
                
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid request: {e}")
            except Exception as e:
                logger.error(f"Bulk sync error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/emergency-update")
        async def emergency_rule_update(request: EmergencyUpdateRequest, _: str = Depends(self._verify_token)):
            """Emergency rule update with immediate network distribution"""
            try:
                sync_id = await self.sync_service.emergency_rule_update(
                    rule_id=request.rule_id,
                    rule_data=request.rule_data,
                    reason=request.reason,
                    target_machines=request.target_machines
                )
                
                return {
                    "success": True,
                    "sync_id": sync_id,
                    "message": f"Emergency update initiated for rule {request.rule_id}",
                    "reason": request.reason
                }
                
            except Exception as e:
                logger.error(f"Emergency update error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/emergency-sync")
        async def handle_emergency_sync(sync_data: Dict[str, Any]):
            """Handle incoming emergency sync from another machine"""
            try:
                # This endpoint is called directly by other machines for emergency updates
                sync_message_data = sync_data.get('sync_message', {})
                source_machine = sync_data.get('source')
                
                # Process the emergency sync message
                # This would typically be handled by the Redis listener, but for direct HTTP calls
                # we need to handle it here
                
                logger.warning(f"Received direct emergency sync from {source_machine}")
                
                return {
                    "success": True,
                    "message": "Emergency sync received and will be processed"
                }
                
            except Exception as e:
                logger.error(f"Emergency sync handling error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/sync-status")
        async def get_sync_status(sync_id: Optional[str] = None, _: str = Depends(self._verify_token)):
            """Get sync operation status"""
            try:
                status = self.sync_service.get_sync_status(sync_id)
                return status
                
            except Exception as e:
                logger.error(f"Sync status error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/conflicts")
        async def get_conflicts(conflict_id: Optional[str] = None, _: str = Depends(self._verify_token)):
            """Get rule synchronization conflicts"""
            try:
                conflicts = self.sync_service.get_conflict_status(conflict_id)
                return conflicts
                
            except Exception as e:
                logger.error(f"Conflicts retrieval error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/resolve-conflict")
        async def resolve_conflict(request: ConflictResolutionRequest, _: str = Depends(self._verify_token)):
            """Manually resolve a rule synchronization conflict"""
            try:
                success = await self.sync_service.resolve_conflict_manually(
                    conflict_id=request.conflict_id,
                    resolution=request.resolution,
                    resolved_by=request.resolved_by
                )
                
                if success:
                    return {
                        "success": True,
                        "message": f"Conflict {request.conflict_id} resolved with strategy: {request.resolution}"
                    }
                else:
                    raise HTTPException(status_code=404, detail=f"Conflict {request.conflict_id} not found")
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Conflict resolution error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/network-status")
        async def get_network_status(_: str = Depends(self._verify_token)):
            """Get network-wide rules synchronization status"""
            try:
                status = {
                    "machine_id": self.sync_service.machine_id,
                    "known_machines": list(self.sync_service.known_machines),
                    "active_syncs": len(self.sync_service.active_syncs),
                    "pending_conflicts": len(self.sync_service.pending_conflicts),
                    "sync_metrics": self.sync_service.sync_metrics,
                    "machine_authorities": self.sync_service.machine_authorities
                }
                
                return status
                
            except Exception as e:
                logger.error(f"Network status error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/sync-health")
        async def get_sync_health(_: str = Depends(self._verify_token)):
            """Get synchronization health metrics"""
            try:
                metrics = self.sync_service.sync_metrics
                
                # Calculate health score
                total_syncs = metrics.get('total_syncs', 0)
                successful_syncs = metrics.get('successful_syncs', 0)
                failed_syncs = metrics.get('failed_syncs', 0)
                
                if total_syncs > 0:
                    success_rate = successful_syncs / total_syncs
                    failure_rate = failed_syncs / total_syncs
                else:
                    success_rate = 1.0
                    failure_rate = 0.0
                
                # Determine health status
                if success_rate >= 0.95:
                    health_status = "excellent"
                elif success_rate >= 0.85:
                    health_status = "good"
                elif success_rate >= 0.70:
                    health_status = "fair"
                else:
                    health_status = "poor"
                
                return {
                    "health_status": health_status,
                    "success_rate": round(success_rate, 3),
                    "failure_rate": round(failure_rate, 3),
                    "metrics": metrics,
                    "active_conflicts": len(self.sync_service.pending_conflicts),
                    "avg_sync_time": round(metrics.get('avg_sync_time', 0), 2)
                }
                
            except Exception as e:
                logger.error(f"Sync health error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/force-sync")
        async def force_network_sync(_: str = Depends(self._verify_token)):
            """Force a complete network synchronization"""
            try:
                sync_id = await self.sync_service.bulk_sync_rules(
                    priority=RuleSyncPriority.HIGH
                )
                
                return {
                    "success": True,
                    "sync_id": sync_id,
                    "message": "Force network sync initiated"
                }
                
            except Exception as e:
                logger.error(f"Force sync error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/sync-history")
        async def get_sync_history(limit: int = 50, _: str = Depends(self._verify_token)):
            """Get synchronization history"""
            try:
                history = self.sync_service.sync_history[-limit:] if limit > 0 else self.sync_service.sync_history
                
                return {
                    "history": [
                        {
                            "sync_id": s.sync_id,
                            "machine_id": s.machine_id,
                            "status": s.status,
                            "started_at": s.started_at.isoformat(),
                            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                            "rules_processed": s.rules_processed,
                            "conflicts_detected": s.conflicts_detected,
                            "error_message": s.error_message
                        }
                        for s in history
                    ],
                    "total_history_entries": len(self.sync_service.sync_history)
                }
                
            except Exception as e:
                logger.error(f"Sync history error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/set-machine-authority")
        async def set_machine_authority(machine_id: str, rule_types: List[str], _: str = Depends(self._verify_token)):
            """Set machine authority for specific rule types"""
            try:
                # Validate rule types
                valid_rule_types = [rt.value for rt in RuleType]
                invalid_types = [rt for rt in rule_types if rt not in valid_rule_types]
                
                if invalid_types:
                    raise HTTPException(status_code=400, detail=f"Invalid rule types: {invalid_types}")
                
                self.sync_service.machine_authorities[machine_id] = rule_types
                
                return {
                    "success": True,
                    "message": f"Machine {machine_id} set as authority for rule types: {rule_types}"
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Set machine authority error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.delete("/clear-conflicts")
        async def clear_resolved_conflicts(_: str = Depends(self._verify_token)):
            """Clear all resolved conflicts from memory"""
            try:
                resolved_conflicts = [cid for cid, conflict in self.sync_service.pending_conflicts.items() if conflict.resolved]
                
                for conflict_id in resolved_conflicts:
                    del self.sync_service.pending_conflicts[conflict_id]
                
                return {
                    "success": True,
                    "message": f"Cleared {len(resolved_conflicts)} resolved conflicts"
                }
                
            except Exception as e:
                logger.error(f"Clear conflicts error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def _verify_token(self, credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())):
        """Simple token verification (expand for production)"""
        # In production, implement proper JWT verification
        # For now, accept any token that matches the configured admin token
        expected_token = "your-api-token"  # This should come from config
        
        if credentials.credentials != expected_token:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        
        return credentials.credentials

def create_rules_sync_router(sync_service: RulesSyncService) -> APIRouter:
    """Create and return the rules sync API router"""
    api = RulesSyncAPI(sync_service)
    return api.router