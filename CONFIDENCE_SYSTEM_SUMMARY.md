# hAIveMind Confidence System - Design Summary

## 🎯 Core Problem

**Current Issue**: All memories treated equally regardless of age, source, or accuracy
- 6-month-old info has same weight as yesterday's
- Expert agent's info weighted same as novice
- No way to know if info is outdated, verified, or contradictory

**Real Impact**: Agents make mistakes by trusting outdated/wrong information

---

## 💡 Solution: Multi-Dimensional Confidence Scoring

Each memory gets a **Confidence Score (0.0 - 1.0)** based on 7 factors:

```
┌─────────────────────────────────────────────────────────────┐
│                  CONFIDENCE SCORE = 0.87                     │
├─────────────────────────────────────────────────────────────┤
│ 🟢 Freshness (20%):         0.95  ← verified 2 days ago    │
│ 🟢 Source Credibility (20%): 0.90  ← elasticsearch expert   │
│ 🟢 Verification (15%):      0.85  ← verified by 3 agents   │
│ 🟢 Consensus (15%):         0.80  ← 4 agents agree         │
│ 🟢 No Contradictions (10%): 1.00  ← no conflicts           │
│ 🟢 Success Rate (10%):      0.92  ← 12/13 successful uses  │
│ 🟢 Context Relevant (10%):  0.88  ← highly relevant        │
└─────────────────────────────────────────────────────────────┘
Final: 🟢 Very High Confidence - Use with confidence
```

---

## 🔧 7 Key Factors Explained

### 1️⃣ Freshness & Time Decay (20%)

**Concept**: Information gets stale over time

**Implementation**: Category-specific half-lives
- Infrastructure configs: 30 days (changes frequently)
- Security vulnerabilities: 20 days (critical freshness)
- Runbooks: 90 days (stable procedures)
- Team membership: 180 days (relatively stable)

**Formula**: `freshness = 0.5^(age_in_days / half_life)`

**Example**:
```
Infrastructure memory about Redis port:
- Created: 90 days ago
- Half-life: 30 days
- Score: 0.5^(90/30) = 0.125 (12.5%)
→ Low confidence, likely outdated!
```

**Smart Extension**: When agent verifies info is still current, reset the clock

---

### 2️⃣ Source Credibility (20%)

**Concept**: Trust experts more than novices

**Tracks**:
- Agent expertise level in domain
- Historical accuracy rate
- Role/permissions (owner > admin > member)
- Track record (successful info vs corrections)

**Example**:
```
Info from "elasticsearch-specialist" agent:
- Expert in this domain: +1.0
- 95% accuracy rate: +0.95
- Track record: 50 contributions, 47 verified correct
→ High credibility: 0.90
```

**Source Types**:
- Automated metric: 1.0 (system measurement)
- Verified fact: 0.95 (multiple confirmations)
- Expert analysis: 0.85
- Observation: 0.70
- Hypothesis: 0.40
- Speculation: 0.20

---

### 3️⃣ Verification Status (15%)

**Concept**: Verified info more trustworthy than unverified

**Levels**:
- Unverified: 0.3 (just created, no validation)
- Self-verified: 0.5 (creator checked it)
- Peer-verified: 0.7 (one other agent confirmed)
- Multi-verified: 0.85 (2+ agents confirmed)
- Consensus: 0.95 (5+ agents agree)
- System-verified: 1.0 (automated check passed)

**Verification Types**:
```python
verify_memory(
    memory_id="abc123",
    verification_type="confirmed",  # or: still_valid, outdated, incorrect
    notes="I tested this and it works"
)
```

---

### 4️⃣ Consensus & Agreement (15%)

**Concept**: Multiple agents independently arriving at same info = higher confidence

**Detection**:
- Semantic similarity clustering
- Find 3+ agents saying same thing
- Check they didn't copy each other (independence)

**Example**:
```
Agent A: "Elasticsearch cluster has 5 nodes"
Agent B: "ES cluster size is 5 nodes"  
Agent C: "We run 5 elasticsearch instances"
→ Consensus cluster detected: 3 agents agree
→ Confidence boost: +0.80
```

**Voting Mechanism**:
```python
vote_on_fact(
    memory_id="abc123",
    vote="agree",  # or: disagree, unsure
    confidence=0.9,
    reasoning="I just checked, this is correct"
)
```

---

