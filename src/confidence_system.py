"""
hAIveMind Confidence System

Multi-dimensional confidence scoring for memory reliability and quality.
Helps agents make better decisions by weighing information quality.

Author: ClaudeOps hAIveMind
Version: 1.0
"""

import sqlite3
import math
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class VerificationStatus(Enum):
    """Verification status levels"""
    UNVERIFIED = "unverified"
    SELF_VERIFIED = "self_verified"
    PEER_VERIFIED = "peer_verified"
    MULTI_VERIFIED = "multi_verified"
    CONSENSUS = "consensus"
    SYSTEM_VERIFIED = "system_verified"


class ConfidenceLevel(Enum):
    """Confidence level classifications"""
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


@dataclass
class ConfidenceScore:
    """Complete confidence score with breakdown"""
    memory_id: str
    final_score: float
    level: ConfidenceLevel
    description: str

    # Factor scores
    freshness_score: float
    source_score: float
    verification_score: float
    consensus_score: float
    contradiction_score: float
    success_rate_score: float
    context_relevance_score: float

    # Metadata
    calculated_at: str
    weights: Dict[str, float]

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        result = asdict(self)
        result['level'] = self.level.value
        return result


@dataclass
class Context:
    """Current agent context for relevance calculation"""
    project_id: Optional[str] = None
    team_id: Optional[str] = None
    task_category: Optional[str] = None
    task_description: Optional[str] = None
    target_systems: Optional[List[str]] = None
    related_projects: Optional[List[str]] = None


# ============================================================================
# Factor Weight Configuration
# ============================================================================

DEFAULT_FACTOR_WEIGHTS = {
    'freshness': 0.20,
    'source_credibility': 0.20,
    'verification': 0.15,
    'consensus': 0.15,
    'contradiction': 0.10,
    'success_rate': 0.10,
    'context_relevance': 0.10,
}


# Category-specific half-lives (in days)
CATEGORY_HALF_LIVES = {
    'infrastructure': 30,
    'incidents': 60,
    'deployments': 45,
    'monitoring': 40,
    'runbooks': 90,
    'security': 20,  # Security info needs to be very fresh
    'team_membership': 180,
    'agent': 120,
    'conversation': 7,  # Conversations decay quickly
    'project': 60,
    'global': 60,
}


# Source type trust weights
SOURCE_TYPE_WEIGHTS = {
    'automated_metric': 1.0,     # Direct system measurement
    'verified_fact': 0.95,       # Multiple confirmations
    'expert_analysis': 0.85,     # Expert agent analysis
    'observation': 0.70,         # Agent observation
    'hypothesis': 0.40,          # Unverified theory
    'speculation': 0.20,         # Pure speculation
    'rumor': 0.10,              # Unconfirmed info
}


# Role-based trust weights
ROLE_TRUST_WEIGHTS = {
    'owner': 0.95,
    'admin': 0.90,
    'member': 0.75,
    'readonly': 0.60,
    'guest': 0.50,
    'orchestrator': 0.90,
    'specialist': 0.95,
    'developer': 0.80,
    'monitor': 0.85,
}


# ============================================================================
# Database Schema
# ============================================================================

