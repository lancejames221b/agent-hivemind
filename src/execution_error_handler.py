#!/usr/bin/env python3
"""
Error Handling and Retry Logic for Advanced Playbook Engine

Provides intelligent error handling, retry mechanisms with exponential backoff,
and integration with hAIveMind for learning from execution patterns.
"""

from __future__ import annotations

import asyncio
import logging
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union
import re
import json

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of errors for intelligent handling"""
    NETWORK = "network"
    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    RESOURCE = "resource"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"
    TEMPORARY = "temporary"
    PERMANENT = "permanent"
    UNKNOWN = "unknown"


class RetryStrategy(Enum):
    """Retry strategies"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"
    NO_RETRY = "no_retry"


@dataclass
class ErrorPattern:
    """Pattern for matching and categorizing errors"""
    name: str
    category: ErrorCategory
    patterns: List[str]  # Regex patterns
    retry_strategy: RetryStrategy
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    custom_handler: Optional[str] = None


@dataclass
class ErrorContext:
    """Context information for error handling"""
    step_id: str
    run_id: str
    playbook_id: int
    error_message: str
    error_type: str
    stack_trace: str
    timestamp: float
    attempt_number: int
    previous_attempts: List[Dict[str, Any]] = field(default_factory=list)
    environment: Dict[str, Any] = field(default_factory=dict)
    step_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetryDecision:
    """Decision about whether and how to retry"""
    should_retry: bool
    delay_seconds: float
    strategy: RetryStrategy
    reason: str
    max_attempts_reached: bool = False
    category: ErrorCategory = ErrorCategory.UNKNOWN


