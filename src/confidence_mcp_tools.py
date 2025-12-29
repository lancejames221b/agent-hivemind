"""
Confidence System MCP Tools

MCP tool definitions and handlers for the hAIveMind confidence system.
Provides 8 tools for confidence scoring, verification, and quality tracking.

Author: ClaudeOps hAIveMind
Version: 1.0
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Import confidence system
try:
    from confidence_system import ConfidenceSystem, Context
    CONFIDENCE_AVAILABLE = True
except ImportError:
    CONFIDENCE_AVAILABLE = False
    logger.warning("Confidence system not available")


# ============================================================================
# MCP Tool Definitions
# ============================================================================

def get_confidence_tools() -> List:
    """
    Get list of Confidence System MCP tools

    Returns 8 tools:
    - get_memory_confidence: Get confidence score breakdown
    - verify_memory: Verify memory accuracy
    - report_memory_usage: Track usage outcomes
    - search_high_confidence: Find reliable information
    - flag_outdated_memories: Find stale information
    - resolve_contradiction: Resolve conflicts
    - vote_on_fact: Vote on information accuracy
    - get_agent_credibility: Check agent trust level
    """
    from mcp.types import Tool

    return [
        # Tool 1: Get Memory Confidence
        Tool(
            name="get_memory_confidence",
            description="""
Get detailed confidence score breakdown for a memory.

Returns multi-dimensional confidence analysis including:
- Final confidence score (0.0-1.0)
- Confidence level (very_high, high, medium, low, very_low)
- Factor breakdown (freshness, source, verification, consensus, etc.)
- Actionable recommendations

Use this to:
- Assess information reliability before acting
- Understand why a score is high or low
- Decide if verification is needed

Example:
  get_memory_confidence(memory_id="mem_abc123")

