# hAIveMind Confidence & Weight-Based Intelligence System

**Version:** 1.0
**Date:** 2025-12-20
**Status:** Design Phase
**Related Systems:** Teams & Vaults, Memory Storage, Agent Coordination

---

## Executive Summary

Design for a multi-dimensional confidence scoring system that helps hAIveMind agents determine:
- **Reliability**: Can this information be trusted?
- **Freshness**: Is this information current or outdated?
- **Relevance**: How applicable is this to my current context?
- **Consensus**: Do other agents agree with this?
- **Accuracy**: Has acting on this information led to success or errors?

This system enables agents to build a better "world view" and reduce mistakes by weighing information quality, not just quantity.

---

## Problem Statement

### Current Limitations

1. **All information treated equally** - A memory from 6 months ago has same weight as one from yesterday
2. **No source trust model** - Information from expert agent weighted same as novice
3. **No verification tracking** - Can't tell if info has been validated or is speculation
4. **No contradiction detection** - Conflicting memories exist without resolution
5. **No feedback loop** - System doesn't learn from successful vs failed actions
6. **No confidence scores** - LLM can't assess certainty of information
7. **No consensus mechanism** - Multiple agents can't collectively verify facts

### Real-World Scenarios

**Scenario 1: Outdated Configuration**
```
Agent finds memory: "Elasticsearch is running on port 9200"
Created: 3 months ago
Reality: Port changed to 9300 last week
Problem: Agent uses wrong port, connection fails
```

**Scenario 2: Conflicting Information**
```
Agent A: "Database backup runs at 2am daily"
Agent B: "Database backup runs at 3am daily"
Agent C: Needs to schedule maintenance - which is correct?
```

**Scenario 3: Unverified Speculation**
```
Memory: "Memory leak appears to be in Redis client"
Source: Quick hypothesis during incident
Verification: Never tested
Problem: Other agents treat this as confirmed fact
```

---

## Design Approach: Multi-Dimensional Confidence Scoring

### Core Concept

Each memory/information has a **Confidence Score** (0.0 - 1.0) calculated from multiple weighted factors:

```
Confidence Score = Σ (factor_weight × factor_score)

Factors:
- Freshness (time decay)
- Source credibility
- Verification status
- Usage success rate
- Consensus level
- Context relevance
- Update frequency
- Contradiction penalty
```

---

## Factor 1: Freshness & Time Decay

### Concept
Information decays in value over time. Recent information weighted higher than old.

### Time Decay Models

**Model A: Linear Decay**
```
freshness_score = 1.0 - (age_in_days / max_age)

Example (max_age = 365 days):
- 1 day old:   0.997 (99.7%)
- 30 days old: 0.918 (91.8%)
- 90 days old: 0.753 (75.3%)
- 180 days old: 0.507 (50.7%)
- 365 days old: 0.0 (0%)
```

**Model B: Exponential Decay (RECOMMENDED)**
```
freshness_score = e^(-λt)
where λ = decay_rate (configurable per category)

Example (λ = 0.01):
- 1 day old:   0.990 (99.0%)
- 30 days old: 0.741 (74.1%)
- 90 days old: 0.407 (40.7%)
- 180 days old: 0.165 (16.5%)
- 365 days old: 0.026 (2.6%)
```

**Model C: Category-Specific Half-Life**
```
Different categories decay at different rates:

Infrastructure configs: half-life = 30 days (changes frequently)
Runbooks:              half-life = 90 days (stable procedures)
Incidents:             half-life = 60 days (lessons learned)
Team membership:       half-life = 180 days (relatively stable)
Code documentation:    half-life = 45 days (code changes)

freshness_score = 0.5^(age / half_life)
```

### Implementation Strategy

```python
class FreshnessCalculator:
    """Calculate time-based confidence decay"""

    # Category-specific half-lives (in days)
    HALF_LIVES = {
        'infrastructure': 30,
        'incidents': 60,
        'deployments': 45,
        'monitoring': 40,
        'runbooks': 90,
        'security': 20,  # Security info needs to be very fresh
        'team_membership': 180,
        'agent_capabilities': 120,
        'conversation': 7,  # Conversations decay quickly
        'global': 60,
    }

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

        half_life = self.HALF_LIVES.get(category, 60)  # Default 60 days

        # Half-life decay: score = 0.5^(age / half_life)
        freshness_score = 0.5 ** (age_days / half_life)

        return max(0.0, min(1.0, freshness_score))
```

### Freshness Boosting Mechanisms

1. **Verification Extension**: When agent verifies info is still accurate, reset decay timer
2. **Usage Confirmation**: Each successful use extends freshness slightly
3. **Manual Refresh**: Agents can mark info as "still current"
4. **Auto-Refresh Triggers**: System prompts agents to verify old critical info

---

## Factor 2: Source Credibility & Trust

### Concept
Information from trusted, expert sources weighted higher than novice sources.

### Trust Dimensions

**A. Agent Expertise Level**
```python
EXPERTISE_LEVELS = {
    'expert': 1.0,      # Specialized agent in this domain
    'experienced': 0.8,  # Has track record in this area
    'intermediate': 0.6, # Some experience
    'novice': 0.4,       # Limited experience
    'unknown': 0.3,      # New agent, no history
}
```

