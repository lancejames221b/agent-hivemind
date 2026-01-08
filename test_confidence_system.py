#!/usr/bin/env python3
"""
Confidence System - Comprehensive Smoke Test

Tests all aspects of the confidence scoring system.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from confidence_system import (
    ConfidenceSystem,
    Context,
    ConfidenceLevel,
    FreshnessCalculator,
    SourceCredibilityCalculator,
)


def print_header(title: str):
    """Print test section header"""
    print()
    print("=" * 70)
    print(f"TEST: {title}")
    print("=" * 70)


def print_success(message: str):
    """Print success message"""
    print(f"✓ {message}")


def print_info(message: str, indent=1):
    """Print info message"""
    prefix = "  " * indent
    print(f"{prefix}- {message}")


def test_core_system():
    """Test 1: Core System Initialization"""
    print_header("Core System Initialization")

    # Clean up test database
    test_db = Path('data/test_confidence.db')
    if test_db.exists():
        test_db.unlink()

    system = ConfidenceSystem(db_path='data/test_confidence.db')
    print_success("System initialized")
    print_info(f"Database: {system.db_path}")
    print_info(f"Factor weights: {len(system.weights)} factors")

    assert system.db_path.exists(), "Database file not created"
    assert len(system.weights) == 7, "Should have 7 confidence factors"

    return system


def test_freshness_calculation(system: ConfidenceSystem):
    """Test 2: Freshness & Time Decay"""
    print_header("Freshness & Time Decay")

    calc = system.freshness_calc

    # Test recent memory (1 day old)
    recent = datetime.now() - timedelta(days=1)
    score_recent = calc.calculate_freshness(
        created_at=recent,
        category='infrastructure'
    )
    print_success(f"Recent memory (1 day): {score_recent:.3f}")
    assert score_recent > 0.95, "Recent memory should have very high freshness"

    # Test 30-day-old memory (infrastructure half-life = 30 days)
    month_old = datetime.now() - timedelta(days=30)
    score_month = calc.calculate_freshness(
        created_at=month_old,
        category='infrastructure'
    )
    print_success(f"30-day-old memory: {score_month:.3f}")
    assert 0.4 < score_month < 0.6, "30-day-old should be ~0.5 (one half-life)"

    # Test 90-day-old memory
    old = datetime.now() - timedelta(days=90)
    score_old = calc.calculate_freshness(
        created_at=old,
        category='infrastructure'
    )
    print_success(f"90-day-old memory: {score_old:.3f}")
    assert score_old < 0.2, "90-day-old should have low freshness"

    # Test verification extension
    very_old = datetime.now() - timedelta(days=180)
    verified_recently = datetime.now() - timedelta(days=2)
    score_verified = calc.calculate_freshness(
        created_at=very_old,
        category='infrastructure',
        last_verified_at=verified_recently
    )
    print_success(f"Old but recently verified: {score_verified:.3f}")
    assert score_verified > 0.9, "Verification should reset freshness clock"

    # Test category-specific half-lives
    security_score = calc.calculate_freshness(
        created_at=month_old,
        category='security'
    )
    runbook_score = calc.calculate_freshness(
        created_at=month_old,
        category='runbooks'
    )
    print_success(f"Security (20d half-life): {security_score:.3f}")
    print_success(f"Runbooks (90d half-life): {runbook_score:.3f}")
    assert security_score < runbook_score, "Security should decay faster"

    print_info("✓ All freshness calculations working correctly", indent=0)


def test_verification_system(system: ConfidenceSystem):
    """Test 3: Verification System"""
    print_header("Verification System")

    memory_id = "test_mem_001"

    # Initial state: unverified
    score = system.verification_calc.calculate_verification_score(memory_id)
    print_success(f"Unverified memory score: {score:.2f}")
    assert score == 0.3, "Unverified should be 0.3"

    # Add peer verification
    system.verify_memory(
        memory_id=memory_id,
        verifier_id="agent_001",
        verification_type="confirmed",
        notes="Tested and verified"
    )
    score = system.verification_calc.calculate_verification_score(memory_id)
    print_success(f"Peer-verified score: {score:.2f}")
    assert score == 0.7, "Peer-verified should be 0.7"

    # Add second verifier
    system.verify_memory(
        memory_id=memory_id,
        verifier_id="agent_002",
        verification_type="confirmed"
    )
    score = system.verification_calc.calculate_verification_score(memory_id)
    print_success(f"Multi-verified score: {score:.2f}")
    assert score >= 0.85, "Multi-verified should be >= 0.85"

    # Add system verification
    system.verify_memory(
        memory_id=memory_id,
        verifier_id="system_auto_verify",
        verification_type="confirmed",
        notes="Automated test passed"
    )
    score = system.verification_calc.calculate_verification_score(memory_id)
    print_success(f"System-verified score: {score:.2f}")
    assert score == 1.0, "System-verified should be 1.0"

    print_info("✓ Verification system working correctly", indent=0)


def test_usage_tracking(system: ConfidenceSystem):
    """Test 4: Usage Success Tracking"""
    print_header("Usage Success Tracking")

    memory_id = "test_mem_002"

    # Track successful usages
    for i in range(10):
        system.track_memory_usage(
            memory_id=memory_id,
            agent_id="test_agent",
            action=f"Test action {i}",
            outcome="success"
        )

    # Track one failure
    system.track_memory_usage(
        memory_id=memory_id,
        agent_id="test_agent",
        action="Test action failed",
        outcome="failure"
    )

    success_rate = system.success_tracker.calculate_success_rate(memory_id)
    print_success(f"Success rate (10/11): {success_rate:.2f}")
    assert 0.85 < success_rate < 0.95, "Should be ~90% success rate"

    # Test memory with no usage data
    no_data_rate = system.success_tracker.calculate_success_rate("nonexistent")
    print_success(f"No usage data (neutral): {no_data_rate:.2f}")
    assert no_data_rate == 0.5, "No data should return neutral 0.5"

    # Test memory with low success rate
    bad_memory = "test_mem_003"
    for i in range(7):
        system.track_memory_usage(
            memory_id=bad_memory,
            agent_id="test_agent",
            action=f"Failing action {i}",
            outcome="failure"
        )
    for i in range(3):
        system.track_memory_usage(
            memory_id=bad_memory,
            agent_id="test_agent",
            action=f"Success action {i}",
            outcome="success"
        )

    bad_rate = system.success_tracker.calculate_success_rate(bad_memory)
    print_success(f"Low success rate (3/10): {bad_rate:.2f}")
    assert bad_rate < 0.4, "Should have low success rate"

    print_info("✓ Usage tracking working correctly", indent=0)


def test_contradiction_detection(system: ConfidenceSystem):
    """Test 5: Contradiction Detection & Resolution"""
    print_header("Contradiction Detection & Resolution")

    memory_a = "test_mem_004"
    memory_b = "test_mem_005"

    # Detect contradiction
    contradiction_id = system.detect_contradiction(
        memory_a_id=memory_a,
        memory_b_id=memory_b,
        contradiction_type="factual",
        severity=0.8,
        details={"conflict": "Redis port: 6379 vs 6380"}
    )
    print_success(f"Contradiction detected: {contradiction_id}")

    # Check penalty before resolution
    penalty_a = system.contradiction_calc.apply_contradiction_penalty(memory_a)
    print_success(f"Contradiction penalty: {1 - penalty_a:.2f}")
    assert penalty_a < 1.0, "Should have penalty for contradiction"

    # Resolve contradiction
    system.resolve_contradiction(
        contradiction_id=contradiction_id,
        winner_memory_id=memory_b,
        strategy="temporal",
        reason="Memory B is more recent"
    )
    print_success(f"Contradiction resolved: {memory_b} wins")

    # Check penalty after resolution
    penalty_a_after = system.contradiction_calc.apply_contradiction_penalty(memory_a)
    penalty_b_after = system.contradiction_calc.apply_contradiction_penalty(memory_b)
    print_success(f"Loser penalty: {1 - penalty_a_after:.2f}")
    print_success(f"Winner penalty: {1 - penalty_b_after:.2f}")

    print_info("✓ Contradiction system working correctly", indent=0)


def test_context_relevance(system: ConfidenceSystem):
    """Test 6: Context Relevance"""
    print_header("Context Relevance")

    # Test project match
    context = Context(
        project_id="proj_001",
        team_id="team_001",
        task_category="infrastructure"
    )

    memory_relevant = {
        "project_id": "proj_001",
        "team_id": "team_001",
        "category": "infrastructure",
        "content": "Elasticsearch cluster configuration"
    }

    score_relevant = system.relevance_calc.calculate_relevance(
        memory_data=memory_relevant,
        current_context=context
    )
    print_success(f"Highly relevant memory: {score_relevant:.2f}")
    assert score_relevant > 0.8, "Should be highly relevant"

    # Test unrelated memory
    memory_unrelated = {
        "project_id": "proj_999",
        "category": "conversation",
        "content": "Random chat message"
    }

    score_unrelated = system.relevance_calc.calculate_relevance(
        memory_data=memory_unrelated,
        current_context=context
    )
    print_success(f"Unrelated memory: {score_unrelated:.2f}")
    assert score_unrelated < 0.6, "Should have low relevance"

    print_info("✓ Context relevance working correctly", indent=0)


def test_composite_confidence(system: ConfidenceSystem):
    """Test 7: Composite Confidence Calculation"""
    print_header("Composite Confidence Calculation")

    # Create a high-quality memory
    memory_id = "test_mem_high_quality"
    memory_data = {
        "created_at": datetime.now().isoformat(),
        "category": "infrastructure",
        "creator_id": "expert_agent",
        "source_type": "verified_fact",
        "creator_role": "specialist",
        "last_verified_at": datetime.now().isoformat(),
    }

    # Add verifications
    for i in range(3):
        system.verify_memory(memory_id, f"verifier_{i}", "confirmed")

    # Add successful usages
    for i in range(15):
        system.track_memory_usage(memory_id, "test_agent",
                                 f"Action {i}", "success")

    # Calculate confidence
    context = Context(project_id="proj_001", task_category="infrastructure")
    confidence = system.calculate_confidence(memory_id, memory_data, context)

    print_success(f"Final confidence score: {confidence.final_score:.3f}")
    print_success(f"Confidence level: {confidence.level.value}")
    print_success(f"Description: {confidence.description}")

    print_info("Factor breakdown:", indent=0)
    print_info(f"Freshness: {confidence.freshness_score:.3f}")
    print_info(f"Source: {confidence.source_score:.3f}")
    print_info(f"Verification: {confidence.verification_score:.3f}")
    print_info(f"Consensus: {confidence.consensus_score:.3f}")
    print_info(f"No Contradictions: {confidence.contradiction_score:.3f}")
    print_info(f"Success Rate: {confidence.success_rate_score:.3f}")
    print_info(f"Relevance: {confidence.context_relevance_score:.3f}")

    assert confidence.final_score > 0.7, "High-quality memory should have high confidence"
    assert confidence.level in [ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH], \
        "Should be high or very high confidence"

    # Create a low-quality memory
    memory_low = "test_mem_low_quality"
    old_date = datetime.now() - timedelta(days=180)
    memory_data_low = {
        "created_at": old_date.isoformat(),
        "category": "infrastructure",
        "creator_id": "unknown_agent",
        "source_type": "speculation",
    }

    # Add failures
    for i in range(5):
        system.track_memory_usage(memory_low, "test_agent",
                                 f"Failed action {i}", "failure")

    confidence_low = system.calculate_confidence(memory_low, memory_data_low)

    print_success(f"\nLow-quality confidence: {confidence_low.final_score:.3f}")
    print_success(f"Level: {confidence_low.level.value}")

    assert confidence_low.final_score < 0.5, "Low-quality memory should have low confidence"

    print_info("✓ Composite confidence calculation working correctly", indent=0)


def test_queries(system: ConfidenceSystem):
    """Test 8: Query Functions"""
    print_header("Query Functions")

    # Get high confidence memories
    high_conf = system.get_high_confidence_memories(min_confidence=0.7)
    print_success(f"High-confidence memories: {len(high_conf)}")

    # Get outdated memories
    outdated = system.get_outdated_memories(freshness_threshold=0.3)
    print_success(f"Outdated memories: {len(outdated)}")

    # Get stored confidence
    if high_conf:
        stored = system.get_confidence_score(high_conf[0])
        print_success(f"Retrieved stored score: {stored['final_score']:.3f}")

    print_info("✓ Query functions working correctly", indent=0)


def main():
    """Run all tests"""
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "     Confidence System - Comprehensive Smoke Test".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")

    tests_run = 0
    tests_passed = 0

    tests = [
        ("Core System Initialization", test_core_system),
        ("Freshness Calculation", test_freshness_calculation),
        ("Verification System", test_verification_system),
        ("Usage Tracking", test_usage_tracking),
        ("Contradiction Detection", test_contradiction_detection),
        ("Context Relevance", test_context_relevance),
        ("Composite Confidence", test_composite_confidence),
        ("Query Functions", test_queries),
    ]

    system = None
    for name, test_func in tests:
        tests_run += 1
        try:
            if system is None:
                system = test_func()
            else:
                test_func(system)
            tests_passed += 1
        except AssertionError as e:
            print(f"\n✗ FAILED: {e}")
        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print()
    print("=" * 70)
    print("SMOKE TEST SUMMARY")
    print("=" * 70)
    print(f"✅ Passed:  {tests_passed}/{tests_run}")
    print(f"❌ Failed:  {tests_run - tests_passed}/{tests_run}")
    print("=" * 70)

    if tests_passed == tests_run:
        print()
        print("╔" + "=" * 68 + "╗")
        print("║" + " " * 68 + "║")
        print("║" + "✅ ALL TESTS PASSED! ✅".center(68) + "║")
        print("║" + " " * 68 + "║")
        print("║" + "Confidence System is fully operational!".center(68) + "║")
        print("║" + " " * 68 + "║")
        print("╚" + "=" * 68 + "╝")
        return 0
    else:
        print("\n⚠️  Some tests failed - review output above\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
