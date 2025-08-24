#!/usr/bin/env python3
"""
Playbook Version Control System for ClaudeOps hAIveMind

This module implements version control for iterative playbook improvement:
- Track playbook versions and changes over time
- Manage playbook evolution based on execution feedback
- Implement rollback capabilities for problematic versions
- Track performance metrics across versions
- Support branching for experimental playbook variations
- Integrate with hAIveMind for collaborative playbook development
"""

import asyncio
import json
import logging
import hashlib
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class ChangeType(Enum):
    CREATED = "created"
    MODIFIED = "modified"
    IMPROVED = "improved"
    BUGFIX = "bugfix"
    ROLLBACK = "rollback"
    MERGED = "merged"
    DEPRECATED = "deprecated"

@dataclass
class PlaybookVersion:
    """Represents a version of a playbook"""
    version_id: str
    playbook_id: str
    version_number: str  # e.g., "1.0.0", "1.1.0", "2.0.0"
    content: Dict[str, Any]
    content_hash: str
    change_type: ChangeType
    change_description: str
    author: str
    created_at: datetime
    parent_version: Optional[str] = None
    branch: str = "main"
    tags: List[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class PlaybookExecution:
    """Represents an execution of a playbook version"""
    execution_id: str
    version_id: str
    playbook_id: str
    executed_by: str
    executed_at: datetime
    success: bool
    duration_seconds: float
    error_message: Optional[str] = None
    context: Dict[str, Any] = None
    feedback_score: Optional[float] = None  # 0.0 to 1.0
    improvements_suggested: List[str] = None

@dataclass
class VersionMetrics:
    """Performance metrics for a playbook version"""
    version_id: str
    total_executions: int
    successful_executions: int
    success_rate: float
    average_duration: float
    average_feedback_score: float
    last_executed: datetime
    issues_reported: int
    improvements_applied: int

class PlaybookVersionControl:
    """Version control system for playbooks"""
    
    def __init__(self, memory_storage, config: Dict[str, Any]):
        self.memory_storage = memory_storage
        self.config = config
        
        # Version control settings
        self.auto_version_on_change = config.get('auto_version_on_change', True)
        self.max_versions_per_playbook = config.get('max_versions_per_playbook', 50)
        self.retention_days = config.get('version_retention_days', 365)
        
        # Performance tracking
        self.track_execution_metrics = config.get('track_execution_metrics', True)
        self.auto_improve_threshold = config.get('auto_improve_threshold', 0.7)
        
        # Cache for frequent operations
        self.version_cache = {}
        self.metrics_cache = {}
    
    async def create_playbook_version(self, 
                                    playbook_id: str,
                                    content: Dict[str, Any],
                                    change_type: ChangeType,
                                    change_description: str,
                                    author: str,
                                    parent_version: Optional[str] = None,
                                    branch: str = "main",
                                    tags: Optional[List[str]] = None) -> PlaybookVersion:
        """
        Create a new version of a playbook
        
        Args:
            playbook_id: Unique identifier for the playbook
            content: Playbook content/specification
            change_type: Type of change being made
            change_description: Description of the changes
            author: Author of the changes
            parent_version: Parent version ID (for tracking lineage)
            branch: Branch name (default: "main")
            tags: Optional tags for this version
            
        Returns:
            New PlaybookVersion object
        """
        try:
            # Generate content hash for deduplication
            content_str = json.dumps(content, sort_keys=True)
            content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:16]
            
            # Check if this exact content already exists
            existing_version = await self._find_version_by_hash(playbook_id, content_hash)
            if existing_version:
                logger.info(f"📋 Identical content found for playbook {playbook_id}, returning existing version")
                return existing_version
            
            # Get current version number and increment
            current_versions = await self._get_playbook_versions(playbook_id, branch)
            version_number = self._calculate_next_version(current_versions, change_type)
            
            # Create new version
            version = PlaybookVersion(
                version_id=f"{playbook_id}_v{version_number}_{int(time.time())}",
                playbook_id=playbook_id,
                version_number=version_number,
                content=content,
                content_hash=content_hash,
                change_type=change_type,
                change_description=change_description,
                author=author,
                created_at=datetime.now(),
                parent_version=parent_version,
                branch=branch,
                tags=tags or [],
                metadata={
                    "created_by_system": self.memory_storage.machine_id,
                    "agent_id": self.memory_storage.agent_id
                }
            )
            
            # Store version in memory system
            await self._store_version(version)
            
            # Update cache
            self.version_cache[version.version_id] = version
            
            # Clean up old versions if necessary
            await self._cleanup_old_versions(playbook_id, branch)
            
            logger.info(f"📋 Created playbook version {version_number} for {playbook_id}")
            return version
            
        except Exception as e:
            logger.error(f"Failed to create playbook version: {e}")
            raise
    
    async def _find_version_by_hash(self, playbook_id: str, content_hash: str) -> Optional[PlaybookVersion]:
        """Find existing version with the same content hash"""
        try:
            search_results = await self.memory_storage.search_memories(
                query=f"playbook_id:{playbook_id} content_hash:{content_hash}",
                category="playbook_versions",
                limit=1
            )
            
            if search_results.get('memories'):
                version_data = json.loads(search_results['memories'][0].get('content', '{}'))
                return PlaybookVersion(**version_data)
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to find version by hash: {e}")
            return None
    
    async def _get_playbook_versions(self, playbook_id: str, branch: str = "main") -> List[PlaybookVersion]:
        """Get all versions of a playbook on a specific branch"""
        try:
            search_results = await self.memory_storage.search_memories(
                query=f"playbook_id:{playbook_id} branch:{branch}",
                category="playbook_versions",
                limit=100
            )
            
            versions = []
            for memory in search_results.get('memories', []):
                try:
                    version_data = json.loads(memory.get('content', '{}'))
                    version = PlaybookVersion(**version_data)
                    versions.append(version)
                except Exception as e:
                    logger.warning(f"Failed to parse version data: {e}")
            
            # Sort by version number
            versions.sort(key=lambda v: self._version_sort_key(v.version_number), reverse=True)
            return versions
            
        except Exception as e:
            logger.error(f"Failed to get playbook versions: {e}")
            return []
    
    def _calculate_next_version(self, existing_versions: List[PlaybookVersion], change_type: ChangeType) -> str:
        """Calculate the next version number based on existing versions and change type"""
        if not existing_versions:
            return "1.0.0"
        
        # Get the latest version
        latest_version = existing_versions[0].version_number
        major, minor, patch = self._parse_version(latest_version)
        
        # Increment based on change type
        if change_type in [ChangeType.CREATED, ChangeType.DEPRECATED]:
            major += 1
            minor = 0
            patch = 0
        elif change_type in [ChangeType.IMPROVED, ChangeType.MERGED]:
            minor += 1
            patch = 0
        else:  # MODIFIED, BUGFIX, ROLLBACK
            patch += 1
        
        return f"{major}.{minor}.{patch}"
    
    def _parse_version(self, version_str: str) -> Tuple[int, int, int]:
        """Parse version string into major, minor, patch components"""
        try:
            parts = version_str.split('.')
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            return major, minor, patch
        except:
            return 1, 0, 0
    
    def _version_sort_key(self, version_str: str) -> Tuple[int, int, int]:
        """Generate sort key for version strings"""
        return self._parse_version(version_str)
    
    async def _store_version(self, version: PlaybookVersion):
        """Store version in memory system"""
        try:
            await self.memory_storage.store_memory(
                content=json.dumps(asdict(version), default=str),
                category="playbook_versions",
                metadata={
                    "version_id": version.version_id,
                    "playbook_id": version.playbook_id,
                    "version_number": version.version_number,
                    "branch": version.branch,
                    "change_type": version.change_type.value,
                    "author": version.author,
                    "content_hash": version.content_hash
                },
                tags=["version_control", "playbook", version.change_type.value] + (version.tags or [])
            )
        except Exception as e:
            logger.error(f"Failed to store version: {e}")
            raise
    
    async def _cleanup_old_versions(self, playbook_id: str, branch: str):
        """Clean up old versions if we exceed the maximum"""
        try:
            versions = await self._get_playbook_versions(playbook_id, branch)
            
            if len(versions) > self.max_versions_per_playbook:
                # Keep the most recent versions and delete the oldest
                versions_to_delete = versions[self.max_versions_per_playbook:]
                
                for version in versions_to_delete:
                    # Don't delete if it's been executed recently
                    recent_executions = await self._get_recent_executions(version.version_id, hours=24)
                    if not recent_executions:
                        await self._delete_version(version.version_id)
                        logger.info(f"🗑️ Cleaned up old version {version.version_number} of {playbook_id}")
            
        except Exception as e:
            logger.warning(f"Failed to cleanup old versions: {e}")
    
    async def _delete_version(self, version_id: str):
        """Delete a specific version"""
        try:
            search_results = await self.memory_storage.search_memories(
                query=f"version_id:{version_id}",
                category="playbook_versions",
                limit=1
            )
            
            if search_results.get('memories'):
                memory_id = search_results['memories'][0].get('id')
                await self.memory_storage.delete_memory(memory_id, hard_delete=True)
                
                # Remove from cache
                if version_id in self.version_cache:
                    del self.version_cache[version_id]
            
        except Exception as e:
            logger.error(f"Failed to delete version {version_id}: {e}")
    
    async def get_version(self, version_id: str) -> Optional[PlaybookVersion]:
        """Get a specific version by ID"""
        try:
            # Check cache first
            if version_id in self.version_cache:
                return self.version_cache[version_id]
            
            search_results = await self.memory_storage.search_memories(
                query=f"version_id:{version_id}",
                category="playbook_versions",
                limit=1
            )
            
            if search_results.get('memories'):
                version_data = json.loads(search_results['memories'][0].get('content', '{}'))
                version = PlaybookVersion(**version_data)
                self.version_cache[version_id] = version
                return version
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get version {version_id}: {e}")
            return None
    
    async def get_latest_version(self, playbook_id: str, branch: str = "main") -> Optional[PlaybookVersion]:
        """Get the latest version of a playbook"""
        try:
            versions = await self._get_playbook_versions(playbook_id, branch)
            return versions[0] if versions else None
        except Exception as e:
            logger.error(f"Failed to get latest version: {e}")
            return None
    
    async def record_execution(self, 
                             version_id: str,
                             executed_by: str,
                             success: bool,
                             duration_seconds: float,
                             error_message: Optional[str] = None,
                             context: Optional[Dict[str, Any]] = None,
                             feedback_score: Optional[float] = None,
                             improvements_suggested: Optional[List[str]] = None) -> PlaybookExecution:
        """
        Record an execution of a playbook version
        
        Args:
            version_id: Version that was executed
            executed_by: Who executed the playbook
            success: Whether execution was successful
            duration_seconds: How long execution took
            error_message: Error message if failed
            context: Execution context
            feedback_score: User feedback score (0.0 to 1.0)
            improvements_suggested: List of suggested improvements
            
        Returns:
            PlaybookExecution record
        """
        try:
            version = await self.get_version(version_id)
            if not version:
                raise ValueError(f"Version {version_id} not found")
            
            execution = PlaybookExecution(
                execution_id=f"exec_{version_id}_{int(time.time())}",
                version_id=version_id,
                playbook_id=version.playbook_id,
                executed_by=executed_by,
                executed_at=datetime.now(),
                success=success,
                duration_seconds=duration_seconds,
                error_message=error_message,
                context=context or {},
                feedback_score=feedback_score,
                improvements_suggested=improvements_suggested or []
            )
            
            # Store execution record
            await self._store_execution(execution)
            
            # Update metrics
            await self._update_version_metrics(version_id)
            
            # Check if auto-improvement is needed
            if self.track_execution_metrics:
                await self._check_auto_improvement(version_id)
            
            logger.info(f"📊 Recorded execution of {version_id}: {'success' if success else 'failure'}")
            return execution
            
        except Exception as e:
            logger.error(f"Failed to record execution: {e}")
            raise
    
    async def _store_execution(self, execution: PlaybookExecution):
        """Store execution record in memory system"""
        try:
            await self.memory_storage.store_memory(
                content=json.dumps(asdict(execution), default=str),
                category="playbook_executions",
                metadata={
                    "execution_id": execution.execution_id,
                    "version_id": execution.version_id,
                    "playbook_id": execution.playbook_id,
                    "executed_by": execution.executed_by,
                    "success": execution.success,
                    "duration_seconds": execution.duration_seconds,
                    "feedback_score": execution.feedback_score
                },
                tags=["execution", "playbook", "success" if execution.success else "failure"]
            )
        except Exception as e:
            logger.error(f"Failed to store execution: {e}")
            raise
    
    async def _update_version_metrics(self, version_id: str):
        """Update performance metrics for a version"""
        try:
            executions = await self._get_version_executions(version_id)
            
            if not executions:
                return
            
            total_executions = len(executions)
            successful_executions = sum(1 for e in executions if e.success)
            success_rate = successful_executions / total_executions
            
            durations = [e.duration_seconds for e in executions if e.duration_seconds > 0]
            average_duration = sum(durations) / len(durations) if durations else 0
            
            feedback_scores = [e.feedback_score for e in executions if e.feedback_score is not None]
            average_feedback_score = sum(feedback_scores) / len(feedback_scores) if feedback_scores else 0
            
            last_executed = max(e.executed_at for e in executions)
            issues_reported = sum(1 for e in executions if e.error_message or not e.success)
            improvements_applied = sum(len(e.improvements_suggested or []) for e in executions)
            
            metrics = VersionMetrics(
                version_id=version_id,
                total_executions=total_executions,
                successful_executions=successful_executions,
                success_rate=success_rate,
                average_duration=average_duration,
                average_feedback_score=average_feedback_score,
                last_executed=last_executed,
                issues_reported=issues_reported,
                improvements_applied=improvements_applied
            )
            
            # Store metrics
            await self._store_metrics(metrics)
            
            # Update cache
            self.metrics_cache[version_id] = metrics
            
        except Exception as e:
            logger.error(f"Failed to update version metrics: {e}")
    
    async def _get_version_executions(self, version_id: str) -> List[PlaybookExecution]:
        """Get all executions for a specific version"""
        try:
            search_results = await self.memory_storage.search_memories(
                query=f"version_id:{version_id}",
                category="playbook_executions",
                limit=1000
            )
            
            executions = []
            for memory in search_results.get('memories', []):
                try:
                    execution_data = json.loads(memory.get('content', '{}'))
                    execution = PlaybookExecution(**execution_data)
                    executions.append(execution)
                except Exception as e:
                    logger.warning(f"Failed to parse execution data: {e}")
            
            return executions
            
        except Exception as e:
            logger.error(f"Failed to get version executions: {e}")
            return []
    
    async def _get_recent_executions(self, version_id: str, hours: int = 24) -> List[PlaybookExecution]:
        """Get recent executions for a version"""
        try:
            all_executions = await self._get_version_executions(version_id)
            cutoff = datetime.now() - timedelta(hours=hours)
            
            return [e for e in all_executions if e.executed_at >= cutoff]
            
        except Exception as e:
            logger.error(f"Failed to get recent executions: {e}")
            return []
    
    async def _store_metrics(self, metrics: VersionMetrics):
        """Store version metrics in memory system"""
        try:
            await self.memory_storage.store_memory(
                content=json.dumps(asdict(metrics), default=str),
                category="playbook_metrics",
                metadata={
                    "version_id": metrics.version_id,
                    "success_rate": metrics.success_rate,
                    "total_executions": metrics.total_executions,
                    "average_feedback_score": metrics.average_feedback_score,
                    "last_executed": metrics.last_executed.isoformat()
                },
                tags=["metrics", "playbook", "performance"]
            )
        except Exception as e:
            logger.error(f"Failed to store metrics: {e}")
    
    async def _check_auto_improvement(self, version_id: str):
        """Check if a version needs auto-improvement based on performance"""
        try:
            metrics = await self.get_version_metrics(version_id)
            if not metrics:
                return
            
            # Check if performance is below threshold
            if (metrics.success_rate < self.auto_improve_threshold or
                metrics.average_feedback_score < self.auto_improve_threshold):
                
                # Get the version and suggest improvements
                version = await self.get_version(version_id)
                if version:
                    await self._suggest_version_improvements(version, metrics)
            
        except Exception as e:
            logger.warning(f"Failed to check auto-improvement: {e}")
    
    async def _suggest_version_improvements(self, version: PlaybookVersion, metrics: VersionMetrics):
        """Suggest improvements for a poorly performing version"""
        try:
            # Analyze execution failures
            executions = await self._get_version_executions(version.version_id)
            failed_executions = [e for e in executions if not e.success]
            
            # Collect common error patterns
            error_patterns = {}
            improvement_suggestions = set()
            
            for execution in failed_executions:
                if execution.error_message:
                    # Simple pattern matching for common issues
                    if "timeout" in execution.error_message.lower():
                        improvement_suggestions.add("Increase timeout values")
                    elif "permission" in execution.error_message.lower():
                        improvement_suggestions.add("Add permission checks")
                    elif "connection" in execution.error_message.lower():
                        improvement_suggestions.add("Add connection retry logic")
                
                # Add user-suggested improvements
                if execution.improvements_suggested:
                    improvement_suggestions.update(execution.improvements_suggested)
            
            if improvement_suggestions:
                # Store improvement suggestions
                await self.memory_storage.store_memory(
                    content=f"Auto-improvement suggestions for {version.playbook_id} v{version.version_number}:\n" + 
                           "\n".join(f"- {suggestion}" for suggestion in improvement_suggestions),
                    category="playbook_suggestions",
                    metadata={
                        "version_id": version.version_id,
                        "playbook_id": version.playbook_id,
                        "improvement_type": "auto_suggested",
                        "success_rate": metrics.success_rate,
                        "feedback_score": metrics.average_feedback_score
                    },
                    tags=["improvement", "auto_generated", "playbook"]
                )
                
                logger.info(f"💡 Generated improvement suggestions for {version.playbook_id} v{version.version_number}")
            
        except Exception as e:
            logger.error(f"Failed to suggest improvements: {e}")
    
    async def get_version_metrics(self, version_id: str) -> Optional[VersionMetrics]:
        """Get performance metrics for a version"""
        try:
            # Check cache first
            if version_id in self.metrics_cache:
                return self.metrics_cache[version_id]
            
            search_results = await self.memory_storage.search_memories(
                query=f"version_id:{version_id}",
                category="playbook_metrics",
                limit=1
            )
            
            if search_results.get('memories'):
                metrics_data = json.loads(search_results['memories'][0].get('content', '{}'))
                metrics = VersionMetrics(**metrics_data)
                self.metrics_cache[version_id] = metrics
                return metrics
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get version metrics: {e}")
            return None
    
    async def create_branch(self, playbook_id: str, branch_name: str, from_version: str) -> bool:
        """Create a new branch from an existing version"""
        try:
            source_version = await self.get_version(from_version)
            if not source_version:
                raise ValueError(f"Source version {from_version} not found")
            
            # Create new version on the new branch
            branch_version = await self.create_playbook_version(
                playbook_id=playbook_id,
                content=source_version.content,
                change_type=ChangeType.CREATED,
                change_description=f"Created branch '{branch_name}' from version {source_version.version_number}",
                author=source_version.author,
                parent_version=from_version,
                branch=branch_name,
                tags=["branch_creation"]
            )
            
            logger.info(f"🌿 Created branch '{branch_name}' for {playbook_id} from version {source_version.version_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create branch: {e}")
            return False
    
    async def merge_branch(self, 
                          playbook_id: str, 
                          source_branch: str, 
                          target_branch: str,
                          author: str,
                          merge_description: str) -> Optional[PlaybookVersion]:
        """Merge one branch into another"""
        try:
            # Get latest versions from both branches
            source_version = await self.get_latest_version(playbook_id, source_branch)
            target_version = await self.get_latest_version(playbook_id, target_branch)
            
            if not source_version:
                raise ValueError(f"No versions found in source branch '{source_branch}'")
            if not target_version:
                raise ValueError(f"No versions found in target branch '{target_branch}'")
            
            # Create merged version (using source content for now - could implement smart merging)
            merged_version = await self.create_playbook_version(
                playbook_id=playbook_id,
                content=source_version.content,
                change_type=ChangeType.MERGED,
                change_description=f"{merge_description} (merged from {source_branch})",
                author=author,
                parent_version=target_version.version_id,
                branch=target_branch,
                tags=["merge", f"from_{source_branch}"]
            )
            
            logger.info(f"🔀 Merged branch '{source_branch}' into '{target_branch}' for {playbook_id}")
            return merged_version
            
        except Exception as e:
            logger.error(f"Failed to merge branches: {e}")
            return None
    
    async def rollback_to_version(self, 
                                playbook_id: str, 
                                target_version_id: str,
                                author: str,
                                rollback_reason: str,
                                branch: str = "main") -> Optional[PlaybookVersion]:
        """Rollback to a previous version"""
        try:
            target_version = await self.get_version(target_version_id)
            if not target_version:
                raise ValueError(f"Target version {target_version_id} not found")
            
            # Create rollback version
            rollback_version = await self.create_playbook_version(
                playbook_id=playbook_id,
                content=target_version.content,
                change_type=ChangeType.ROLLBACK,
                change_description=f"Rollback to version {target_version.version_number}: {rollback_reason}",
                author=author,
                parent_version=target_version_id,
                branch=branch,
                tags=["rollback", f"to_{target_version.version_number}"]
            )
            
            logger.info(f"⏪ Rolled back {playbook_id} to version {target_version.version_number}")
            return rollback_version
            
        except Exception as e:
            logger.error(f"Failed to rollback version: {e}")
            return None
    
    async def get_version_history(self, playbook_id: str, branch: str = "main", limit: int = 50) -> List[PlaybookVersion]:
        """Get version history for a playbook"""
        try:
            versions = await self._get_playbook_versions(playbook_id, branch)
            return versions[:limit]
        except Exception as e:
            logger.error(f"Failed to get version history: {e}")
            return []
    
    async def compare_versions(self, version_id_1: str, version_id_2: str) -> Dict[str, Any]:
        """Compare two versions and return differences"""
        try:
            version_1 = await self.get_version(version_id_1)
            version_2 = await self.get_version(version_id_2)
            
            if not version_1 or not version_2:
                return {"error": "One or both versions not found"}
            
            # Simple comparison - could be enhanced with detailed diff
            differences = {
                "version_1": {
                    "id": version_1.version_id,
                    "number": version_1.version_number,
                    "author": version_1.author,
                    "created_at": version_1.created_at.isoformat(),
                    "change_description": version_1.change_description
                },
                "version_2": {
                    "id": version_2.version_id,
                    "number": version_2.version_number,
                    "author": version_2.author,
                    "created_at": version_2.created_at.isoformat(),
                    "change_description": version_2.change_description
                },
                "content_identical": version_1.content_hash == version_2.content_hash,
                "content_hash_1": version_1.content_hash,
                "content_hash_2": version_2.content_hash
            }
            
            # Get performance comparison if available
            metrics_1 = await self.get_version_metrics(version_id_1)
            metrics_2 = await self.get_version_metrics(version_id_2)
            
            if metrics_1 and metrics_2:
                differences["performance_comparison"] = {
                    "success_rate_diff": metrics_2.success_rate - metrics_1.success_rate,
                    "duration_diff": metrics_2.average_duration - metrics_1.average_duration,
                    "feedback_score_diff": metrics_2.average_feedback_score - metrics_1.average_feedback_score
                }
            
            return differences
            
        except Exception as e:
            logger.error(f"Failed to compare versions: {e}")
            return {"error": str(e)}
    
    async def get_playbook_statistics(self, playbook_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a playbook across all versions"""
        try:
            # Get all versions
            all_versions = []
            for branch in ["main", "develop", "experimental"]:  # Common branches
                branch_versions = await self._get_playbook_versions(playbook_id, branch)
                all_versions.extend(branch_versions)
            
            if not all_versions:
                return {"error": "No versions found for playbook"}
            
            # Calculate statistics
            total_versions = len(all_versions)
            branches = list(set(v.branch for v in all_versions))
            authors = list(set(v.author for v in all_versions))
            
            # Get execution statistics
            all_executions = []
            for version in all_versions:
                version_executions = await self._get_version_executions(version.version_id)
                all_executions.extend(version_executions)
            
            total_executions = len(all_executions)
            successful_executions = sum(1 for e in all_executions if e.success)
            overall_success_rate = successful_executions / total_executions if total_executions > 0 else 0
            
            # Latest version info
            latest_version = max(all_versions, key=lambda v: v.created_at)
            
            statistics = {
                "playbook_id": playbook_id,
                "total_versions": total_versions,
                "branches": branches,
                "authors": authors,
                "latest_version": {
                    "version_id": latest_version.version_id,
                    "version_number": latest_version.version_number,
                    "branch": latest_version.branch,
                    "created_at": latest_version.created_at.isoformat()
                },
                "execution_statistics": {
                    "total_executions": total_executions,
                    "successful_executions": successful_executions,
                    "overall_success_rate": overall_success_rate
                },
                "version_distribution": {
                    branch: len([v for v in all_versions if v.branch == branch])
                    for branch in branches
                },
                "change_type_distribution": {
                    change_type.value: len([v for v in all_versions if v.change_type == change_type])
                    for change_type in ChangeType
                }
            }
            
            return statistics
            
        except Exception as e:
            logger.error(f"Failed to get playbook statistics: {e}")
            return {"error": str(e)}