**B. Agent Track Record**
```python
def calculate_agent_credibility(agent_id: str, category: str) -> float:
    """
    Calculate agent credibility based on historical accuracy

    Factors:
    - Success rate of past information
    - Number of verifications received
    - Corrections issued
    - Time in system
    """
    history = get_agent_history(agent_id, category)

    # Success rate: info that was verified correct vs wrong
    success_rate = history.verified_correct / max(1, history.total_verified)

    # Experience factor: more contributions = more trust (to a point)
    experience = min(1.0, history.contribution_count / 100)

    # Correction penalty: issuing many corrections lowers trust
    correction_penalty = history.corrections_issued * 0.05

    # Time in system bonus: longer tenure = more trust
    tenure_bonus = min(0.2, history.days_active / 365 * 0.2)

    credibility = (success_rate * 0.6 +
                   experience * 0.3 +
                   tenure_bonus * 0.1 -
                   correction_penalty)

    return max(0.0, min(1.0, credibility))
```

**C. Role-Based Trust Weights**
```python
ROLE_TRUST_WEIGHTS = {
    # Team roles
    'owner': 0.95,      # Team owner - high trust for team matters
    'admin': 0.90,      # Admin - high trust
    'member': 0.75,     # Regular member
    'readonly': 0.60,   # Observer role
    'guest': 0.50,      # Guest - lower trust

    # Agent specializations
    'orchestrator': 0.90,     # Lance-dev coordinating
    'elasticsearch_specialist': 0.95,  # Expert in ES
    'database_admin': 0.95,   # Expert in DB
    'developer': 0.80,        # General dev work
    'monitor': 0.85,          # Monitoring specialist
}
```

**D. Source Type Trust**
```python
SOURCE_TYPE_WEIGHTS = {
    'automated_metric': 1.0,     # Direct system measurement
    'verified_fact': 0.95,       # Multiple confirmations
    'expert_analysis': 0.85,     # Expert agent analysis
    'observation': 0.70,         # Agent observation
    'hypothesis': 0.40,          # Unverified theory
    'speculation': 0.20,         # Pure speculation
    'rumor': 0.10,              # Unconfirmed info
}
```

### Implementation Strategy

```python
class SourceCredibilityCalculator:
    """Calculate source-based confidence"""

    def calculate_source_score(self,
                               agent_id: str,
                               category: str,
                               source_type: str,
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
        role_weight = ROLE_TRUST_WEIGHTS.get(team_role, 0.7)

        # Get source type weight
        source_weight = SOURCE_TYPE_WEIGHTS.get(source_type, 0.5)

        # Weighted combination
        source_score = (agent_cred * 0.5 +
                       role_weight * 0.3 +
                       source_weight * 0.2)

        return max(0.0, min(1.0, source_score))
```

---

## Factor 3: Verification & Validation Status

### Concept
Information that has been verified by multiple agents/sources is more trustworthy.

### Verification Levels

```python
class VerificationStatus(Enum):
    UNVERIFIED = 0      # No verification (base score: 0.3)
    SELF_VERIFIED = 1   # Creator verified it themselves (0.5)
    PEER_VERIFIED = 2   # One other agent verified (0.7)
    MULTI_VERIFIED = 3  # 2+ agents verified (0.85)
    CONSENSUS = 4       # 5+ agents agree (0.95)
    SYSTEM_VERIFIED = 5 # Automated verification (1.0)

def verification_score(status: VerificationStatus,
                      verifier_count: int) -> float:
    """
    Calculate verification confidence score

    More verifications = higher confidence
    """
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
```

### Verification Mechanisms

**A. Explicit Verification**
```python
def verify_memory(memory_id: str,
                 verifier_id: str,
                 verification_type: str,
                 notes: Optional[str] = None):
    """
    Agent explicitly verifies a memory as accurate

    Types:
    - 'confirmed': I verified this is correct
    - 'still_valid': Old info, still accurate
    - 'partially_valid': Mostly right, some corrections
    - 'outdated': This is no longer accurate
    - 'incorrect': This was always wrong
    """
    db.execute("""
        INSERT INTO memory_verifications
        (memory_id, verifier_id, verification_type, verified_at, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (memory_id, verifier_id, verification_type,
          datetime.now(), notes))

    # Update memory confidence score
    recalculate_confidence(memory_id)
```

**B. Implicit Verification (Usage Success)**
```python
def track_memory_usage(memory_id: str,
                      agent_id: str,
                      action_taken: str,
                      outcome: str):
    """
    Track when memory is used and outcome

    Outcomes:
    - 'success': Action based on memory succeeded
    - 'failure': Action failed (memory may be wrong)
    - 'partial': Mixed results
    """
    db.execute("""
        INSERT INTO memory_usage_tracking
        (memory_id, agent_id, action_taken, outcome, tracked_at)
        VALUES (?, ?, ?, ?, ?)
    """, (memory_id, agent_id, action_taken, outcome, datetime.now()))

    # Successful usage implicitly verifies memory
    if outcome == 'success':
        # Boost confidence slightly
        increment_usage_success(memory_id)
```

**C. System Verification (Automated)**
```python
async def auto_verify_infrastructure_state():
    """
    Automatically verify infrastructure memories

    Example: Memory says "Redis running on port 6379"
    System checks: Actually connects to verify
    """
    infra_memories = get_memories(category='infrastructure',
                                  type='service_config')

    for memory in infra_memories:
        if 'port' in memory.content and 'redis' in memory.content.lower():
            # Extract claimed port
            claimed_port = extract_port(memory.content)

            # Attempt connection
            if await check_redis_connection(claimed_port):
                # System verification - highest trust
                verify_memory(memory.id,
                            verifier_id='system_auto_verify',
                            verification_type='confirmed',
                            notes='Automated connection test succeeded')
            else:
                # Mark as potentially outdated
                flag_memory_for_review(memory.id,
                                      reason='Connection test failed')
```