CONFIDENCE_SCHEMA = """
-- Memory confidence scores
CREATE TABLE IF NOT EXISTS memory_confidence (
    memory_id TEXT PRIMARY KEY,
    final_score REAL NOT NULL,
    confidence_level TEXT NOT NULL,
    description TEXT,

    -- Factor scores
    freshness_score REAL,
    source_score REAL,
    verification_score REAL,
    consensus_score REAL,
    contradiction_score REAL,
    success_rate_score REAL,
    context_relevance_score REAL,

    -- Metadata
    weights_json TEXT,  -- JSON of weights used
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_confidence_score ON memory_confidence(final_score);
CREATE INDEX IF NOT EXISTS idx_confidence_level ON memory_confidence(confidence_level);
CREATE INDEX IF NOT EXISTS idx_confidence_updated ON memory_confidence(updated_at);

-- Memory verifications
CREATE TABLE IF NOT EXISTS memory_verifications (
    id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    verifier_id TEXT NOT NULL,
    verification_type TEXT NOT NULL, -- confirmed, still_valid, outdated, incorrect, partially_valid
    confidence REAL DEFAULT 1.0,
    notes TEXT,
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(memory_id, verifier_id, verification_type)
);

CREATE INDEX IF NOT EXISTS idx_verifications_memory ON memory_verifications(memory_id);
CREATE INDEX IF NOT EXISTS idx_verifications_verifier ON memory_verifications(verifier_id);
CREATE INDEX IF NOT EXISTS idx_verifications_type ON memory_verifications(verification_type);

-- Memory usage outcomes
CREATE TABLE IF NOT EXISTS memory_usage_outcomes (
    id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL, -- success, failure, partial, error
    details TEXT, -- JSON
    tracked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_outcomes_memory ON memory_usage_outcomes(memory_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_agent ON memory_usage_outcomes(agent_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_outcome ON memory_usage_outcomes(outcome);
CREATE INDEX IF NOT EXISTS idx_outcomes_tracked ON memory_usage_outcomes(tracked_at);

-- Detected contradictions
CREATE TABLE IF NOT EXISTS memory_contradictions (
    id TEXT PRIMARY KEY,
    memory_a_id TEXT NOT NULL,
    memory_b_id TEXT NOT NULL,
    contradiction_type TEXT NOT NULL, -- semantic, factual, temporal
    severity REAL NOT NULL, -- 0.0-1.0
    details TEXT, -- JSON
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_strategy TEXT,
    resolution_winner TEXT,
    resolution_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_contradictions_memory_a ON memory_contradictions(memory_a_id);
CREATE INDEX IF NOT EXISTS idx_contradictions_memory_b ON memory_contradictions(memory_b_id);
CREATE INDEX IF NOT EXISTS idx_contradictions_resolved ON memory_contradictions(resolved_at);

-- Agent credibility tracking
CREATE TABLE IF NOT EXISTS agent_credibility (
    agent_id TEXT NOT NULL,
    category TEXT NOT NULL,
    contribution_count INTEGER DEFAULT 0,
    verification_count INTEGER DEFAULT 0,
    verified_correct INTEGER DEFAULT 0,
    verified_incorrect INTEGER DEFAULT 0,
    corrections_issued INTEGER DEFAULT 0,
    days_active INTEGER DEFAULT 0,
    credibility_score REAL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (agent_id, category)
);

CREATE INDEX IF NOT EXISTS idx_credibility_agent ON agent_credibility(agent_id);
CREATE INDEX IF NOT EXISTS idx_credibility_category ON agent_credibility(category);
CREATE INDEX IF NOT EXISTS idx_credibility_score ON agent_credibility(credibility_score);

-- Consensus clusters
CREATE TABLE IF NOT EXISTS consensus_clusters (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    category TEXT,
    memory_ids TEXT NOT NULL, -- JSON array
    agent_count INTEGER,
    agreement_level REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_clusters_topic ON consensus_clusters(topic);
CREATE INDEX IF NOT EXISTS idx_clusters_category ON consensus_clusters(category);
CREATE INDEX IF NOT EXISTS idx_clusters_agreement ON consensus_clusters(agreement_level);

-- Fact votes
CREATE TABLE IF NOT EXISTS fact_votes (
    id TEXT PRIMARY KEY,
    fact_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    vote TEXT NOT NULL, -- agree, disagree, unsure
    confidence REAL NOT NULL,
    reasoning TEXT,
    voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(fact_id, agent_id)
);

CREATE INDEX IF NOT EXISTS idx_votes_fact ON fact_votes(fact_id);
CREATE INDEX IF NOT EXISTS idx_votes_agent ON fact_votes(agent_id);
CREATE INDEX IF NOT EXISTS idx_votes_vote ON fact_votes(vote);
"""


# ============================================================================
# Calculator Classes
# ============================================================================

class FreshnessCalculator:
    """Calculate time-based confidence decay"""

    def __init__(self, half_lives: Dict[str, int] = None):
        self.half_lives = half_lives or CATEGORY_HALF_LIVES

    def calculate_freshness(self,
                           created_at: datetime,
                           category: str,
                           last_verified_at: Optional[datetime] = None) -> float:
        """
        Calculate freshness score with verification boost

        Args:
            created_at: When memory was created
            category: Memory category for half-life lookup
            last_verified_at: When memory was last verified (extends freshness)

        Returns:
            Freshness score 0.0-1.0
        """
        # Use most recent date (creation or verification)
        reference_date = last_verified_at or created_at
        age_days = (datetime.now() - reference_date).days

        # Get category-specific half-life
        half_life = self.half_lives.get(category, 60)  # Default 60 days

        # Half-life decay: score = 0.5^(age / half_life)
        freshness_score = 0.5 ** (age_days / half_life)

        return max(0.0, min(1.0, freshness_score))