### 5️⃣ Contradiction Detection (10%)

**Concept**: Conflicting info lowers confidence

**Detection Methods**:
1. Same entity, different states: "Redis running" vs "Redis stopped"
2. Same topic, different values: "port 9200" vs "port 9300"
3. Mutually exclusive states: "enabled" vs "disabled"

**Auto-Resolution Strategies**:
1. **Temporal**: Newer info wins (if >30 days apart)
2. **Source Trust**: Higher credibility source wins
3. **Consensus**: Majority view wins
4. **System Verification**: Check ground truth
5. **Agent Review**: Flag for expert judgment

**Example**:
```
Memory A: "Redis on port 6379" (3 months old, novice agent)
Memory B: "Redis on port 6380" (1 week old, expert agent)
→ Contradiction detected!
→ Auto-resolve: Memory B wins (newer + expert)
→ Memory A marked "outdated"
```

---

### 6️⃣ Usage Success Rate (10%)

**Concept**: Info that leads to success is more reliable

**Tracking**:
```python
# When agent uses memory for action:
report_memory_usage(
    memory_id="abc123",
    action="Connected to Redis on port 6379",
    outcome="success"  # or: failure, partial, error
)

# System learns:
# - Success rate: 12/13 uses = 92% → High confidence
# - Failure rate: 7/10 uses = 70% → Flag for review
```

**Auto Error Detection**:
```
Agent uses memory: "API endpoint is /api/v1/users"
HTTP request → 404 Not Found
System automatically:
1. Records failed usage
2. Lowers confidence score
3. If >50% failures → flags for review
```

---

### 7️⃣ Context Relevance (10%)

**Concept**: Relevance depends on current context

**Factors**:
- Project match (current project vs memory project)
- Team match (your team vs memory team)
- Category alignment (task type vs memory category)
- System relevance (working on elastic1, memory about elastic1)
- Semantic similarity (task description vs memory content)

**Example**:
```
Current Task: "Optimize Elasticsearch queries"
Memory A: "Elasticsearch query optimization tips" → 0.95 relevant
Memory B: "PostgreSQL backup procedures" → 0.20 relevant
→ Memory A boosted in search results
```

---

## 🎨 Visual Confidence Levels

```
🟢 Very High (0.85-1.0):  "Highly reliable - use with confidence"
🟡 High (0.70-0.84):      "Reliable - likely accurate"  
🟠 Medium (0.55-0.69):    "Moderately reliable - verify if critical"
🔴 Low (0.40-0.54):       "Low confidence - verify before use"
⚫ Very Low (0.0-0.39):   "Very low confidence - likely outdated"
```

---

## 🤖 Smart Decision Making

### Risk-Based Action Thresholds

```python
Action Risk Level → Required Confidence
─────────────────────────────────────
Low risk           → 0.40  (e.g., viewing logs)
Medium risk        → 0.60  (e.g., restarting service)
High risk          → 0.75  (e.g., changing config)
Critical risk      → 0.90  (e.g., deleting data)
```

**Example Decision Flow**:
```
Agent wants to: Restart production Redis (HIGH RISK)
Memory says: "Redis running on port 6379"
Confidence: 0.45 (LOW)
Required: 0.75 (for high risk)

→ Decision: DON'T ACT
→ Recommendation: "Verify information before restarting production service"
→ Suggested: Search for more recent info or verify current state
```

---

## 🔄 Continuous Learning

System learns from outcomes:

```
Predicted: High confidence (0.85)
Actual: Action failed
→ System investigates: Which factors were wrong?
→ Adjusts weights: Maybe freshness matters more than we thought
→ Improves: Future predictions more accurate
```

**Feedback Loop**:
1. Agent acts on high-confidence info
2. Action succeeds/fails
3. System records outcome
4. Weights adjusted to minimize prediction error
5. Next predictions more accurate

---

## 📊 Database Schema (New Tables)