---

## Factor 4: Consensus & Agreement

### Concept
When multiple agents independently arrive at same information, confidence increases.

### Consensus Calculation

```python
def calculate_consensus_score(memory_id: str) -> float:
    """
    Calculate consensus score based on agreement

    Factors:
    - Number of agents making similar claims
    - Diversity of agents (different specializations agreeing)
    - Independence (agents didn't copy from each other)
    """
    # Find similar/duplicate memories
    similar = find_similar_memories(memory_id, similarity_threshold=0.85)

    if len(similar) == 0:
        return 0.5  # Neutral - single source

    # Count unique agents
    unique_agents = set([m.creator_id for m in similar])
    agent_count = len(unique_agents)

    # More agents = higher consensus (logarithmic scale)
    agent_score = min(1.0, math.log(agent_count + 1) / math.log(10))

    # Check agent diversity (different specializations)
    specializations = set([get_agent_specialization(a) for a in unique_agents])
    diversity_bonus = min(0.2, len(specializations) * 0.05)

    # Check independence (did they reference each other?)
    independence = check_independence(similar)
    independence_factor = 0.8 if independence else 0.5

    consensus_score = (agent_score + diversity_bonus) * independence_factor

    return max(0.0, min(1.0, consensus_score))
```

### Consensus Mechanisms

**A. Semantic Similarity Clustering**
```python
def find_consensus_clusters():
    """
    Group similar memories to detect consensus

    Example:
    Memory A: "Elasticsearch cluster has 5 nodes"
    Memory B: "ES cluster size is 5 nodes"
    Memory C: "We run 5 elasticsearch instances"

    -> Consensus cluster: 3 agents agree on cluster size
    """
    memories = get_recent_memories(days=30)

    # Use ChromaDB vector similarity
    clusters = []
    for memory in memories:
        similar = chroma_collection.query(
            query_embeddings=[memory.embedding],
            n_results=10,
            where={"category": memory.category}
        )

        # If 3+ similar memories, create consensus cluster
        if len(similar['ids'][0]) >= 3:
            cluster = ConsensusCluster(
                topic=extract_topic(memory),
                memories=similar['ids'][0],
                agreement_level=calculate_agreement(similar)
            )
            clusters.append(cluster)

    return clusters
```

**B. Voting Mechanism**
```python
def agent_vote_on_fact(fact_id: str,
                      agent_id: str,
                      vote: str,
                      confidence: float):
    """
    Agents vote on controversial facts

    Votes:
    - 'agree': I believe this is correct
    - 'disagree': I believe this is wrong
    - 'unsure': I don't have enough info

    Confidence: How sure agent is (0.0-1.0)
    """
    db.execute("""
        INSERT INTO fact_votes
        (fact_id, agent_id, vote, confidence, voted_at)
        VALUES (?, ?, ?, ?, ?)
    """, (fact_id, agent_id, vote, confidence, datetime.now()))

    # Recalculate consensus
    votes = get_votes(fact_id)

    # Weight votes by agent credibility
    weighted_agrees = sum([v.confidence * get_agent_credibility(v.agent_id)
                          for v in votes if v.vote == 'agree'])
    weighted_disagrees = sum([v.confidence * get_agent_credibility(v.agent_id)
                             for v in votes if v.vote == 'disagree'])

    consensus_score = weighted_agrees / (weighted_agrees + weighted_disagrees + 0.001)

    return consensus_score
```

---

## Factor 5: Contradiction Detection & Penalty

### Concept
Contradictory information lowers confidence. System must detect and resolve conflicts.

### Contradiction Detection

```python
class ContradictionDetector:
    """Detect conflicting information in memory store"""

    def detect_contradictions(self, memory: Memory) -> List[Contradiction]:
        """
        Find memories that contradict this one

        Methods:
        1. Semantic similarity with opposite sentiment
        2. Fact extraction and comparison
        3. Temporal conflicts
        """
        contradictions = []

        # Method 1: Semantic Analysis
        # Find similar topics with different conclusions
        similar = self.find_similar_topics(memory)
        for candidate in similar:
            if self.are_contradictory(memory, candidate):
                contradictions.append(
                    Contradiction(
                        memory_a=memory.id,
                        memory_b=candidate.id,
                        type='semantic',
                        severity=self.calculate_severity(memory, candidate)
                    )
                )

        # Method 2: Fact Extraction
        # "Redis on port 6379" vs "Redis on port 6380"
        facts_a = self.extract_facts(memory.content)
        for other in self.get_related_memories(memory):
            facts_b = self.extract_facts(other.content)
            conflicts = self.compare_facts(facts_a, facts_b)
            if conflicts:
                contradictions.append(
                    Contradiction(
                        memory_a=memory.id,
                        memory_b=other.id,
                        type='factual',
                        conflicts=conflicts,
                        severity='high'
                    )
                )

        return contradictions

    def are_contradictory(self, mem_a: Memory, mem_b: Memory) -> bool:
        """
        Check if two memories contradict each other

        Heuristics:
        - Same topic, different values
        - Opposite sentiment/conclusions
        - Mutually exclusive states
        """
        # Extract key entities and relationships
        entities_a = self.extract_entities(mem_a.content)
        entities_b = self.extract_entities(mem_b.content)

        # Check for same entity with different states
        for entity in entities_a:
            if entity.name in [e.name for e in entities_b]:
                entity_b = [e for e in entities_b if e.name == entity.name][0]

                # Check if states are mutually exclusive
                if self.mutually_exclusive(entity.state, entity_b.state):
                    return True

        return False

    def mutually_exclusive(self, state_a: str, state_b: str) -> bool:
        """Check if two states can't both be true"""
        exclusive_pairs = [
            ('running', 'stopped'),
            ('enabled', 'disabled'),
            ('healthy', 'degraded'),
            ('online', 'offline'),
            ('active', 'inactive'),
        ]

        state_a_lower = state_a.lower()
        state_b_lower = state_b.lower()

        for pair in exclusive_pairs:
            if (state_a_lower in pair[0] and state_b_lower in pair[1]) or \
               (state_a_lower in pair[1] and state_b_lower in pair[0]):
                return True

        return False
```

