#!/usr/bin/env python3
"""
hAIveMind Memory Format System - Token Optimization & Format Guidance

Teaches Claude the optimal compression format on first memory access,
tracks format versions, and detects legacy verbose content.
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Current format version
FORMAT_VERSION = "v2"

# Compact format guide (injected on first access)
FORMAT_GUIDE_COMPACT = """=== hAIveMind Format v2 ===
STORE/READ with these conventions:

Symbols: → (flow) | (or) ? (opt) ! (req) :: (type)
Tables > prose: | key | val |
Refs: [ID]: define → use [ID]
Compact: auth(key) → search(q) → JSON

Legacy memories may be verbose - ok to read, compress when updating.
"""

# Detailed format guide (available on demand)
FORMAT_GUIDE_FULL = """=== hAIveMind Optimal Format Guide (v2) ===

PURPOSE: Minimize token usage while preserving semantic clarity.

1. STRUCTURED > PROSE
   ❌ "The user should authenticate, then search"
   ✅ auth(key) → search(query) → results

2. TABLES > LISTS
   ❌ "Tool A does X, Tool B does Y, Tool C does Z"
   ✅ | Tool | Function |
      | A    | X        |
      | B    | Y        |

3. SYMBOLS (AI-native)
   → flow/returns    | OR options
   ? optional        * many/repeated
   ! required        :: type annotation

4. REFERENCE PATTERN
   [CTX-1]: complex context defined once
   Later: "See [CTX-1]" instead of repeating

5. SEMANTIC DENSITY
   ❌ "make it so only authorized users can access"
   ✅ "add RBAC" or "auth guard"

6. HIERARCHICAL NESTING (YAML-style)
   api:
     auth: [jwt, oauth]
     endpoints: [/users, /items]

7. COMPRESSION RATIO
   Target: 60-80% reduction from prose
   Example: 52 words → 15 tokens (71% savings)

WHEN STORING: Use v2 format for new memories
WHEN READING: Legacy (v1) content is fine, compress on update
"""


class MemoryFormatSystem:
    """Manages format versioning, session tracking, and format guidance injection."""

    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.session_id = self._generate_session_id()
        self._first_access_done = False
        self._access_log: List[Dict[str, Any]] = []

    def _generate_session_id(self) -> str:
        """Generate or retrieve session ID from environment."""
        # Check for existing session ID
        env_session = os.environ.get('CLAUDE_SESSION_ID') or os.environ.get('HAIVEMIND_SESSION_ID')
        if env_session:
            return env_session

        # Generate new session ID
        return f"session-{int(time.time())}-{os.getpid()}"

    def _check_redis_session(self) -> bool:
        """Check if this session has accessed memory before (via Redis)."""
        if not self.redis_client:
            return self._first_access_done

        try:
            key = f"haivemind:session:{self.session_id}:accessed"
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.debug(f"Redis session check failed: {e}")
            return self._first_access_done

    def _mark_session_accessed(self):
        """Mark this session as having accessed memory."""
        self._first_access_done = True

        if self.redis_client:
            try:
                key = f"haivemind:session:{self.session_id}:accessed"
                self.redis_client.setex(key, 3600 * 4, "1")  # 4 hour TTL
            except Exception as e:
                logger.debug(f"Redis session mark failed: {e}")

    def record_access(self, tool_name: str, arguments: Dict[str, Any]):
        """Record a memory tool access."""
        self._access_log.append({
            "tool": tool_name,
            "timestamp": time.time(),
            "session_id": self.session_id,
            "arguments_keys": list(arguments.keys())
        })

    def is_first_session_access(self) -> bool:
        """Check if this is the first memory access in the session."""
        return not self._check_redis_session()

    def get_format_metadata(self, include_guide: bool = False) -> Dict[str, Any]:
        """Get format metadata to include in responses."""
        is_first = self.is_first_session_access()

        meta = {
            "format_version": FORMAT_VERSION,
            "is_first_session_access": is_first,
            "session_id": self.session_id
        }

        if include_guide or is_first:
            meta["format_guide"] = FORMAT_GUIDE_COMPACT

        return meta

    def enhance_response(self, data: Any, tool_name: str) -> Dict[str, Any]:
        """
        Enhance a tool response with format metadata.
        On first access, includes the format guide.
        """
        is_first = self.is_first_session_access()

        # Build enhanced response
        enhanced = {
            "_haivemind_meta": {
                "format_version": FORMAT_VERSION,
                "tool": tool_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        # Add format guide on first access
        if is_first:
            enhanced["_haivemind_meta"]["is_first_session_access"] = True
            enhanced["_haivemind_meta"]["format_guide"] = FORMAT_GUIDE_COMPACT
            self._mark_session_accessed()

        # Add the actual data
        enhanced["data"] = data

        # Check for legacy content in memories
        if isinstance(data, list):
            legacy_count = sum(1 for item in data if self._is_legacy_content(item))
            if legacy_count > 0:
                enhanced["_haivemind_meta"]["legacy_content_detected"] = True
                enhanced["_haivemind_meta"]["legacy_count"] = legacy_count
                enhanced["_haivemind_meta"]["hint"] = "Consider updating verbose memories to v2 format"

        return enhanced

    def _is_legacy_content(self, memory: Dict[str, Any]) -> bool:
        """Detect if memory content appears to be verbose/legacy format."""
        if not isinstance(memory, dict):
            return False

        content = memory.get('content', '') or ''
        metadata = memory.get('metadata', {}) or {}

        # Check for format version tag
        if metadata.get('format_version') == FORMAT_VERSION:
            return False

        # Heuristics for verbose content
        if len(content) < 50:
            return False

        # Check for verbose patterns
        verbose_indicators = [
            "should be able to",
            "The user will",
            "In order to",
            "Please note that",
            "It is important to",
            "you need to first",
            "make sure that",
        ]

        content_lower = content.lower()
        verbose_score = sum(1 for pattern in verbose_indicators if pattern.lower() in content_lower)

        # Check word-to-symbol ratio (compact format uses more symbols)
        words = len(content.split())
        symbols = sum(content.count(s) for s in ['→', '|', '::', '?', '!', '*'])

        # If many words but few compression symbols, likely verbose
        if words > 30 and symbols < 2:
            verbose_score += 1

        return verbose_score >= 2

    def prepare_memory_metadata(self, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add format version to memory metadata before storage."""
        meta = metadata.copy() if metadata else {}
        meta['format_version'] = FORMAT_VERSION
        meta['stored_at'] = datetime.utcnow().isoformat()
        return meta

    def get_access_stats(self) -> Dict[str, Any]:
        """Get statistics about memory access in this session."""
        tool_counts = {}
        for access in self._access_log:
            tool = access['tool']
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

        return {
            "session_id": self.session_id,
            "total_accesses": len(self._access_log),
            "first_access_done": self._first_access_done,
            "tool_usage": tool_counts,
            "format_version": FORMAT_VERSION
        }

    def get_format_guide(self, detailed: bool = False) -> str:
        """Get the format guide (compact or detailed)."""
        return FORMAT_GUIDE_FULL if detailed else FORMAT_GUIDE_COMPACT


# Singleton instance for the format system
_format_system_instance: Optional[MemoryFormatSystem] = None


def get_format_system(redis_client=None) -> MemoryFormatSystem:
    """Get or create the singleton format system instance."""
    global _format_system_instance
    if _format_system_instance is None:
        _format_system_instance = MemoryFormatSystem(redis_client)
    return _format_system_instance


def reset_format_system():
    """Reset the format system (mainly for testing)."""
    global _format_system_instance
    _format_system_instance = None