class SourceCredibilityCalculator:
    """Calculate source-based confidence"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def calculate_agent_credibility(self, agent_id: str, category: str) -> float:
        """
        Calculate agent credibility based on historical accuracy

        Factors:
        - Success rate of past information
        - Number of verifications received
        - Corrections issued
        - Time in system
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            result = conn.execute("""
                SELECT contribution_count, verification_count,
                       verified_correct, verified_incorrect,
                       corrections_issued, days_active
                FROM agent_credibility
                WHERE agent_id = ? AND category = ?
            """, (agent_id, category)).fetchone()

        if not result:
            return 0.5  # Neutral for unknown agents

        # Success rate: info that was verified correct vs wrong
        total_verified = max(1, result['verified_correct'] + result['verified_incorrect'])
        success_rate = result['verified_correct'] / total_verified

        # Experience factor: more contributions = more trust (to a point)
        experience = min(1.0, result['contribution_count'] / 100)

        # Correction penalty: issuing many corrections lowers trust
        correction_penalty = min(0.5, result['corrections_issued'] * 0.05)

        # Time in system bonus: longer tenure = more trust
        tenure_bonus = min(0.2, result['days_active'] / 365 * 0.2)

        credibility = (success_rate * 0.6 +
                      experience * 0.3 +
                      tenure_bonus * 0.1 -
                      correction_penalty)

        return max(0.0, min(1.0, credibility))

    def calculate_source_score(self,
                               agent_id: str,
                               category: str,
                               source_type: Optional[str] = None,
                               team_role: Optional[str] = None) -> float:
        """
        Calculate overall source credibility

        Combines:
        - Agent track record
        - Role-based trust
        - Source type reliability
        """
        # Get agent's historical credibility in this category
        agent_cred = self.calculate_agent_credibility(agent_id, category)

        # Get role-based trust weight
        role_weight = ROLE_TRUST_WEIGHTS.get(team_role, 0.7) if team_role else 0.7

        # Get source type weight
        source_weight = SOURCE_TYPE_WEIGHTS.get(source_type, 0.5) if source_type else 0.5

        # Weighted combination
        source_score = (agent_cred * 0.5 +
                       role_weight * 0.3 +
                       source_weight * 0.2)

        return max(0.0, min(1.0, source_score))