### Contradiction Resolution

```python
def resolve_contradiction(contradiction: Contradiction) -> Resolution:
    """
    Resolve conflicting information

    Resolution strategies:
    1. Temporal: Newer information supersedes older
    2. Source trust: Higher credibility source wins
    3. Consensus: Majority view wins
    4. System verification: Check ground truth
    5. Agent review: Flag for manual resolution
    """
    mem_a = get_memory(contradiction.memory_a)
    mem_b = get_memory(contradiction.memory_b)

    # Strategy 1: Clear temporal winner?
    time_diff = abs((mem_a.created_at - mem_b.created_at).days)
    if time_diff > 30:  # More than 30 days apart
        winner = mem_a if mem_a.created_at > mem_b.created_at else mem_b
        loser = mem_b if winner == mem_a else mem_a

        return Resolution(
            winner=winner.id,
            loser=loser.id,
            strategy='temporal',
            reason=f'Newer information ({winner.created_at}) supersedes older',
            action='deprecate_loser'
        )

    # Strategy 2: Clear source credibility difference?
    cred_a = get_confidence_score(mem_a.id, factor='source')
    cred_b = get_confidence_score(mem_b.id, factor='source')

    if abs(cred_a - cred_b) > 0.3:  # Significant credibility gap
        winner = mem_a if cred_a > cred_b else mem_b
        loser = mem_b if winner == mem_a else mem_a

        return Resolution(
            winner=winner.id,
            loser=loser.id,
            strategy='source_credibility',
            reason=f'Higher credibility source ({cred_a:.2f} vs {cred_b:.2f})',
            action='mark_loser_disputed'
        )

    # Strategy 3: Check consensus
    consensus_a = get_consensus_count(mem_a.id)
    consensus_b = get_consensus_count(mem_b.id)

    if consensus_a > consensus_b + 2:  # Clear consensus winner
        return Resolution(
            winner=mem_a.id,
            loser=mem_b.id,
            strategy='consensus',
            reason=f'{consensus_a} agents agree vs {consensus_b}',
            action='mark_loser_disputed'
        )

    # Strategy 4: System verification if possible
    if can_auto_verify(mem_a) or can_auto_verify(mem_b):
        verification_result = auto_verify_fact(mem_a, mem_b)
        if verification_result.conclusive:
            return Resolution(
                winner=verification_result.correct_memory_id,
                loser=verification_result.incorrect_memory_id,
                strategy='system_verification',
                reason='Automated verification determined ground truth',
                action='deprecate_loser'
            )

    # Strategy 5: Flag for agent review
    return Resolution(
        winner=None,
        loser=None,
        strategy='agent_review',
        reason='Unable to auto-resolve - requires agent judgment',
        action='flag_for_review',
        assigned_to=find_expert_agent(mem_a.category)
    )
```

### Contradiction Penalty

```python
def apply_contradiction_penalty(memory_id: str) -> float:
    """
    Lower confidence for contradicted information

    Penalty based on:
    - Number of contradictions
    - Severity of contradictions
    - Whether memory is the likely wrong one
    """
    contradictions = get_contradictions(memory_id)

    if not contradictions:
        return 1.0  # No penalty

    penalty = 0.0
    for contradiction in contradictions:
        # Determine if this memory is likely wrong
        resolution = get_resolution(contradiction.id)

        if resolution and resolution.loser == memory_id:
            # This memory was determined to be wrong
            penalty += 0.3  # Heavy penalty
        elif not resolution:
            # Unresolved contradiction
            penalty += 0.1 * contradiction.severity_score

    # Max penalty is 0.8 (minimum score of 0.2)
    penalty = min(0.8, penalty)

    return 1.0 - penalty
```

---

## Factor 6: Usage Success Rate

### Concept
Information that leads to successful actions is more reliable than info that causes errors.

### Success Tracking