class ExecutionErrorHandler:
    """Intelligent error handler with learning capabilities"""
    
    def __init__(self, haivemind_client: Optional[Any] = None):
        self.haivemind_client = haivemind_client
        
        # Built-in error patterns
        self.error_patterns = self._initialize_error_patterns()
        
        # Error statistics for learning
        self.error_stats = {}
        self.retry_success_rates = {}
        
        # Custom error handlers
        self.custom_handlers = {}
        
        # Circuit breaker states
        self.circuit_breakers = {}
    
    def _initialize_error_patterns(self) -> List[ErrorPattern]:
        """Initialize built-in error patterns"""
        return [
            # Network errors
            ErrorPattern(
                name="connection_timeout",
                category=ErrorCategory.NETWORK,
                patterns=[
                    r"connection.*timeout",
                    r"timeout.*connection",
                    r"read.*timeout",
                    r"connect.*timeout"
                ],
                retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_retries=5,
                base_delay=2.0,
                max_delay=30.0
            ),
            ErrorPattern(
                name="connection_refused",
                category=ErrorCategory.NETWORK,
                patterns=[
                    r"connection.*refused",
                    r"refused.*connection",
                    r"no route to host",
                    r"network.*unreachable"
                ],
                retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_retries=3,
                base_delay=5.0,
                max_delay=60.0
            ),
            ErrorPattern(
                name="dns_resolution",
                category=ErrorCategory.NETWORK,
                patterns=[
                    r"name.*not.*resolved",
                    r"dns.*resolution.*failed",
                    r"hostname.*not.*found",
                    r"nodename.*nor.*servname"
                ],
                retry_strategy=RetryStrategy.LINEAR_BACKOFF,
                max_retries=3,
                base_delay=10.0
            ),
            
            # HTTP errors
            ErrorPattern(
                name="http_5xx",
                category=ErrorCategory.TEMPORARY,
                patterns=[
                    r"http.*5\d\d",
                    r"internal.*server.*error",
                    r"bad.*gateway",
                    r"service.*unavailable",
                    r"gateway.*timeout"
                ],
                retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_retries=4,
                base_delay=1.0,
                max_delay=16.0
            ),
            ErrorPattern(
                name="http_429",
                category=ErrorCategory.TEMPORARY,
                patterns=[
                    r"http.*429",
                    r"too.*many.*requests",
                    r"rate.*limit.*exceeded"
                ],
                retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_retries=5,
                base_delay=5.0,
                max_delay=120.0
            ),
            ErrorPattern(
                name="http_4xx_client",
                category=ErrorCategory.PERMANENT,
                patterns=[
                    r"http.*40[0-3]",
                    r"http.*40[5-9]",
                    r"bad.*request",
                    r"unauthorized",
                    r"forbidden",
                    r"not.*found",
                    r"method.*not.*allowed"
                ],
                retry_strategy=RetryStrategy.NO_RETRY,
                max_retries=0
            ),
            
            # Authentication/Authorization
            ErrorPattern(
                name="auth_token_expired",
                category=ErrorCategory.AUTHENTICATION,
                patterns=[
                    r"token.*expired",
                    r"expired.*token",
                    r"authentication.*expired",
                    r"session.*expired"
                ],
                retry_strategy=RetryStrategy.IMMEDIATE,
                max_retries=2,
                custom_handler="refresh_auth_token"
            ),
            ErrorPattern(
                name="permission_denied",
                category=ErrorCategory.AUTHORIZATION,
                patterns=[
                    r"permission.*denied",
                    r"access.*denied",
                    r"insufficient.*privileges",
                    r"unauthorized.*access"
                ],
                retry_strategy=RetryStrategy.NO_RETRY,
                max_retries=0
            ),
            
            # Resource errors
            ErrorPattern(
                name="disk_full",
                category=ErrorCategory.RESOURCE,
                patterns=[
                    r"no.*space.*left",
                    r"disk.*full",
                    r"insufficient.*disk.*space",
                    r"device.*full"
                ],
                retry_strategy=RetryStrategy.LINEAR_BACKOFF,
                max_retries=2,
                base_delay=30.0,
                custom_handler="cleanup_disk_space"
            ),
            ErrorPattern(
                name="memory_exhausted",
                category=ErrorCategory.RESOURCE,
                patterns=[
                    r"out.*of.*memory",
                    r"memory.*exhausted",
                    r"cannot.*allocate.*memory",
                    r"insufficient.*memory"
                ],
                retry_strategy=RetryStrategy.LINEAR_BACKOFF,
                max_retries=2,
                base_delay=60.0,
                custom_handler="free_memory"
            ),
            
            # Service/dependency errors
            ErrorPattern(
                name="service_unavailable",
                category=ErrorCategory.DEPENDENCY,
                patterns=[
                    r"service.*unavailable",
                    r"service.*down",
                    r"service.*not.*running",
                    r"dependency.*unavailable"
                ],
                retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_retries=5,
                base_delay=10.0,
                max_delay=300.0
            ),
            
            # Configuration errors
            ErrorPattern(
                name="config_invalid",
                category=ErrorCategory.CONFIGURATION,
                patterns=[
                    r"invalid.*configuration",
                    r"configuration.*error",
                    r"config.*not.*found",
                    r"malformed.*config"
                ],
                retry_strategy=RetryStrategy.NO_RETRY,
                max_retries=0
            ),
            
            # Validation errors
            ErrorPattern(
                name="validation_failed",
                category=ErrorCategory.VALIDATION,
                patterns=[
                    r"validation.*failed",
                    r"invalid.*input",
                    r"schema.*validation",
                    r"parameter.*invalid"
                ],
                retry_strategy=RetryStrategy.NO_RETRY,
                max_retries=0
            ),
            
            # Temporary system errors
            ErrorPattern(
                name="temporary_failure",
                category=ErrorCategory.TEMPORARY,
                patterns=[
                    r"temporary.*failure",
                    r"try.*again.*later",
                    r"system.*busy",
                    r"resource.*temporarily.*unavailable"
                ],
                retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_retries=3,
                base_delay=5.0,
                max_delay=60.0
            )
        ]
    
    async def handle_error(self, error_context: ErrorContext) -> RetryDecision:
        """Handle an error and decide on retry strategy"""
        try:
            # Categorize the error
            error_pattern = self._match_error_pattern(error_context.error_message)
            category = error_pattern.category if error_pattern else ErrorCategory.UNKNOWN
            
            # Update error statistics
            await self._update_error_stats(error_context, category)
            
            # Check circuit breaker
            if self._is_circuit_breaker_open(error_context.step_id, category):
                return RetryDecision(
                    should_retry=False,
                    delay_seconds=0,
                    strategy=RetryStrategy.NO_RETRY,
                    reason="Circuit breaker open",
                    category=category
                )
            
            # Determine retry decision
            if not error_pattern:
                # Unknown error - use conservative retry
                return await self._handle_unknown_error(error_context)
            
            # Check if max attempts reached
            if error_context.attempt_number >= error_pattern.max_retries:
                await self._update_circuit_breaker(error_context.step_id, category, success=False)
                return RetryDecision(
                    should_retry=False,
                    delay_seconds=0,
                    strategy=error_pattern.retry_strategy,
                    reason=f"Max retries ({error_pattern.max_retries}) reached",
                    max_attempts_reached=True,
                    category=category
                )
            
            # Execute custom handler if specified
            if error_pattern.custom_handler:
                await self._execute_custom_handler(error_pattern.custom_handler, error_context)
            
            # Calculate retry delay
            delay = self._calculate_retry_delay(error_pattern, error_context.attempt_number)
            
            # Store retry attempt in hAIveMind
            if self.haivemind_client:
                await self._store_retry_attempt(error_context, error_pattern, delay)
            
            return RetryDecision(
                should_retry=error_pattern.retry_strategy != RetryStrategy.NO_RETRY,
                delay_seconds=delay,
                strategy=error_pattern.retry_strategy,
                reason=f"Retry attempt {error_context.attempt_number + 1}/{error_pattern.max_retries}",
                category=category
            )
            
        except Exception as e:
            logger.error(f"Error in error handler: {e}", exc_info=True)
            # Fallback to no retry on handler error
            return RetryDecision(
                should_retry=False,
                delay_seconds=0,
                strategy=RetryStrategy.NO_RETRY,
                reason=f"Error handler failed: {str(e)}",
                category=ErrorCategory.UNKNOWN
            )
    
    def _match_error_pattern(self, error_message: str) -> Optional[ErrorPattern]:
        """Match error message against known patterns"""
        error_lower = error_message.lower()
        
        for pattern in self.error_patterns:
            for regex_pattern in pattern.patterns:
                if re.search(regex_pattern, error_lower, re.IGNORECASE):
                    return pattern
        
        return None
    
    async def _handle_unknown_error(self, error_context: ErrorContext) -> RetryDecision:
        """Handle unknown errors with conservative retry"""
        # Use hAIveMind to check if we've seen similar errors before
        if self.haivemind_client:
            similar_errors = await self._find_similar_errors(error_context)
            if similar_errors:
                # Use pattern from most similar error
                best_match = similar_errors[0]
                return RetryDecision(
                    should_retry=best_match.get("should_retry", False),
                    delay_seconds=best_match.get("delay_seconds", 5.0),
                    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                    reason=f"Similar error pattern found (confidence: {best_match.get('confidence', 0):.2f})",
                    category=ErrorCategory.UNKNOWN
                )
        
        # Conservative default for unknown errors
        if error_context.attempt_number < 2:
            return RetryDecision(
                should_retry=True,
                delay_seconds=5.0,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                reason="Unknown error - conservative retry",
                category=ErrorCategory.UNKNOWN
            )
        else:
            return RetryDecision(
                should_retry=False,
                delay_seconds=0,
                strategy=RetryStrategy.NO_RETRY,
                reason="Unknown error - max conservative retries reached",
                category=ErrorCategory.UNKNOWN
            )
    
    def _calculate_retry_delay(self, pattern: ErrorPattern, attempt_number: int) -> float:
        """Calculate retry delay based on strategy"""
        import random
        
        if pattern.retry_strategy == RetryStrategy.NO_RETRY:
            return 0
        elif pattern.retry_strategy == RetryStrategy.IMMEDIATE:
            return 0
        elif pattern.retry_strategy == RetryStrategy.FIXED_DELAY:
            delay = pattern.base_delay
        elif pattern.retry_strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = pattern.base_delay * (attempt_number + 1)
        elif pattern.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = pattern.base_delay * (pattern.backoff_multiplier ** attempt_number)
        else:
            delay = pattern.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, pattern.max_delay)
        
        # Add jitter to prevent thundering herd
        if pattern.jitter:
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        return max(0, delay)
    
    async def _update_error_stats(self, error_context: ErrorContext, category: ErrorCategory) -> None:
        """Update error statistics for learning"""
        key = f"{error_context.step_id}:{category.value}"
        
        if key not in self.error_stats:
            self.error_stats[key] = {
                "total_errors": 0,
                "error_types": {},
                "recent_errors": []
            }
        
        stats = self.error_stats[key]
        stats["total_errors"] += 1
        
        # Track error types
        error_type = error_context.error_type
        if error_type not in stats["error_types"]:
            stats["error_types"][error_type] = 0
        stats["error_types"][error_type] += 1
        
        # Keep recent errors (last 10)
        stats["recent_errors"].append({
            "timestamp": error_context.timestamp,
            "message": error_context.error_message,
            "attempt": error_context.attempt_number
        })
        if len(stats["recent_errors"]) > 10:
            stats["recent_errors"] = stats["recent_errors"][-10:]
    
    def _is_circuit_breaker_open(self, step_id: str, category: ErrorCategory) -> bool:
        """Check if circuit breaker is open for this step/category"""
        key = f"{step_id}:{category.value}"
        
        if key not in self.circuit_breakers:
            return False
        
        breaker = self.circuit_breakers[key]
        current_time = time.time()
        
        # Check if circuit breaker should reset
        if current_time - breaker["last_failure"] > breaker["reset_timeout"]:
            breaker["state"] = "closed"
            breaker["failure_count"] = 0
            return False
        
        return breaker["state"] == "open"
    
    async def _update_circuit_breaker(self, step_id: str, category: ErrorCategory, success: bool) -> None:
        """Update circuit breaker state"""
        key = f"{step_id}:{category.value}"
        current_time = time.time()
        
        if key not in self.circuit_breakers:
            self.circuit_breakers[key] = {
                "state": "closed",
                "failure_count": 0,
                "last_failure": 0,
                "reset_timeout": 300,  # 5 minutes
                "failure_threshold": 5
            }
        
        breaker = self.circuit_breakers[key]
        
        if success:
            breaker["failure_count"] = 0
            breaker["state"] = "closed"
        else:
            breaker["failure_count"] += 1
            breaker["last_failure"] = current_time
            
            if breaker["failure_count"] >= breaker["failure_threshold"]:
                breaker["state"] = "open"
                logger.warning(f"Circuit breaker opened for {key}")
    
    async def _execute_custom_handler(self, handler_name: str, error_context: ErrorContext) -> None:
        """Execute custom error handler"""
        if handler_name in self.custom_handlers:
            try:
                await self.custom_handlers[handler_name](error_context)
            except Exception as e:
                logger.error(f"Custom handler {handler_name} failed: {e}")
        else:
            logger.warning(f"Custom handler {handler_name} not found")
    
    async def _store_retry_attempt(self, error_context: ErrorContext, pattern: ErrorPattern, delay: float) -> None:
        """Store retry attempt in hAIveMind"""
        try:
            await self.haivemind_client.store_memory(
                content=f"Retry attempt for error: {error_context.error_message}",
                category="playbook_execution",
                metadata={
                    "run_id": error_context.run_id,
                    "step_id": error_context.step_id,
                    "error_category": pattern.category.value,
                    "retry_strategy": pattern.retry_strategy.value,
                    "attempt_number": error_context.attempt_number,
                    "delay_seconds": delay,
                    "error_pattern": pattern.name
                },
                tags=["error_handling", "retry", pattern.category.value]
            )
        except Exception as e:
            logger.error(f"Failed to store retry attempt in hAIveMind: {e}")
    
    async def _find_similar_errors(self, error_context: ErrorContext) -> List[Dict[str, Any]]:
        """Find similar errors in hAIveMind"""
        try:
            # Search for similar error messages
            results = await self.haivemind_client.search_memories(
                query=error_context.error_message,
                category="playbook_execution",
                limit=5
            )
            
            # Filter and score results
            similar_errors = []
            for result in results:
                metadata = result.get("metadata", {})
                if "error_category" in metadata and "retry_strategy" in metadata:
                    # Calculate similarity score (simplified)
                    confidence = result.get("score", 0.0)
                    similar_errors.append({
                        "should_retry": metadata.get("retry_strategy") != "no_retry",
                        "delay_seconds": metadata.get("delay_seconds", 5.0),
                        "confidence": confidence,
                        "category": metadata.get("error_category")
                    })
            
            return sorted(similar_errors, key=lambda x: x["confidence"], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to find similar errors in hAIveMind: {e}")
            return []
    
    def add_error_pattern(self, pattern: ErrorPattern) -> None:
        """Add a custom error pattern"""
        self.error_patterns.append(pattern)
        logger.info(f"Added custom error pattern: {pattern.name}")
    
    def add_custom_handler(self, name: str, handler: Callable[[ErrorContext], None]) -> None:
        """Add a custom error handler"""
        self.custom_handlers[name] = handler
        logger.info(f"Added custom error handler: {name}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for analysis"""
        return {
            "error_stats": self.error_stats,
            "circuit_breakers": self.circuit_breakers,
            "retry_success_rates": self.retry_success_rates,
            "total_patterns": len(self.error_patterns)
        }
    
    async def learn_from_execution(self, run_id: str, success: bool, error_contexts: List[ErrorContext]) -> None:
        """Learn from execution results to improve error handling"""
        if not self.haivemind_client:
            return
        
        try:
            # Analyze error patterns and success rates
            pattern_performance = {}
            
            for error_context in error_contexts:
                pattern = self._match_error_pattern(error_context.error_message)
                if pattern:
                    key = pattern.name
                    if key not in pattern_performance:
                        pattern_performance[key] = {
                            "total_attempts": 0,
                            "successful_retries": 0,
                            "failed_retries": 0
                        }
                    
                    pattern_performance[key]["total_attempts"] += 1
                    if success:
                        pattern_performance[key]["successful_retries"] += 1
                    else:
                        pattern_performance[key]["failed_retries"] += 1
            
            # Store learning results
            await self.haivemind_client.store_memory(
                content=f"Error handling learning from execution {run_id}",
                category="playbook_execution",
                metadata={
                    "run_id": run_id,
                    "execution_success": success,
                    "pattern_performance": pattern_performance,
                    "total_errors": len(error_contexts),
                    "learning_timestamp": time.time()
                },
                tags=["error_handling", "learning", "pattern_analysis"]
            )
            
            # Update retry success rates
            for pattern_name, perf in pattern_performance.items():
                if pattern_name not in self.retry_success_rates:
                    self.retry_success_rates[pattern_name] = {
                        "total_attempts": 0,
                        "successful_retries": 0
                    }
                
                rates = self.retry_success_rates[pattern_name]
                rates["total_attempts"] += perf["total_attempts"]
                rates["successful_retries"] += perf["successful_retries"]
            
        except Exception as e:
            logger.error(f"Failed to learn from execution: {e}")


# Built-in custom handlers

async def refresh_auth_token_handler(error_context: ErrorContext) -> None:
    """Handler for refreshing authentication tokens"""
    logger.info(f"Attempting to refresh auth token for step {error_context.step_id}")
    # Implementation would depend on the specific authentication system
    # This is a placeholder for the actual token refresh logic
    pass


async def cleanup_disk_space_handler(error_context: ErrorContext) -> None:
    """Handler for cleaning up disk space"""
    logger.info(f"Attempting to clean up disk space for step {error_context.step_id}")
    # Implementation would include:
    # - Clean temporary files
    # - Rotate logs
    # - Remove old cache files
    # - etc.
    pass


async def free_memory_handler(error_context: ErrorContext) -> None:
    """Handler for freeing memory"""
    logger.info(f"Attempting to free memory for step {error_context.step_id}")
    # Implementation would include:
    # - Force garbage collection
    # - Clear caches
    # - Restart memory-intensive services
    # - etc.
    pass


def create_default_error_handler(haivemind_client: Optional[Any] = None) -> ExecutionErrorHandler:
    """Create error handler with default configuration"""
    handler = ExecutionErrorHandler(haivemind_client)
    
    # Add built-in custom handlers
    handler.add_custom_handler("refresh_auth_token", refresh_auth_token_handler)
    handler.add_custom_handler("cleanup_disk_space", cleanup_disk_space_handler)
    handler.add_custom_handler("free_memory", free_memory_handler)
    
    return handler