```sql
-- Confidence scores
CREATE TABLE memory_confidence (
    memory_id TEXT PRIMARY KEY,
    final_score REAL,
    freshness_score REAL,
    source_score REAL,
    verification_score REAL,
    consensus_score REAL,
    contradiction_score REAL,
    success_rate_score REAL,
    context_relevance_score REAL
);

-- Verifications
CREATE TABLE memory_verifications (
    memory_id TEXT,
    verifier_id TEXT,
    verification_type TEXT, -- confirmed, outdated, incorrect
    verified_at TIMESTAMP
);

-- Usage outcomes
CREATE TABLE memory_usage_outcomes (
    memory_id TEXT,
    agent_id TEXT,
    action TEXT,
    outcome TEXT, -- success, failure, error
    tracked_at TIMESTAMP
);

-- Contradictions
CREATE TABLE memory_contradictions (
    memory_a_id TEXT,
    memory_b_id TEXT,
    contradiction_type TEXT, -- semantic, factual, temporal
    severity TEXT,
    resolution_winner TEXT
);

-- Agent credibility
CREATE TABLE agent_credibility (
    agent_id TEXT,
    category TEXT,
    verified_correct INTEGER,
    verified_incorrect INTEGER,
    credibility_score REAL
);
```

---

## 🛠️ New MCP Tools

```python
# 1. Get confidence breakdown
get_memory_confidence(memory_id="abc123")
→ Returns: final_score, factor_scores, recommendation

# 2. Verify memory
verify_memory(
    memory_id="abc123",
    verification_type="confirmed",
    notes="Tested this, still accurate"
)

# 3. Report usage outcome
report_memory_usage(
    memory_id="abc123",
    action="Connected to database",
    outcome="success"
)

# 4. Search with confidence filter
search_high_confidence_memories(
    query="Redis configuration",
    min_confidence=0.7
)

# 5. Find outdated info
flag_outdated_memories(
    category="infrastructure",
    days_old=90
)

# 6. Resolve contradictions
resolve_contradiction(
    contradiction_id="conflict_123",
    winner_memory_id="abc123",
    strategy="temporal",
    reason="Newer information supersedes older"
)

# 7. Vote on facts
vote_on_fact(
    memory_id="abc123",
    vote="agree",
    confidence=0.9,
    reasoning="I verified this is correct"
)

# 8. Check agent credibility
get_agent_credibility(
    agent_id="elasticsearch-specialist",
    category="infrastructure"
)
```

---

## 📈 Success Metrics (6-month targets)

- ✅ 90% of high-confidence (>0.8) info leads to successful actions
- ✅ 50% reduction in actions based on outdated info
- ✅ 80% of contradictions auto-resolved within 24 hours
- ✅ Average memory confidence score > 0.65
- ✅ Agent error rate decreased by 40%

---

## 🚀 Implementation Phases

**Phase 1** (2 weeks): Core infrastructure
- Database tables
- Freshness calculation
- Source credibility
- Basic confidence scoring

**Phase 2** (2 weeks): Verification & Consensus
- Verification system
- Consensus detection
- Contradiction detection
- Resolution mechanisms

**Phase 3** (2 weeks): Advanced features
- Context relevance
- Success tracking
- Automated verification
- Confidence-aware search

**Phase 4** (2 weeks): Learning & Polish
- Feedback loops
- Weight optimization
- UI integration
- Testing

---

## ❓ Open Questions

1. **Factor Weights**: Should they be configurable per deployment?
2. **Decay Rates**: Are category-specific half-lives right? Other models?
3. **Auto-Resolution**: Should system auto-fix contradictions or always flag?
4. **Privacy**: How to handle confidence for vault secrets?
5. **Performance**: How to calculate efficiently at scale?
6. **Learning**: Auto-adjust weights or manual tuning?

---

## 💭 Example End-to-End Flow

```
1. Agent searches: "How to restart Elasticsearch"

2. System finds 3 memories:
   A. "sudo systemctl restart elasticsearch" 
      → Confidence: 🟢 0.89 (recent, verified, expert source)
   
   B. "service elasticsearch restart"
      → Confidence: 🟠 0.55 (old, unverified, works on old Ubuntu)
   
   C. "docker restart elasticsearch_container"
      → Confidence: 🔴 0.35 (wrong - we don't use Docker)

3. Agent gets results ranked by: semantic_match × confidence × relevance
   → Memory A ranked #1

4. Agent acts on Memory A:
   → Action succeeds ✅

5. System tracks outcome:
   → Increments success count for Memory A
   → Boosts confidence to 0.91
   → Increases credibility of source agent

6. Future agents benefit:
   → Memory A now has even higher confidence
   → More likely to use correct method
```

---

*See full design doc: `docs/designs/HAIVEMIND_CONFIDENCE_SYSTEM.md`*