```python
class UsageSuccessTracker:
    """Track outcomes when memories are used"""

    def track_usage(self,
                   memory_id: str,
                   agent_id: str,
                   action: str,
                   outcome: str,
                   details: Optional[Dict] = None):
        """
        Record memory usage and outcome

        Outcomes:
        - 'success': Action worked as expected
        - 'failure': Action failed (memory may be wrong/outdated)
        - 'partial': Mixed results
        - 'error': Action caused error
        """
        db.execute("""
            INSERT INTO memory_usage_outcomes
            (memory_id, agent_id, action, outcome, details, tracked_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (memory_id, agent_id, action, outcome,
              json.dumps(details), datetime.now()))

        # Update success rate
        self.recalculate_success_rate(memory_id)

    def calculate_success_rate(self, memory_id: str) -> float:
        """
        Calculate success rate for this memory

        Returns: 0.0 (always fails) to 1.0 (always succeeds)
        """
        outcomes = db.execute("""
            SELECT outcome, COUNT(*) as count
            FROM memory_usage_outcomes
            WHERE memory_id = ?
            AND tracked_at > datetime('now', '-90 days')
            GROUP BY outcome
        """, (memory_id,)).fetchall()

        if not outcomes:
            return 0.5  # No data - neutral score

        total = sum([o['count'] for o in outcomes])
        successes = sum([o['count'] for o in outcomes
                        if o['outcome'] == 'success'])
        partial = sum([o['count'] for o in outcomes
                      if o['outcome'] == 'partial']) * 0.5

        success_rate = (successes + partial) / total

        # Confidence boost for high sample size
        if total >= 10:
            # Well-tested information
            return success_rate
        else:
            # Low sample size - regress toward mean (0.5)
            confidence = total / 10  # 0.0 to 1.0
            return success_rate * confidence + 0.5 * (1 - confidence)
```

### Automatic Error Detection

```python
async def detect_memory_errors():
    """
    Automatically detect when memories lead to errors

    Example:
    Agent uses memory: "API endpoint is /api/v1/users"
    Action: Makes HTTP request
    Result: 404 Not Found
    System: Flags memory as potentially outdated
    """
    recent_errors = get_recent_errors(hours=24)

    for error in recent_errors:
        # Extract which memories were used before error
        context = get_agent_context(error.agent_id, error.timestamp)

        for memory_id in context.memories_accessed:
            # Record failed usage
            track_usage(
                memory_id=memory_id,
                agent_id=error.agent_id,
                action=error.action,
                outcome='failure',
                details={'error': error.message}
            )

            # If multiple failures, flag for review
            failure_rate = calculate_failure_rate(memory_id, days=7)
            if failure_rate > 0.5:  # More than 50% failures
                flag_memory(
                    memory_id=memory_id,
                    reason='high_failure_rate',
                    severity='high',
                    message=f'This memory has {failure_rate:.0%} failure rate in last 7 days'
                )
```

---

## Factor 7: Context Relevance

### Concept
Information relevance depends on current context (project, team, mode, task).

### Relevance Calculation

```python
class ContextRelevanceCalculator:
    """Calculate how relevant information is to current context"""

    def calculate_relevance(self,
                           memory: Memory,
                           current_context: Context) -> float:
        """
        Calculate context relevance score

        Factors:
        - Project match
        - Team match
        - Category relevance
        - Task alignment
        - Machine/system relevance
        """
        score = 0.0
        weights_sum = 0.0

        # Project relevance (weight: 0.3)
        if current_context.project_id:
            if memory.project_id == current_context.project_id:
                score += 1.0 * 0.3
            elif memory.project_id in current_context.related_projects:
                score += 0.6 * 0.3
            weights_sum += 0.3

        # Team relevance (weight: 0.25)
        if current_context.team_id:
            if memory.team_id == current_context.team_id:
                score += 1.0 * 0.25
            elif memory.shared_with and current_context.team_id in memory.shared_with:
                score += 0.8 * 0.25
            weights_sum += 0.25

        # Category relevance (weight: 0.2)
        if current_context.task_category:
            if memory.category == current_context.task_category:
                score += 1.0 * 0.2
            elif memory.category in RELATED_CATEGORIES.get(current_context.task_category, []):
                score += 0.5 * 0.2
            weights_sum += 0.2

        # Machine/system relevance (weight: 0.15)
        if current_context.target_systems:
            memory_systems = self.extract_systems(memory.content)
            overlap = len(set(memory_systems) & set(current_context.target_systems))
            if overlap > 0:
                score += min(1.0, overlap / len(current_context.target_systems)) * 0.15
            weights_sum += 0.15

        # Semantic task alignment (weight: 0.1)
        if current_context.task_description:
            semantic_similarity = self.calculate_semantic_similarity(
                memory.content,
                current_context.task_description
            )
            score += semantic_similarity * 0.1
            weights_sum += 0.1

        # Normalize by weights used
        if weights_sum > 0:
            return score / weights_sum
        else:
            return 0.5  # No context available - neutral
```

---

## Composite Confidence Score

### Final Calculation