class VerificationCalculator:
    """Calculate verification-based confidence"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_verification_status(self, memory_id: str) -> Tuple[VerificationStatus, int]:
        """
        Get verification status and verifier count

        Returns:
            (status, verifier_count)
        """
        with sqlite3.connect(self.db_path) as conn:
            # Count verified confirmations
            confirmed = conn.execute("""
                SELECT COUNT(DISTINCT verifier_id) as count
                FROM memory_verifications
                WHERE memory_id = ? AND verification_type IN ('confirmed', 'still_valid')
            """, (memory_id,)).fetchone()[0]

            # Check for system verification
            system_verified = conn.execute("""
                SELECT COUNT(*) FROM memory_verifications
                WHERE memory_id = ? AND verifier_id = 'system_auto_verify'
            """, (memory_id,)).fetchone()[0]

        if system_verified > 0:
            return VerificationStatus.SYSTEM_VERIFIED, confirmed + 1
        elif confirmed >= 5:
            return VerificationStatus.CONSENSUS, confirmed
        elif confirmed >= 2:
            return VerificationStatus.MULTI_VERIFIED, confirmed
        elif confirmed == 1:
            return VerificationStatus.PEER_VERIFIED, confirmed
        else:
            return VerificationStatus.UNVERIFIED, 0

    def calculate_verification_score(self, memory_id: str) -> float:
        """
        Calculate verification confidence score

        More verifications = higher confidence
        """
        status, verifier_count = self.get_verification_status(memory_id)

        base_scores = {
            VerificationStatus.UNVERIFIED: 0.3,
            VerificationStatus.SELF_VERIFIED: 0.5,
            VerificationStatus.PEER_VERIFIED: 0.7,
            VerificationStatus.MULTI_VERIFIED: 0.85,
            VerificationStatus.CONSENSUS: 0.95,
            VerificationStatus.SYSTEM_VERIFIED: 1.0,
        }

        base = base_scores[status]

        # Bonus for additional verifiers (diminishing returns)
        if verifier_count > 0:
            bonus = min(0.2, (verifier_count - 1) * 0.05)
            return min(1.0, base + bonus)

        return base


class ConsensusCalculator:
    """Calculate consensus-based confidence"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def calculate_consensus_score(self, memory_id: str) -> float:
        """
        Calculate consensus score based on agreement

        Factors:
        - Number of agents making similar claims
        - Diversity of agents
        - Vote counts
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Check if memory is in a consensus cluster
            cluster = conn.execute("""
                SELECT agent_count, agreement_level
                FROM consensus_clusters
                WHERE memory_ids LIKE ?
            """, (f'%"{memory_id}"%',)).fetchone()

            if cluster and cluster['agent_count'] >= 3:
                # Part of consensus cluster
                return cluster['agreement_level']

            # Check fact votes
            votes = conn.execute("""
                SELECT vote, COUNT(*) as count, AVG(confidence) as avg_conf
                FROM fact_votes
                WHERE fact_id = ?
                GROUP BY vote
            """, (memory_id,)).fetchall()

        if not votes:
            return 0.5  # Neutral - no consensus data

        # Calculate weighted agreement
        agree_count = sum(v['count'] for v in votes if v['vote'] == 'agree')
        disagree_count = sum(v['count'] for v in votes if v['vote'] == 'disagree')
        total = agree_count + disagree_count

        if total == 0:
            return 0.5

        agreement_ratio = agree_count / total

        # Scale based on number of voters
        confidence_boost = min(0.3, total * 0.05)

        consensus_score = agreement_ratio * 0.7 + confidence_boost

        return max(0.0, min(1.0, consensus_score))


class ContradictionCalculator:
    """Calculate contradiction penalty"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def apply_contradiction_penalty(self, memory_id: str) -> float:
        """
        Lower confidence for contradicted information

        Penalty based on:
        - Number of contradictions
        - Severity of contradictions
        - Whether memory is the likely wrong one
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            contradictions = conn.execute("""
                SELECT severity, resolution_winner, resolved_at
                FROM memory_contradictions
                WHERE (memory_a_id = ? OR memory_b_id = ?)
                AND resolved_at IS NULL
            """, (memory_id, memory_id)).fetchall()

        if not contradictions:
            return 1.0  # No penalty

        penalty = 0.0
        for contradiction in contradictions:
            if contradiction['resolution_winner'] and \
               contradiction['resolution_winner'] != memory_id:
                # This memory was determined to be wrong
                penalty += 0.3  # Heavy penalty
            else:
                # Unresolved contradiction
                penalty += 0.1 * contradiction['severity']

        # Max penalty is 0.8 (minimum score of 0.2)
        penalty = min(0.8, penalty)

        return 1.0 - penalty


class UsageSuccessTracker:
    """Track outcomes when memories are used"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def calculate_success_rate(self, memory_id: str, days_back: int = 90) -> float:
        """
        Calculate success rate for this memory

        Returns: 0.0 (always fails) to 1.0 (always succeeds)
        """
        with sqlite3.connect(self.db_path) as conn:
            outcomes = conn.execute("""
                SELECT outcome, COUNT(*) as count
                FROM memory_usage_outcomes
                WHERE memory_id = ?
                AND tracked_at > datetime('now', ? || ' days')
                GROUP BY outcome
            """, (memory_id, -days_back)).fetchall()

        if not outcomes:
            return 0.5  # No data - neutral score

        total = sum([o[1] for o in outcomes])
        successes = sum([o[1] for o in outcomes if o[0] == 'success'])
        partial = sum([o[1] for o in outcomes if o[0] == 'partial']) * 0.5

        success_rate = (successes + partial) / total

        # Confidence boost for high sample size
        if total >= 10:
            # Well-tested information
            return success_rate
        else:
            # Low sample size - regress toward mean (0.5)
            confidence = total / 10  # 0.0 to 1.0
            return success_rate * confidence + 0.5 * (1 - confidence)

    def track_usage(self,
                   memory_id: str,
                   agent_id: str,
                   action: str,
                   outcome: str,
                   details: Optional[Dict] = None) -> str:
        """
        Record memory usage and outcome

        Returns: usage record ID
        """
        import secrets
        usage_id = f"usage_{secrets.token_hex(8)}"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO memory_usage_outcomes
                (id, memory_id, agent_id, action, outcome, details, tracked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (usage_id, memory_id, agent_id, action, outcome,
                  json.dumps(details) if details else None,
                  datetime.now().isoformat()))

        return usage_id


