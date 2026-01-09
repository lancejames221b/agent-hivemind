#!/usr/bin/env python3
"""
Memory Format System - Optimal AI Communication for hAIveMind

Provides:
1. Format guide metadata injection for AI-optimal memory storage/retrieval
2. Memory access detection and logging
3. Format version tracking for migration
4. Compression hints for Claude
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# Current format version
FORMAT_VERSION = "v2"

class FormatVersion(Enum):
    """Memory format versions for migration tracking"""
    V1_VERBOSE = "v1"      # Original verbose prose format
    V2_COMPRESSED = "v2"   # Optimized compressed format


# Compact format guide injected into memory responses
# This teaches Claude the optimal compression language on first access
FORMAT_GUIDE_COMPACT = """
=== hAIveMind Format Guide (v2) ===
STORE memories using compressed notation:
- Tables > prose: | key | value |
- Symbols: → (flow), | (or), ? (optional), ! (required), :: (type)
- Refs: [ID]: define once, use [ID] to reference
- Pseudocode: if err: retry(3) else: return
- YAML/JSON for structure, not sentences
- Technical terms > descriptions: "RBAC" not "role-based access"

Example compression:
❌ "When searching, authenticate with API key, then call search endpoint"
✅ auth(key) → search(query) → results::JSON

Old memories (v1) may be verbose - compress when updating.
"""

# Ultra-compact version for subsequent accesses (saves tokens)
FORMAT_GUIDE_MINIMAL = "Format:v2|Tables>prose|→=flow|[REF]:define→use"


@dataclass
class MemoryAccessEvent:
    """Tracks when Claude accesses memory tools"""
    tool_name: str
    timestamp: str
    session_id: str
    arguments: Dict[str, Any]
    is_first_access: bool
    format_version: str = FORMAT_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryFormatMeta:
    """Metadata injected into memory responses"""
    format_version: str = FORMAT_VERSION
    format_guide: str = ""
    access_logged: bool = True
    is_first_session_access: bool = False
    legacy_content_detected: bool = False
    compression_hint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v}  # Skip empty


class MemoryAccessTracker:
    """
    Tracks memory tool access patterns per session.
    Detects first access to inject format guide.
    """

    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self._session_access_count: Dict[str, int] = {}
        self._access_log: List[MemoryAccessEvent] = []
        self._hooks: Dict[str, List[Callable]] = {
            'on_memory_read': [],
            'on_memory_write': [],
            'on_first_access': [],
        }

    def get_session_id(self) -> str:
        """Get or generate session ID"""
        # Try to get from environment or generate
        import os
        return os.environ.get('CLAUDE_SESSION_ID', f"session_{int(time.time())}")

    def is_first_access(self, session_id: str = None) -> bool:
        """Check if this is the first memory access in session"""
        session_id = session_id or self.get_session_id()
        return self._session_access_count.get(session_id, 0) == 0

    def record_access(self, tool_name: str, arguments: Dict[str, Any]) -> MemoryAccessEvent:
        """Record a memory tool access"""
        session_id = self.get_session_id()
        is_first = self.is_first_access(session_id)

        event = MemoryAccessEvent(
            tool_name=tool_name,
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            arguments={k: str(v)[:100] for k, v in arguments.items()},  # Truncate for logging
            is_first_access=is_first
        )

        # Update counters
        self._session_access_count[session_id] = self._session_access_count.get(session_id, 0) + 1
        self._access_log.append(event)

        # Keep log bounded
        if len(self._access_log) > 1000:
            self._access_log = self._access_log[-500:]

        # Trigger hooks
        if is_first:
            self._trigger_hooks('on_first_access', event)

        if tool_name in ['search_memories', 'retrieve_memory', 'get_recent_memories']:
            self._trigger_hooks('on_memory_read', event)
        elif tool_name in ['store_memory', 'update_memory']:
            self._trigger_hooks('on_memory_write', event)

        # Log to Redis if available
        if self.redis_client:
            try:
                self.redis_client.lpush(
                    f"memory_access:{session_id}",
                    json.dumps(event.to_dict())
                )
                self.redis_client.expire(f"memory_access:{session_id}", 86400)  # 24h
            except Exception as e:
                logger.warning(f"Failed to log access to Redis: {e}")

        logger.info(f"Memory access: {tool_name} (session={session_id}, first={is_first})")
        return event

    def register_hook(self, event_type: str, callback: Callable):
        """Register a hook for memory access events"""
        if event_type in self._hooks:
            self._hooks[event_type].append(callback)

    def _trigger_hooks(self, event_type: str, event: MemoryAccessEvent):
        """Trigger registered hooks"""
        for hook in self._hooks.get(event_type, []):
            try:
                hook(event)
            except Exception as e:
                logger.warning(f"Hook error ({event_type}): {e}")

    def get_access_stats(self, session_id: str = None) -> Dict[str, Any]:
        """Get access statistics for session"""
        session_id = session_id or self.get_session_id()
        session_events = [e for e in self._access_log if e.session_id == session_id]

        return {
            'session_id': session_id,
            'total_accesses': len(session_events),
            'by_tool': self._count_by_tool(session_events),
            'first_access_at': session_events[0].timestamp if session_events else None
        }

    def _count_by_tool(self, events: List[MemoryAccessEvent]) -> Dict[str, int]:
        counts = {}
        for e in events:
            counts[e.tool_name] = counts.get(e.tool_name, 0) + 1
        return counts


class MemoryFormatEnhancer:
    """
    Enhances memory responses with format metadata.
    Handles format versioning and migration hints.
    """

    def __init__(self, access_tracker: MemoryAccessTracker = None):
        self.tracker = access_tracker or MemoryAccessTracker()

    def detect_legacy_format(self, content: str) -> bool:
        """Detect if content is in old verbose format (v1)"""
        if not content:
            return False

        # Heuristics for verbose format detection
        verbose_indicators = [
            len(content.split()) > 50,  # Long prose
            content.count('.') > 3,     # Multiple sentences
            'should' in content.lower(),
            'when you' in content.lower(),
            'in order to' in content.lower(),
            content.count(',') > 5,     # Complex sentences
        ]

        # Compact format indicators
        compact_indicators = [
            '→' in content,
            '|' in content and ':' in content,
            content.startswith('{') or content.startswith('['),
            '::' in content,
            content.count('\n') > content.count('. '),  # More structure than prose
        ]

        verbose_score = sum(verbose_indicators)
        compact_score = sum(compact_indicators)

        return verbose_score > compact_score and verbose_score >= 2

    def get_compression_hint(self, content: str) -> str:
        """Generate a compression hint for legacy content"""
        if not self.detect_legacy_format(content):
            return ""

        word_count = len(content.split())
        if word_count > 100:
            return "Legacy v1 format detected (~{} words). Consider compressing to table/YAML.".format(word_count)
        elif word_count > 50:
            return "Verbose content. Use symbols: → | :: for compression."
        return "Consider: key:value or YAML format"

    def enhance_response(self,
                         tool_name: str,
                         data: Any,
                         arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance a memory response with format metadata.

        Returns wrapped response with _haivemind_meta header.
        """
        # Record access
        event = self.tracker.record_access(tool_name, arguments)

        # Build metadata
        meta = MemoryFormatMeta(
            format_version=FORMAT_VERSION,
            access_logged=True,
            is_first_session_access=event.is_first_access
        )

        # Add format guide on first access
        if event.is_first_access:
            meta.format_guide = FORMAT_GUIDE_COMPACT

        # Detect legacy content in responses
        if isinstance(data, dict) and 'content' in data:
            content = data.get('content', '')
            if self.detect_legacy_format(content):
                meta.legacy_content_detected = True
                meta.compression_hint = self.get_compression_hint(content)
        elif isinstance(data, list):
            # Check memories in search results
            legacy_count = sum(1 for m in data if isinstance(m, dict)
                             and self.detect_legacy_format(m.get('content', '')))
            if legacy_count > 0:
                meta.legacy_content_detected = True
                meta.compression_hint = f"{legacy_count} memories in v1 format. Compress when updating."

        return {
            "_haivemind_meta": meta.to_dict(),
            "data": data
        }

    def enhance_store_response(self, memory_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance store_memory response"""
        event = self.tracker.record_access('store_memory', arguments)

        response = {
            "_haivemind_meta": {
                "format_version": FORMAT_VERSION,
                "stored_as_version": FORMAT_VERSION,
                "access_logged": True,
            },
            "memory_id": memory_id,
            "message": f"Memory stored (format: {FORMAT_VERSION})"
        }

        # On first access, include format guide
        if event.is_first_access:
            response["_haivemind_meta"]["format_guide"] = FORMAT_GUIDE_COMPACT

        return response


def add_format_version_to_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Add format version to memory metadata before storage"""
    metadata = metadata.copy()
    metadata['format_version'] = FORMAT_VERSION
    metadata['stored_at_version'] = FORMAT_VERSION
    return metadata


def wrap_memory_response(data: Any, include_guide: bool = False) -> str:
    """
    Wrap memory data with format metadata for JSON response.

    Args:
        data: The memory data to wrap
        include_guide: Whether to include the format guide (first access)

    Returns:
        JSON string with metadata header
    """
    wrapper = {
        "_fmt": FORMAT_VERSION,  # Compact version indicator
    }

    if include_guide:
        wrapper["_guide"] = FORMAT_GUIDE_MINIMAL

    wrapper["data"] = data

    return json.dumps(wrapper, indent=2)


# Singleton instances for global access
_access_tracker: Optional[MemoryAccessTracker] = None
_format_enhancer: Optional[MemoryFormatEnhancer] = None


def get_access_tracker(redis_client=None) -> MemoryAccessTracker:
    """Get or create the global access tracker"""
    global _access_tracker
    if _access_tracker is None:
        _access_tracker = MemoryAccessTracker(redis_client)
    return _access_tracker


def get_format_enhancer(redis_client=None) -> MemoryFormatEnhancer:
    """Get or create the global format enhancer"""
    global _format_enhancer
    if _format_enhancer is None:
        tracker = get_access_tracker(redis_client)
        _format_enhancer = MemoryFormatEnhancer(tracker)
    return _format_enhancer


# Example usage and testing
if __name__ == "__main__":
    # Test the format system
    enhancer = MemoryFormatEnhancer()

    # Simulate first access
    response = enhancer.enhance_response(
        'search_memories',
        [{"content": "When the user wants to search for something, they should first authenticate using their API key, then they can call the search endpoint with their query. The results will be returned as JSON and can be filtered by date or relevance.", "id": "test1"}],
        {"query": "test"}
    )

    print("First access response:")
    print(json.dumps(response, indent=2))

    # Simulate second access
    response2 = enhancer.enhance_response(
        'search_memories',
        [{"content": "auth(key) → search(query) → results::JSON", "id": "test2"}],
        {"query": "test2"}
    )

    print("\nSecond access response:")
    print(json.dumps(response2, indent=2))

    # Get stats
    print("\nAccess stats:")
    print(json.dumps(enhancer.tracker.get_access_stats(), indent=2))