```python
class ConfidenceScoreCalculator:
    """Calculate final confidence score from all factors"""

    # Factor weights (must sum to 1.0)
    WEIGHTS = {
        'freshness': 0.20,           # How recent/current
        'source_credibility': 0.20,  # Who said it
        'verification': 0.15,         # Has it been verified
        'consensus': 0.15,           # Do others agree
        'contradiction': 0.10,       # Any conflicts
        'success_rate': 0.10,        # Usage outcomes
        'context_relevance': 0.10,   # Relevance to task
    }

    def calculate_confidence(self,
                            memory: Memory,
                            context: Optional[Context] = None) -> ConfidenceScore:
        """
        Calculate comprehensive confidence score

        Returns detailed breakdown and final score
        """
        scores = {}

        # Factor 1: Freshness
        freshness_calc = FreshnessCalculator()
        scores['freshness'] = freshness_calc.calculate_freshness(
            created_at=memory.created_at,
            category=memory.category,
            last_verified_at=memory.last_verified_at
        )

        # Factor 2: Source Credibility
        source_calc = SourceCredibilityCalculator()
        scores['source_credibility'] = source_calc.calculate_source_score(
            agent_id=memory.creator_id,
            category=memory.category,
            source_type=memory.source_type,
            team_role=memory.creator_role
        )

        # Factor 3: Verification
        scores['verification'] = verification_score(
            status=memory.verification_status,
            verifier_count=len(memory.verifications)
        )

        # Factor 4: Consensus
        scores['consensus'] = calculate_consensus_score(memory.id)

        # Factor 5: Contradiction Penalty
        scores['contradiction'] = apply_contradiction_penalty(memory.id)

        # Factor 6: Success Rate
        success_tracker = UsageSuccessTracker()
        scores['success_rate'] = success_tracker.calculate_success_rate(memory.id)

        # Factor 7: Context Relevance (if context provided)
        if context:
            relevance_calc = ContextRelevanceCalculator()
            scores['context_relevance'] = relevance_calc.calculate_relevance(
                memory=memory,
                current_context=context
            )
        else:
            scores['context_relevance'] = 0.5  # Neutral if no context

        # Calculate weighted final score
        final_score = sum([
            scores[factor] * self.WEIGHTS[factor]
            for factor in self.WEIGHTS.keys()
        ])

        # Determine confidence level
        if final_score >= 0.85:
            level = 'very_high'
            description = 'Highly reliable information - use with confidence'
        elif final_score >= 0.70:
            level = 'high'
            description = 'Reliable information - likely accurate'
        elif final_score >= 0.55:
            level = 'medium'
            description = 'Moderately reliable - verify if critical'
        elif final_score >= 0.40:
            level = 'low'
            description = 'Low confidence - verify before use'
        else:
            level = 'very_low'
            description = 'Very low confidence - likely outdated/incorrect'

        return ConfidenceScore(
            final_score=final_score,
            level=level,
            description=description,
            factor_scores=scores,
            weights=self.WEIGHTS,
            calculated_at=datetime.now()
        )
```

---

## Database Schema Extensions

### New Tables

```sql
-- Memory confidence scores
CREATE TABLE memory_confidence (
    memory_id TEXT PRIMARY KEY,
    final_score REAL NOT NULL,
    confidence_level TEXT NOT NULL,

    -- Factor scores
    freshness_score REAL,
    source_score REAL,
    verification_score REAL,
    consensus_score REAL,
    contradiction_score REAL,
    success_rate_score REAL,
    context_relevance_score REAL,

    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (memory_id) REFERENCES memories(id)
);

-- Memory verifications
CREATE TABLE memory_verifications (
    id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    verifier_id TEXT NOT NULL,
    verification_type TEXT NOT NULL, -- confirmed, still_valid, outdated, incorrect
    confidence REAL DEFAULT 1.0,
    notes TEXT,
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (memory_id) REFERENCES memories(id)
);

-- Memory usage outcomes
CREATE TABLE memory_usage_outcomes (
    id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL, -- success, failure, partial, error
    details TEXT, -- JSON
    tracked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (memory_id) REFERENCES memories(id)
);

-- Detected contradictions
CREATE TABLE memory_contradictions (
    id TEXT PRIMARY KEY,
    memory_a_id TEXT NOT NULL,
    memory_b_id TEXT NOT NULL,
    contradiction_type TEXT NOT NULL, -- semantic, factual, temporal
    severity TEXT NOT NULL, -- low, medium, high
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_strategy TEXT,
    resolution_winner TEXT,

    FOREIGN KEY (memory_a_id) REFERENCES memories(id),
    FOREIGN KEY (memory_b_id) REFERENCES memories(id)
);

-- Agent credibility tracking
CREATE TABLE agent_credibility (
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

-- Consensus clusters
CREATE TABLE consensus_clusters (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    category TEXT,
    memory_ids TEXT NOT NULL, -- JSON array
    agent_count INTEGER,
    agreement_level REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fact votes
CREATE TABLE fact_votes (
    id TEXT PRIMARY KEY,
    fact_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    vote TEXT NOT NULL, -- agree, disagree, unsure
    confidence REAL NOT NULL,
    reasoning TEXT,
    voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(fact_id, agent_id)
);
```

---

## MCP Tools for Confidence System

### New Tools