class ContextRelevanceCalculator:
    """Calculate how relevant information is to current context"""

    def calculate_relevance(self,
                           memory_data: Dict,
                           current_context: Context) -> float:
        """
        Calculate context relevance score

        Factors:
        - Project match
        - Team match
        - Category relevance
        - System/machine relevance
        """
        score = 0.0
        weights_sum = 0.0

        # Project relevance (weight: 0.3)
        if current_context.project_id:
            if memory_data.get('project_id') == current_context.project_id:
                score += 1.0 * 0.3
            elif current_context.related_projects and \
                 memory_data.get('project_id') in current_context.related_projects:
                score += 0.6 * 0.3
            weights_sum += 0.3

        # Team relevance (weight: 0.25)
        if current_context.team_id:
            if memory_data.get('team_id') == current_context.team_id:
                score += 1.0 * 0.25
            weights_sum += 0.25

        # Category relevance (weight: 0.2)
        if current_context.task_category:
            if memory_data.get('category') == current_context.task_category:
                score += 1.0 * 0.2
            weights_sum += 0.2

        # System relevance (weight: 0.15)
        if current_context.target_systems:
            memory_content = memory_data.get('content', '').lower()
            matches = sum(1 for sys in current_context.target_systems
                         if sys.lower() in memory_content)
            if matches > 0:
                score += min(1.0, matches / len(current_context.target_systems)) * 0.15
            weights_sum += 0.15

        # Normalize by weights used
        if weights_sum > 0:
            return score / weights_sum
        else:
            return 0.5  # No context available - neutral


# ============================================================================
# Main Confidence System
# ============================================================================