Returns detailed breakdown with all 7 confidence factors.
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "Memory ID to get confidence score for"
                    }
                },
                "required": ["memory_id"]
            }
        ),

        # Tool 2: Verify Memory
        Tool(
            name="verify_memory",
            description="""
Explicitly verify a memory as accurate, outdated, or incorrect.

Verification types:
- confirmed: I verified this is correct
- still_valid: Old info, but still accurate
- partially_valid: Mostly right, some corrections needed
- outdated: This is no longer accurate
- incorrect: This was always wrong

Boosts confidence for verified-correct info, lowers for outdated/incorrect.
Creates audit trail of verification actions.

Example:
  verify_memory(
    memory_id="mem_abc123",
    verification_type="confirmed",
    notes="Tested connection, works correctly"
  )

Use after:
- Testing information accuracy
- Validating old memories are still current
- Discovering outdated information
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "Memory to verify"
                    },
                    "verification_type": {
                        "type": "string",
                        "enum": ["confirmed", "still_valid", "partially_valid", "outdated", "incorrect"],
                        "description": "Type of verification"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Verifier confidence level (0.0-1.0)",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 1.0
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional verification notes"
                    }
                },
                "required": ["memory_id", "verification_type"]
            }
        ),

        # Tool 3: Report Memory Usage
        Tool(
            name="report_memory_usage",
            description="""
Report outcome when using memory for an action.

Tracks success/failure patterns to learn which information is reliable.
System automatically adjusts confidence based on usage outcomes.

Outcomes:
- success: Action based on memory worked as expected
- failure: Action failed (memory may be wrong/outdated)
- partial: Mixed results
- error: Action caused an error

Example:
  report_memory_usage(
    memory_id="mem_abc123",
    action="Connected to Redis on port 6379",
    outcome="success",
    details={"latency_ms": 12}
  )

Use to:
- Build reliability track record
- Identify problematic information
- Help system learn from outcomes
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "Memory that was used"
                    },
                    "action": {
                        "type": "string",
                        "description": "What action was taken based on this memory"
                    },
                    "outcome": {
                        "type": "string",
                        "enum": ["success", "failure", "partial", "error"],
                        "description": "Outcome of the action"
                    },
                    "details": {
                        "type": "object",
                        "description": "Optional additional details (JSON)"
                    }
                },
                "required": ["memory_id", "action", "outcome"]
            }
        ),

        # Tool 4: Search High Confidence Memories
        Tool(
            name="search_high_confidence",
            description="""
Search for memories with confidence score above threshold.

Filters search results to only show reliable information.
Useful when you need to be certain about information accuracy.

Example:
  search_high_confidence(
    query="Redis configuration",
    min_confidence=0.7,
    limit=20
  )

Use cases:
- Critical operations requiring reliable info
- Finding verified facts
- Avoiding outdated/unverified information

Confidence thresholds:
- 0.40: Low risk actions
- 0.60: Medium risk actions
- 0.75: High risk actions
- 0.90: Critical actions
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "min_confidence": {
                        "type": "number",
                        "description": "Minimum confidence threshold (0.0-1.0)",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 0.7
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 20
                    }
                },
                "required": ["query"]
            }
        ),

        # Tool 5: Flag Outdated Memories
        Tool(
            name="flag_outdated_memories",
            description="""
Find memories that need verification due to age.

Identifies information that may be stale based on:
- Time since creation
- Category-specific decay rates
- Lack of recent verification

Returns list of memories flagged for review.

Example:
  flag_outdated_memories(
    category="infrastructure",
    days_old=90
  )

Use for:
- Periodic information audits
- Identifying memories needing verification
- Maintaining information quality

Category decay rates:
- infrastructure: 30 days
- security: 20 days
- incidents: 60 days
- runbooks: 90 days
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional category to filter"
                    },
                    "freshness_threshold": {
                        "type": "number",
                        "description": "Freshness score threshold (0.0-1.0)",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 0.3
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 50
                    }
                },
                "required": []
            }
        ),

        # Tool 6: Resolve Contradiction
        Tool(
            name="resolve_contradiction",
            description="""
Manually resolve a detected contradiction between memories.

When two memories conflict, determine which is correct.
Marks winner as reliable, loser as disputed/outdated.

Resolution strategies:
- temporal: Newer information wins
- source_trust: Higher credibility source wins
- consensus: Majority view wins
- system_verification: Ground truth check
- manual_review: Human/agent judgment

Example:
  resolve_contradiction(
    contradiction_id="conflict_xyz789",
    winner_memory_id="mem_abc123",
    strategy="temporal",
    reason="Newer information from last week supersedes 3-month-old data"
  )

Use when:
- Multiple memories give conflicting info
- Need to determine correct version
- Cleaning up information quality
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "contradiction_id": {
                        "type": "string",
                        "description": "Contradiction ID to resolve"
                    },
                    "winner_memory_id": {
                        "type": "string",
                        "description": "Memory determined to be correct"
                    },
                    "strategy": {
                        "type": "string",
                        "enum": ["temporal", "source_trust", "consensus", "system_verification", "manual_review"],
                        "description": "Resolution strategy used"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Explanation for this resolution"
                    }
                },
                "required": ["contradiction_id", "winner_memory_id", "strategy", "reason"]
            }
        ),

        # Tool 7: Vote on Fact
        Tool(
            name="vote_on_fact",
            description="""
Vote on whether a memory/fact is accurate.

Consensus voting mechanism where multiple agents can agree/disagree.
Votes are weighted by agent credibility to prevent gaming.

Votes:
- agree: I believe this is correct
- disagree: I believe this is wrong
- unsure: I don't have enough information

Example:
  vote_on_fact(
    memory_id="mem_abc123",
    vote="agree",
    confidence=0.9,
    reasoning="I just verified this configuration is correct"
  )

Use for:
- Building consensus on controversial facts
- Collaborative verification
- Democratic information quality
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "Memory/fact to vote on"
                    },
                    "vote": {
                        "type": "string",
                        "enum": ["agree", "disagree", "unsure"],
                        "description": "Your vote on this fact"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "How confident you are (0.0-1.0)",
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Optional explanation for your vote"
                    }
                },
                "required": ["memory_id", "vote", "confidence"]
            }
        ),

        # Tool 8: Get Agent Credibility
        Tool(
            name="get_agent_credibility",
            description="""
Get credibility score for an agent in a specific category.

Returns track record including:
- Credibility score (0.0-1.0)
- Contribution count
- Verification success rate
- Corrections issued
- Days active

Use to:
- Assess information source reliability
- Understand agent expertise
- Weight information by source trust

Example:
  get_agent_credibility(
    agent_id="elasticsearch-specialist",
    category="infrastructure"
  )

Higher credibility = more trustworthy information from this agent.
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Agent ID to check"
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category for domain-specific credibility"
                    }
                },
                "required": ["agent_id"]
            }
        ),
    ]


# ============================================================================
# MCP Tool Handlers
# ============================================================================

class ConfidenceMCPTools:
    """Handler class for confidence MCP tools"""

    def __init__(self, system: ConfidenceSystem, default_agent_id: str):
        """
        Initialize confidence MCP tools handler

        Args:
            system: ConfidenceSystem instance
            default_agent_id: Default agent ID for operations
        """
        self.system = system
        self.default_agent_id = default_agent_id
        logger.info("📊 Confidence MCP Tools initialized")

    # ========================================================================
    # Tool Handlers
    # ========================================================================

    async def handle_get_memory_confidence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed confidence score breakdown"""
        memory_id = arguments['memory_id']

        # Get stored confidence score
        stored = self.system.get_confidence_score(memory_id)

        if not stored:
            return {
                "success": False,
                "error": f"No confidence score found for memory {memory_id}",
                "message": "Calculate confidence score first using the memory system"
            }

        return {
            "success": True,
            "memory_id": memory_id,
            "confidence": {
                "final_score": stored['final_score'],
                "level": stored['confidence_level'],
                "description": stored['description'],
                "factors": {
                    "freshness": stored['freshness_score'],
                    "source_credibility": stored['source_score'],
                    "verification": stored['verification_score'],
                    "consensus": stored['consensus_score'],
                    "no_contradictions": stored['contradiction_score'],
                    "success_rate": stored['success_rate_score'],
                    "context_relevance": stored['context_relevance_score'],
                },
                "calculated_at": stored['calculated_at']
            }
        }

    async def handle_verify_memory(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Verify memory accuracy"""
        memory_id = arguments['memory_id']
        verification_type = arguments['verification_type']
        confidence = arguments.get('confidence', 1.0)
        notes = arguments.get('notes')

        verifier_id = self.default_agent_id

        verification_id = self.system.verify_memory(
            memory_id=memory_id,
            verifier_id=verifier_id,
            verification_type=verification_type,
            confidence=confidence,
            notes=notes
        )

        return {
            "success": True,
            "verification_id": verification_id,
            "memory_id": memory_id,
            "verification_type": verification_type,
            "verifier_id": verifier_id,
            "message": f"Memory verified as '{verification_type}'"
        }

    async def handle_report_memory_usage(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Report memory usage outcome"""
        memory_id = arguments['memory_id']
        action = arguments['action']
        outcome = arguments['outcome']
        details = arguments.get('details')

        agent_id = self.default_agent_id

        usage_id = self.system.track_memory_usage(
            memory_id=memory_id,
            agent_id=agent_id,
            action=action,
            outcome=outcome,
            details=details
        )

        return {
            "success": True,
            "usage_id": usage_id,
            "memory_id": memory_id,
            "outcome": outcome,
            "message": f"Usage outcome '{outcome}' recorded for memory"
        }

    async def handle_search_high_confidence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for high-confidence memories"""
        query = arguments['query']
        min_confidence = arguments.get('min_confidence', 0.7)
        limit = arguments.get('limit', 20)

        # Get high-confidence memory IDs
        memory_ids = self.system.get_high_confidence_memories(
            min_confidence=min_confidence,
            limit=limit
        )

        return {
            "success": True,
            "query": query,
            "min_confidence": min_confidence,
            "count": len(memory_ids),
            "memory_ids": memory_ids,
            "message": f"Found {len(memory_ids)} memories with confidence >= {min_confidence}"
        }

    async def handle_flag_outdated_memories(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find outdated memories needing verification"""
        category = arguments.get('category')
        freshness_threshold = arguments.get('freshness_threshold', 0.3)
        limit = arguments.get('limit', 50)

        # Get outdated memory IDs
        memory_ids = self.system.get_outdated_memories(
            category=category,
            freshness_threshold=freshness_threshold
        )

        # Limit results
        memory_ids = memory_ids[:limit]

        return {
            "success": True,
            "category": category or "all",
            "freshness_threshold": freshness_threshold,
            "count": len(memory_ids),
            "memory_ids": memory_ids,
            "message": f"Found {len(memory_ids)} outdated memories needing verification"
        }

    async def handle_resolve_contradiction(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a contradiction"""
        contradiction_id = arguments['contradiction_id']
        winner_memory_id = arguments['winner_memory_id']
        strategy = arguments['strategy']
        reason = arguments['reason']

        success = self.system.resolve_contradiction(
            contradiction_id=contradiction_id,
            winner_memory_id=winner_memory_id,
            strategy=strategy,
            reason=reason
        )

        return {
            "success": success,
            "contradiction_id": contradiction_id,
            "winner_memory_id": winner_memory_id,
            "strategy": strategy,
            "message": f"Contradiction resolved: {winner_memory_id} determined correct"
        }

    async def handle_vote_on_fact(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Vote on fact accuracy"""
        memory_id = arguments['memory_id']
        vote = arguments['vote']
        confidence = arguments['confidence']
        reasoning = arguments.get('reasoning')

        import secrets
        vote_id = f"vote_{secrets.token_hex(8)}"
        agent_id = self.default_agent_id

        # Store vote in database
        import sqlite3
        from datetime import datetime
        with sqlite3.connect(self.system.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO fact_votes
                (id, fact_id, agent_id, vote, confidence, reasoning, voted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (vote_id, memory_id, agent_id, vote, confidence,
                  reasoning, datetime.now().isoformat()))

        return {
            "success": True,
            "vote_id": vote_id,
            "memory_id": memory_id,
            "vote": vote,
            "confidence": confidence,
            "message": f"Vote '{vote}' recorded for memory"
        }

    async def handle_get_agent_credibility(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get agent credibility score"""
        agent_id = arguments['agent_id']
        category = arguments.get('category', 'global')

        credibility_score = self.system.source_calc.calculate_agent_credibility(
            agent_id=agent_id,
            category=category
        )

        # Get detailed stats
        import sqlite3
        with sqlite3.connect(self.system.db_path) as conn:
            conn.row_factory = sqlite3.Row
            stats = conn.execute("""
                SELECT * FROM agent_credibility
                WHERE agent_id = ? AND category = ?
            """, (agent_id, category)).fetchone()

        if stats:
            return {
                "success": True,
                "agent_id": agent_id,
                "category": category,
                "credibility_score": credibility_score,
                "stats": {
                    "contribution_count": stats['contribution_count'],
                    "verified_correct": stats['verified_correct'],
                    "verified_incorrect": stats['verified_incorrect'],
                    "corrections_issued": stats['corrections_issued'],
                    "days_active": stats['days_active'],
                },
                "message": f"Agent credibility: {credibility_score:.2f}"
            }
        else:
            return {
                "success": True,
                "agent_id": agent_id,
                "category": category,
                "credibility_score": credibility_score,
                "message": "No historical data - using default credibility"
            }