```python
# Tool 1: Get confidence score
def get_memory_confidence(memory_id: str) -> Dict:
    """
    Get detailed confidence score breakdown for memory

    Returns:
        final_score: 0.0-1.0
        level: very_high|high|medium|low|very_low
        factor_scores: breakdown of all factors
        recommendation: how to use this information
    """

# Tool 2: Verify memory
def verify_memory(memory_id: str,
                 verification_type: str,
                 notes: Optional[str] = None) -> Dict:
    """
    Explicitly verify a memory as accurate/outdated

    Types: confirmed, still_valid, partially_valid, outdated, incorrect
    """

# Tool 3: Report usage outcome
def report_memory_usage(memory_id: str,
                       action: str,
                       outcome: str,
                       details: Optional[Dict] = None) -> Dict:
    """
    Report outcome when using memory for an action

    Outcomes: success, failure, partial, error
    """

# Tool 4: Find high-confidence info
def search_high_confidence_memories(query: str,
                                   min_confidence: float = 0.7,
                                   category: Optional[str] = None) -> List[Dict]:
    """
    Search for memories with confidence >= threshold

    Useful for finding only reliable information
    """

# Tool 5: Flag outdated info
def flag_outdated_memories(category: Optional[str] = None,
                          days_old: int = 90) -> List[Dict]:
    """
    Find memories that need verification

    Returns list of old, unverified memories
    """

# Tool 6: Resolve contradiction
def resolve_contradiction(contradiction_id: str,
                         winner_memory_id: str,
                         strategy: str,
                         reason: str) -> Dict:
    """
    Manually resolve a contradiction

    Marks one memory as correct, other as disputed
    """

# Tool 7: Vote on fact
def vote_on_fact(memory_id: str,
                vote: str,
                confidence: float,
                reasoning: Optional[str] = None) -> Dict:
    """
    Vote on whether a fact is correct

    Votes: agree, disagree, unsure
    Confidence: 0.0-1.0
    """

# Tool 8: Get agent credibility
def get_agent_credibility(agent_id: str,
                         category: Optional[str] = None) -> Dict:
    """
    Get credibility score for an agent

    Returns track record and trust level
    """
```

---

## UI Integration

### Confidence Indicators

**Visual Confidence Levels:**
```
🟢 Very High (0.85-1.0):  "Highly reliable - use with confidence"
🟡 High (0.70-0.84):      "Reliable - likely accurate"
🟠 Medium (0.55-0.69):    "Moderately reliable - verify if critical"
🔴 Low (0.40-0.54):       "Low confidence - verify before use"
⚫ Very Low (0.0-0.39):   "Very low confidence - likely outdated"
```

**Memory Display:**
```
┌─────────────────────────────────────────────────────────────┐
│ Memory: Elasticsearch cluster configuration                 │
│ Confidence: 🟢 0.87 (Very High)                             │
├─────────────────────────────────────────────────────────────┤
│ Content: Elasticsearch cluster has 5 nodes running on       │
│ elastic1-5. Primary shards: 3, Replicas: 2                 │
├─────────────────────────────────────────────────────────────┤
│ Confidence Breakdown:                                        │
│   Freshness:      🟢 0.95 (verified 2 days ago)            │
│   Source:         🟢 0.90 (elasticsearch specialist)        │
│   Verification:   🟢 0.85 (verified by 3 agents)           │
│   Consensus:      🟢 0.80 (4 agents agree)                 │
│   Contradiction:  🟢 1.00 (no conflicts)                   │
│   Success Rate:   🟢 0.92 (12/13 successful uses)          │
│   Relevance:      🟢 0.88 (highly relevant to task)        │
├─────────────────────────────────────────────────────────────┤
│ Recommendation: Use with confidence - well-verified info    │
└─────────────────────────────────────────────────────────────┘
```

---

## Smart Retrieval with Confidence

### Confidence-Aware Search

```python
def smart_search(query: str,
                context: Context,
                min_confidence: float = 0.5,
                boost_relevant: bool = True) -> List[Memory]:
    """
    Search with confidence-aware ranking

    Args:
        query: Search query
        context: Current agent context
        min_confidence: Minimum confidence threshold
        boost_relevant: Boost highly relevant results

    Returns:
        Memories ranked by: semantic_match × confidence × relevance
    """
    # Vector similarity search
    results = chroma_collection.query(
        query_texts=[query],
        n_results=50
    )

    ranked_results = []
    for memory in results:
        # Calculate confidence score
        confidence = calculate_confidence(memory, context)

        # Filter by minimum confidence
        if confidence.final_score < min_confidence:
            continue

        # Calculate relevance to context
        relevance = calculate_relevance(memory, context)

        # Composite ranking score
        semantic_score = memory.similarity_score  # From vector search

        if boost_relevant:
            rank_score = semantic_score * confidence.final_score * (1 + relevance)
        else:
            rank_score = semantic_score * confidence.final_score

        ranked_results.append({
            'memory': memory,
            'confidence': confidence,
            'relevance': relevance,
            'rank_score': rank_score
        })

    # Sort by rank score
    ranked_results.sort(key=lambda x: x['rank_score'], reverse=True)

    return ranked_results
```

---

## Confidence-Based Decision Making

### When to Trust Information

```python
class ConfidenceBasedDecisionMaker:
    """Help agents decide how to use information based on confidence"""

    def should_act_on_info(self,
                          memory: Memory,
                          action_risk: str) -> DecisionGuidance:
        """
        Determine if agent should act on this information

        Args:
            memory: The information to act on
            action_risk: low|medium|high|critical

        Returns:
            DecisionGuidance with recommendation
        """
        confidence = calculate_confidence(memory)

        # Risk-based confidence thresholds
        THRESHOLDS = {
            'low': 0.40,      # Low risk action - ok with moderate confidence
            'medium': 0.60,   # Medium risk - need good confidence
            'high': 0.75,     # High risk - need high confidence
            'critical': 0.90, # Critical action - need very high confidence
        }

        required = THRESHOLDS.get(action_risk, 0.60)

        if confidence.final_score >= required:
            return DecisionGuidance(
                should_act=True,
                confidence=confidence,
                reasoning=f"Confidence {confidence.final_score:.2f} meets threshold {required:.2f} for {action_risk} risk action",
                recommendation="Proceed with action"
            )
        elif confidence.final_score >= required - 0.1:
            # Close - suggest verification first
            return DecisionGuidance(
                should_act=False,
                confidence=confidence,
                reasoning=f"Confidence {confidence.final_score:.2f} slightly below threshold {required:.2f}",
                recommendation="Verify information before acting",
                suggested_action="verify_memory"
            )
        else:
            # Too low - find better info
            return DecisionGuidance(
                should_act=False,
                confidence=confidence,
                reasoning=f"Confidence {confidence.final_score:.2f} too low for {action_risk} risk action",
                recommendation="Find more reliable information or verify current info",
                suggested_action="search_alternatives"
            )
```