class ConfidenceSystem:
    """
    Main confidence scoring system for hAIveMind

    Calculates multi-dimensional confidence scores to help agents
    determine information reliability and make better decisions.
    """

    def __init__(self, db_path: str = "data/confidence.db",
                 factor_weights: Dict[str, float] = None):
        """
        Initialize confidence system

        Args:
            db_path: Path to SQLite database
            factor_weights: Custom factor weights (defaults to DEFAULT_FACTOR_WEIGHTS)
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.weights = factor_weights or DEFAULT_FACTOR_WEIGHTS

        # Initialize database
        self._init_database()

        # Initialize calculators
        self.freshness_calc = FreshnessCalculator()
        self.source_calc = SourceCredibilityCalculator(str(self.db_path))
        self.verification_calc = VerificationCalculator(str(self.db_path))
        self.consensus_calc = ConsensusCalculator(str(self.db_path))
        self.contradiction_calc = ContradictionCalculator(str(self.db_path))
        self.success_tracker = UsageSuccessTracker(str(self.db_path))
        self.relevance_calc = ContextRelevanceCalculator()

        logger.info(f"✅ Confidence System initialized: {self.db_path}")

    def _init_database(self):
        """Initialize SQLite database with schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(CONFIDENCE_SCHEMA)

    # ========================================================================
    # Core Confidence Calculation
    # ========================================================================

    def calculate_confidence(self,
                            memory_id: str,
                            memory_data: Dict,
                            context: Optional[Context] = None) -> ConfidenceScore:
        """
        Calculate comprehensive confidence score

        Args:
            memory_id: Memory identifier
            memory_data: Memory metadata (created_at, category, creator_id, etc.)
            context: Current agent context for relevance calculation

        Returns:
            ConfidenceScore with detailed breakdown
        """
        scores = {}

        # Factor 1: Freshness
        created_at = datetime.fromisoformat(memory_data['created_at'])
        last_verified = memory_data.get('last_verified_at')
        if last_verified:
            last_verified = datetime.fromisoformat(last_verified)

        scores['freshness'] = self.freshness_calc.calculate_freshness(
            created_at=created_at,
            category=memory_data.get('category', 'global'),
            last_verified_at=last_verified
        )

        # Factor 2: Source Credibility
        scores['source_credibility'] = self.source_calc.calculate_source_score(
            agent_id=memory_data.get('creator_id', 'unknown'),
            category=memory_data.get('category', 'global'),
            source_type=memory_data.get('source_type'),
            team_role=memory_data.get('creator_role')
        )

        # Factor 3: Verification
        scores['verification'] = self.verification_calc.calculate_verification_score(
            memory_id=memory_id
        )

        # Factor 4: Consensus
        scores['consensus'] = self.consensus_calc.calculate_consensus_score(
            memory_id=memory_id
        )

        # Factor 5: Contradiction Penalty
        scores['contradiction'] = self.contradiction_calc.apply_contradiction_penalty(
            memory_id=memory_id
        )

        # Factor 6: Success Rate
        scores['success_rate'] = self.success_tracker.calculate_success_rate(
            memory_id=memory_id
        )

        # Factor 7: Context Relevance
        if context:
            scores['context_relevance'] = self.relevance_calc.calculate_relevance(
                memory_data=memory_data,
                current_context=context
            )
        else:
            scores['context_relevance'] = 0.5  # Neutral if no context

        # Calculate weighted final score
        final_score = sum([
            scores[factor] * self.weights[factor]
            for factor in self.weights.keys()
        ])

        # Determine confidence level
        if final_score >= 0.85:
            level = ConfidenceLevel.VERY_HIGH
            description = 'Highly reliable information - use with confidence'
        elif final_score >= 0.70:
            level = ConfidenceLevel.HIGH
            description = 'Reliable information - likely accurate'
        elif final_score >= 0.55:
            level = ConfidenceLevel.MEDIUM
            description = 'Moderately reliable - verify if critical'
        elif final_score >= 0.40:
            level = ConfidenceLevel.LOW
            description = 'Low confidence - verify before use'
        else:
            level = ConfidenceLevel.VERY_LOW
            description = 'Very low confidence - likely outdated/incorrect'

        confidence = ConfidenceScore(
            memory_id=memory_id,
            final_score=final_score,
            level=level,
            description=description,
            freshness_score=scores['freshness'],
            source_score=scores['source_credibility'],
            verification_score=scores['verification'],
            consensus_score=scores['consensus'],
            contradiction_score=scores['contradiction'],
            success_rate_score=scores['success_rate'],
            context_relevance_score=scores['context_relevance'],
            calculated_at=datetime.now().isoformat(),
            weights=self.weights
        )

        # Store in database
        self._store_confidence_score(confidence)

        return confidence

    def _store_confidence_score(self, score: ConfidenceScore):
        """Store confidence score in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memory_confidence
                (memory_id, final_score, confidence_level, description,
                 freshness_score, source_score, verification_score,
                 consensus_score, contradiction_score, success_rate_score,
                 context_relevance_score, weights_json, calculated_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                score.memory_id,
                score.final_score,
                score.level.value,
                score.description,
                score.freshness_score,
                score.source_score,
                score.verification_score,
                score.consensus_score,
                score.contradiction_score,
                score.success_rate_score,
                score.context_relevance_score,
                json.dumps(score.weights),
                score.calculated_at,
                datetime.now().isoformat()
            ))

    # ========================================================================
    # Verification Methods
    # ========================================================================

    def verify_memory(self,
                     memory_id: str,
                     verifier_id: str,
                     verification_type: str = "confirmed",
                     confidence: float = 1.0,
                     notes: Optional[str] = None) -> str:
        """
        Explicitly verify a memory as accurate/outdated

        Args:
            memory_id: Memory to verify
            verifier_id: Agent doing verification
            verification_type: confirmed, still_valid, outdated, incorrect, partially_valid
            confidence: Verifier's confidence (0.0-1.0)
            notes: Optional notes

        Returns:
            Verification ID
        """
        import secrets
        verification_id = f"verify_{secrets.token_hex(8)}"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memory_verifications
                (id, memory_id, verifier_id, verification_type, confidence, notes, verified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (verification_id, memory_id, verifier_id, verification_type,
                  confidence, notes, datetime.now().isoformat()))

        logger.info(f"✓ Memory {memory_id} verified as '{verification_type}' by {verifier_id}")
        return verification_id

    # ========================================================================
    # Usage Tracking
    # ========================================================================

    def track_memory_usage(self,
                          memory_id: str,
                          agent_id: str,
                          action: str,
                          outcome: str,
                          details: Optional[Dict] = None) -> str:
        """
        Record memory usage and outcome

        Args:
            memory_id: Memory that was used
            agent_id: Agent that used it
            action: What action was taken
            outcome: success, failure, partial, error
            details: Additional details

        Returns:
            Usage record ID
        """
        return self.success_tracker.track_usage(
            memory_id, agent_id, action, outcome, details
        )

    # ========================================================================
    # Contradiction Detection
    # ========================================================================

    def detect_contradiction(self,
                            memory_a_id: str,
                            memory_b_id: str,
                            contradiction_type: str,
                            severity: float,
                            details: Optional[Dict] = None) -> str:
        """
        Record a detected contradiction

        Args:
            memory_a_id: First memory
            memory_b_id: Second memory
            contradiction_type: semantic, factual, temporal
            severity: 0.0-1.0
            details: Additional details

        Returns:
            Contradiction ID
        """
        import secrets
        contradiction_id = f"conflict_{secrets.token_hex(8)}"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO memory_contradictions
                (id, memory_a_id, memory_b_id, contradiction_type, severity, details, detected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (contradiction_id, memory_a_id, memory_b_id, contradiction_type,
                  severity, json.dumps(details) if details else None,
                  datetime.now().isoformat()))

        logger.warning(f"⚠️ Contradiction detected: {memory_a_id} vs {memory_b_id}")
        return contradiction_id

    def resolve_contradiction(self,
                             contradiction_id: str,
                             winner_memory_id: str,
                             strategy: str,
                             reason: str) -> bool:
        """
        Resolve a contradiction

        Args:
            contradiction_id: Contradiction to resolve
            winner_memory_id: Memory determined to be correct
            strategy: Resolution strategy used
            reason: Why this resolution

        Returns:
            True if successful
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE memory_contradictions
                SET resolved_at = ?,
                    resolution_strategy = ?,
                    resolution_winner = ?,
                    resolution_reason = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), strategy, winner_memory_id,
                  reason, contradiction_id))

        logger.info(f"✓ Contradiction {contradiction_id} resolved: {winner_memory_id} wins")
        return True

    # ========================================================================
    # Agent Credibility
    # ========================================================================

    def update_agent_credibility(self,
                                agent_id: str,
                                category: str,
                                verified_correct: int = 0,
                                verified_incorrect: int = 0,
                                corrections: int = 0):
        """Update agent credibility scores"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO agent_credibility
                (agent_id, category, verified_correct, verified_incorrect, corrections_issued, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id, category) DO UPDATE SET
                    verified_correct = verified_correct + excluded.verified_correct,
                    verified_incorrect = verified_incorrect + excluded.verified_incorrect,
                    corrections_issued = corrections_issued + excluded.corrections_issued,
                    updated_at = excluded.updated_at
            """, (agent_id, category, verified_correct, verified_incorrect,
                  corrections, datetime.now().isoformat()))

    # ========================================================================
    # Queries
    # ========================================================================

    def get_confidence_score(self, memory_id: str) -> Optional[Dict]:
        """Get stored confidence score"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            result = conn.execute("""
                SELECT * FROM memory_confidence WHERE memory_id = ?
            """, (memory_id,)).fetchone()

        if result:
            return dict(result)
        return None

    def get_high_confidence_memories(self,
                                    min_confidence: float = 0.7,
                                    limit: int = 100) -> List[str]:
        """Get memory IDs with high confidence scores"""
        with sqlite3.connect(self.db_path) as conn:
            results = conn.execute("""
                SELECT memory_id FROM memory_confidence
                WHERE final_score >= ?
                ORDER BY final_score DESC
                LIMIT ?
            """, (min_confidence, limit)).fetchall()

        return [r[0] for r in results]

    def get_outdated_memories(self,
                             category: Optional[str] = None,
                             freshness_threshold: float = 0.3) -> List[str]:
        """Get memories with low freshness scores"""
        with sqlite3.connect(self.db_path) as conn:
            if category:
                results = conn.execute("""
                    SELECT mc.memory_id
                    FROM memory_confidence mc
                    WHERE mc.freshness_score < ?
                """, (freshness_threshold,)).fetchall()
            else:
                results = conn.execute("""
                    SELECT memory_id FROM memory_confidence
                    WHERE freshness_score < ?
                    ORDER BY freshness_score ASC
                """, (freshness_threshold,)).fetchall()

        return [r[0] for r in results]

    # ========================================================================
    # Monitoring & Statistics
    # ========================================================================

    def get_confidence_stats(self) -> Dict[str, Any]:
        """Get comprehensive confidence statistics for monitoring"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Average confidence score
            avg_result = conn.execute("""
                SELECT AVG(final_score) as avg_score
                FROM memory_confidence
            """).fetchone()
            average_confidence = avg_result['avg_score'] or 0.5

            # Count by confidence level
            level_counts = {}
            level_results = conn.execute("""
                SELECT confidence_level, COUNT(*) as count
                FROM memory_confidence
                GROUP BY confidence_level
            """).fetchall()
            for row in level_results:
                level_counts[row['confidence_level']] = row['count']

            # High confidence count (>= 0.70)
            high_conf_result = conn.execute("""
                SELECT COUNT(*) as count
                FROM memory_confidence
                WHERE final_score >= 0.70
            """).fetchone()
            high_confidence_count = high_conf_result['count']

            # Needs verification (low freshness)
            needs_verify_result = conn.execute("""
                SELECT COUNT(*) as count
                FROM memory_confidence
                WHERE freshness_score < 0.3
            """).fetchone()
            needs_verification_count = needs_verify_result['count']

            # Recent verifications (last 24 hours)
            recent_verify_result = conn.execute("""
                SELECT COUNT(*) as count
                FROM memory_verifications
                WHERE verified_at > datetime('now', '-24 hours')
            """).fetchone()
            recent_verifications = recent_verify_result['count']

            # Total memories with confidence scores
            total_result = conn.execute("""
                SELECT COUNT(*) as count
                FROM memory_confidence
            """).fetchone()
            total_memories = total_result['count']

            # Contradictions count
            contradictions_result = conn.execute("""
                SELECT COUNT(*) as count
                FROM memory_contradictions
                WHERE resolved_at IS NULL
            """).fetchone()
            unresolved_contradictions = contradictions_result['count']

        return {
            "average_confidence": average_confidence,
            "total_memories": total_memories,
            "high_confidence_count": high_confidence_count,
            "needs_verification_count": needs_verification_count,
            "recent_verifications": recent_verifications,
            "unresolved_contradictions": unresolved_contradictions,
            "distribution": level_counts,
            "timestamp": datetime.now().isoformat()
        }

    def get_low_confidence_memories(self,
                                   threshold: float = 0.4,
                                   limit: int = 10) -> List[Dict[str, Any]]:
        """Get memories with low confidence scores for review"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            results = conn.execute("""
                SELECT memory_id, final_score, confidence_level,
                       freshness_score, source_score, verification_score,
                       calculated_at
                FROM memory_confidence
                WHERE final_score < ?
                ORDER BY final_score ASC
                LIMIT ?
            """, (threshold, limit)).fetchall()

        return [dict(row) for row in results]

    def get_confidence_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get confidence score trends over time"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Daily average confidence
            daily_avg = conn.execute("""
                SELECT DATE(calculated_at) as date, AVG(final_score) as avg_score
                FROM memory_confidence
                WHERE calculated_at > datetime('now', ? || ' days')
                GROUP BY DATE(calculated_at)
                ORDER BY date
            """, (-days,)).fetchall()

            # Verification trend
            verify_trend = conn.execute("""
                SELECT DATE(verified_at) as date, COUNT(*) as count
                FROM memory_verifications
                WHERE verified_at > datetime('now', ? || ' days')
                GROUP BY DATE(verified_at)
                ORDER BY date
            """, (-days,)).fetchall()

        return {
            "daily_average": [{"date": r['date'], "score": r['avg_score']}
                             for r in daily_avg],
            "verification_trend": [{"date": r['date'], "count": r['count']}
                                  for r in verify_trend],
            "period_days": days
        }