---

## Continuous Learning & Improvement

### Feedback Loops

```python
class ContinuousLearning:
    """System learns from outcomes to improve confidence scoring"""

    def learn_from_outcome(self,
                          memory_id: str,
                          predicted_confidence: float,
                          actual_outcome: str):
        """
        Adjust confidence model based on actual outcomes

        If high-confidence info led to failure, adjust weights
        If low-confidence info led to success, adjust weights
        """
        # Record outcome
        db.execute("""
            INSERT INTO confidence_predictions
            (memory_id, predicted_confidence, actual_outcome, learned_at)
            VALUES (?, ?, ?, ?)
        """, (memory_id, predicted_confidence, actual_outcome, datetime.now()))

        # Analyze prediction accuracy
        if actual_outcome == 'success' and predicted_confidence < 0.5:
            # We underestimated - this info was better than we thought
            # Investigate which factors were wrong
            self.adjust_factor_weights(memory_id, direction='increase')

        elif actual_outcome == 'failure' and predicted_confidence > 0.7:
            # We overestimated - this info was worse than we thought
            # Investigate which factors were wrong
            self.adjust_factor_weights(memory_id, direction='decrease')

    def adjust_factor_weights(self, memory_id: str, direction: str):
        """
        Adjust which factors matter most for confidence

        Use machine learning to optimize factor weights over time
        """
        # Get all predictions and outcomes
        data = db.execute("""
            SELECT memory_id, predicted_confidence, actual_outcome,
                   freshness_score, source_score, verification_score, etc.
            FROM confidence_predictions
            JOIN memory_confidence USING(memory_id)
            WHERE learned_at > datetime('now', '-90 days')
        """).fetchall()

        # Train model to predict actual_outcome from factor scores
        # Adjust weights to minimize prediction error
        # (Could use logistic regression, gradient boosting, etc.)

        optimized_weights = self.optimize_weights(data)

        # Update factor weights
        self.update_weights(optimized_weights)
```

---

## Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Add confidence database tables
- [ ] Implement freshness calculation
- [ ] Implement source credibility scoring
- [ ] Add basic confidence score calculation
- [ ] Create MCP tools for verification

### Phase 2: Verification & Consensus (Week 3-4)
- [ ] Implement verification system
- [ ] Add consensus detection
- [ ] Build contradiction detection
- [ ] Create resolution mechanisms
- [ ] Add usage tracking

### Phase 3: Advanced Features (Week 5-6)
- [ ] Context relevance calculation
- [ ] Success rate tracking
- [ ] Automated verification
- [ ] Confidence-based search
- [ ] UI integration

### Phase 4: Learning & Optimization (Week 7-8)
- [ ] Feedback loop implementation
- [ ] Weight optimization
- [ ] Performance tuning
- [ ] Documentation and training
- [ ] Testing and validation

---

## Success Metrics

### How to Measure Effectiveness

1. **Reduced Error Rate**: Actions based on high-confidence info should have lower failure rate
2. **Improved Decision Quality**: Agents make better choices with confidence scores
3. **Faster Problem Resolution**: Agents quickly identify unreliable info
4. **Higher Information Quality**: Average confidence score trends upward over time
5. **Better Coordination**: Agents converge on consensus faster
6. **Fewer Contradictions**: System detects and resolves conflicts automatically

### Target Metrics (6 months)
- 90% of high-confidence (>0.8) info leads to successful actions
- 50% reduction in actions based on outdated info
- 80% of contradictions auto-resolved within 24 hours
- Average memory confidence score > 0.65
- Agent error rate decreased by 40%

---

## Open Questions for Discussion

1. **Factor Weights**: Should factor weights be configurable per deployment? Per category?
2. **Decay Rates**: Are category-specific half-lives the right approach? Other models?
3. **Verification Requirements**: How many verifications needed for consensus? Should it vary by criticality?
4. **Contradiction Resolution**: Should system auto-resolve or always flag for review?
5. **Privacy**: How to handle confidence scores for private/sensitive info in vaults?
6. **Performance**: How to efficiently calculate confidence for large-scale searches?
7. **UI/UX**: How prominently should confidence scores be displayed to users?
8. **Learning**: Should the system auto-adjust weights, or require manual tuning?

---

## Next Steps

1. **Review & Feedback**: Team review of design approach
2. **Prototype**: Build minimal prototype of core scoring system
3. **Test**: Validate with real hAIveMind data
4. **Iterate**: Adjust based on findings
5. **Implement**: Full implementation following roadmap
6. **Monitor**: Track success metrics and optimize

---

*This is a living document. Please provide feedback and suggestions.*
