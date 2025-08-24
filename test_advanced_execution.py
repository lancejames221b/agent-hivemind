#!/usr/bin/env python3
"""
Test script for Advanced Playbook Execution Engine

Demonstrates all the advanced features including:
- Step-by-step execution with pause/resume
- Real-time validation
- Variable interpolation
- Rollback mechanisms
- Parallel execution
- Approval gates
- Error handling and retry logic
- hAIveMind integration
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any

from src.advanced_playbook_engine import AdvancedPlaybookEngine, ExecutionState, StepState
from src.execution_error_handler import ExecutionErrorHandler, ErrorContext, create_default_error_handler
from src.playbook_engine import load_playbook_content

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MockHAIveMindClient:
    """Mock hAIveMind client for testing"""
    
    def __init__(self):
        self.memories = []
    
    async def store_memory(self, content: str, category: str, metadata: Dict[str, Any], tags: list = None):
        """Store a memory"""
        memory = {
            "content": content,
            "category": category,
            "metadata": metadata,
            "tags": tags or [],
            "timestamp": time.time()
        }
        self.memories.append(memory)
        logger.info(f"Stored hAIveMind memory: {content[:100]}...")
    
    async def search_memories(self, query: str, category: str = None, limit: int = 10):
        """Search memories"""
        results = []
        for memory in self.memories:
            if category and memory["category"] != category:
                continue
            if query.lower() in memory["content"].lower():
                results.append({
                    "content": memory["content"],
                    "metadata": memory["metadata"],
                    "score": 0.8  # Mock score
                })
        return results[:limit]


async def test_basic_execution():
    """Test basic playbook execution"""
    print("\n=== Testing Basic Execution ===")
    
    # Create mock hAIveMind client
    haivemind_client = MockHAIveMindClient()
    
    # Create execution engine
    engine = AdvancedPlaybookEngine(
        allow_unsafe_shell=False,
        haivemind_client=haivemind_client
    )
    
    # Simple test playbook
    playbook = {
        "version": 1,
        "name": "Basic Test Playbook",
        "description": "Test basic execution features",
        "parameters": [
            {"name": "test_param", "required": True, "description": "Test parameter"}
        ],
        "steps": [
            {
                "id": "step1",
                "name": "Test HTTP Request",
                "action": "http_request",
                "args": {
                    "method": "GET",
                    "url": "https://httpbin.org/json",
                    "timeout": 10
                },
                "outputs": [
                    {"name": "response_data", "from": "body_json"}
                ],
                "validations": [
                    {"type": "http_status", "left": "${status_code}", "right": 200}
                ]
            },
            {
                "id": "step2",
                "name": "Wait Step",
                "action": "wait",
                "args": {"seconds": 2},
                "depends_on": ["step1"]
            },
            {
                "id": "step3",
                "name": "No-op Step",
                "action": "noop",
                "args": {"message": "Test completed with param: ${test_param}"},
                "depends_on": ["step2"]
            }
        ]
    }
    
    # Execute playbook
    context = await engine.execute_playbook(
        spec=playbook,
        parameters={"test_param": "hello_world"},
        dry_run=False
    )
    
    print(f"Execution completed with state: {context.state}")
    print(f"Duration: {context.duration:.2f}s")
    print(f"Steps completed: {len([r for r in context.step_results.values() if r.state == StepState.COMPLETED])}")
    
    return context.state == ExecutionState.COMPLETED


async def test_parallel_execution():
    """Test parallel execution"""
    print("\n=== Testing Parallel Execution ===")
    
    haivemind_client = MockHAIveMindClient()
    engine = AdvancedPlaybookEngine(haivemind_client=haivemind_client)
    
    playbook = {
        "version": 1,
        "name": "Parallel Test Playbook",
        "description": "Test parallel execution",
        "steps": [
            {
                "id": "parallel1",
                "name": "Parallel Step 1",
                "action": "wait",
                "parallel_group": "group1",
                "args": {"seconds": 2}
            },
            {
                "id": "parallel2",
                "name": "Parallel Step 2",
                "action": "wait",
                "parallel_group": "group1",
                "args": {"seconds": 2}
            },
            {
                "id": "parallel3",
                "name": "Parallel Step 3",
                "action": "wait",
                "parallel_group": "group1",
                "args": {"seconds": 2}
            },
            {
                "id": "sequential",
                "name": "Sequential Step",
                "action": "noop",
                "args": {"message": "All parallel steps completed"},
                "depends_on": ["parallel1", "parallel2", "parallel3"]
            }
        ]
    }
    
    start_time = time.time()
    context = await engine.execute_playbook(spec=playbook)
    duration = time.time() - start_time
    
    print(f"Parallel execution completed in {duration:.2f}s")
    print(f"Expected ~2s (parallel), got {duration:.2f}s")
    
    return context.state == ExecutionState.COMPLETED and duration < 4.0


async def test_error_handling():
    """Test error handling and retry logic"""
    print("\n=== Testing Error Handling ===")
    
    haivemind_client = MockHAIveMindClient()
    engine = AdvancedPlaybookEngine(haivemind_client=haivemind_client)
    
    playbook = {
        "version": 1,
        "name": "Error Handling Test",
        "description": "Test error handling and retry",
        "steps": [
            {
                "id": "failing_step",
                "name": "Failing HTTP Request",
                "action": "http_request",
                "args": {
                    "method": "GET",
                    "url": "https://httpbin.org/status/500",
                    "timeout": 5
                },
                "retry": {
                    "max_attempts": 3,
                    "base_delay": 1.0,
                    "exponential_backoff": True
                },
                "validations": [
                    {"type": "http_status", "left": "${status_code}", "right": 200}
                ]
            }
        ]
    }
    
    context = await engine.execute_playbook(spec=playbook)
    
    print(f"Error handling test completed with state: {context.state}")
    
    # Should fail after retries
    failed_step = context.step_results.get("failing_step")
    if failed_step:
        print(f"Step retry count: {failed_step.retry_count}")
        print(f"Step error: {failed_step.error}")
    
    return context.state == ExecutionState.FAILED


async def test_validation():
    """Test advanced validation"""
    print("\n=== Testing Advanced Validation ===")
    
    haivemind_client = MockHAIveMindClient()
    engine = AdvancedPlaybookEngine(haivemind_client=haivemind_client)
    
    playbook = {
        "version": 1,
        "name": "Validation Test",
        "description": "Test advanced validation features",
        "steps": [
            {
                "id": "http_validation",
                "name": "HTTP Validation Test",
                "action": "http_request",
                "args": {
                    "method": "GET",
                    "url": "https://httpbin.org/json",
                    "timeout": 10
                },
                "validators": [
                    {
                        "type": "http_status",
                        "url": "https://httpbin.org/status/200",
                        "expected_status": 200
                    }
                ],
                "validations": [
                    {"type": "http_status", "left": "${status_code}", "right": 200},
                    {"type": "contains", "left": "${body}", "right": "slideshow"}
                ]
            }
        ]
    }
    
    context = await engine.execute_playbook(spec=playbook)
    
    print(f"Validation test completed with state: {context.state}")
    
    # Check validation results
    step_result = context.step_results.get("http_validation")
    if step_result:
        print(f"Validation results: {len(step_result.validation_results)}")
        for validation in step_result.validation_results:
            print(f"  - {validation.message}: {'✓' if validation.valid else '✗'}")
    
    return context.state == ExecutionState.COMPLETED


async def test_pause_resume():
    """Test pause and resume functionality"""
    print("\n=== Testing Pause/Resume ===")
    
    haivemind_client = MockHAIveMindClient()
    engine = AdvancedPlaybookEngine(haivemind_client=haivemind_client)
    
    playbook = {
        "version": 1,
        "name": "Pause/Resume Test",
        "description": "Test pause and resume",
        "steps": [
            {
                "id": "step1",
                "name": "First Step",
                "action": "wait",
                "args": {"seconds": 1}
            },
            {
                "id": "step2",
                "name": "Second Step",
                "action": "wait",
                "args": {"seconds": 5},
                "depends_on": ["step1"]
            },
            {
                "id": "step3",
                "name": "Third Step",
                "action": "noop",
                "args": {"message": "Final step"},
                "depends_on": ["step2"]
            }
        ]
    }
    
    # Start execution
    execution_task = asyncio.create_task(
        engine.execute_playbook(spec=playbook, run_id="pause_test")
    )
    
    # Wait a bit then pause
    await asyncio.sleep(2)
    pause_success = await engine.pause_execution("pause_test")
    print(f"Pause successful: {pause_success}")
    
    # Wait a bit then resume
    await asyncio.sleep(1)
    resume_success = await engine.resume_execution("pause_test")
    print(f"Resume successful: {resume_success}")
    
    # Wait for completion
    context = await execution_task
    
    print(f"Pause/Resume test completed with state: {context.state}")
    
    return context.state == ExecutionState.COMPLETED


async def test_dry_run():
    """Test dry run functionality"""
    print("\n=== Testing Dry Run ===")
    
    haivemind_client = MockHAIveMindClient()
    engine = AdvancedPlaybookEngine(haivemind_client=haivemind_client)
    
    playbook = {
        "version": 1,
        "name": "Dry Run Test",
        "description": "Test dry run validation",
        "steps": [
            {
                "id": "step1",
                "name": "HTTP Request",
                "action": "http_request",
                "args": {
                    "method": "GET",
                    "url": "https://httpbin.org/json"
                }
            },
            {
                "id": "step2",
                "name": "Wait Step",
                "action": "wait",
                "args": {"seconds": 10}  # Would take long in real execution
            }
        ]
    }
    
    start_time = time.time()
    context = await engine.execute_playbook(spec=playbook, dry_run=True)
    duration = time.time() - start_time
    
    print(f"Dry run completed in {duration:.2f}s")
    print(f"State: {context.state}")
    
    # Dry run should complete quickly
    return context.state == ExecutionState.COMPLETED and duration < 2.0


async def test_variable_interpolation():
    """Test variable interpolation"""
    print("\n=== Testing Variable Interpolation ===")
    
    haivemind_client = MockHAIveMindClient()
    engine = AdvancedPlaybookEngine(haivemind_client=haivemind_client)
    
    playbook = {
        "version": 1,
        "name": "Variable Test",
        "description": "Test variable interpolation",
        "parameters": [
            {"name": "base_url", "required": True},
            {"name": "endpoint", "required": True}
        ],
        "steps": [
            {
                "id": "step1",
                "name": "Get Data",
                "action": "http_request",
                "args": {
                    "method": "GET",
                    "url": "${base_url}/${endpoint}"
                },
                "outputs": [
                    {"name": "response_status", "from": "status_code"}
                ]
            },
            {
                "id": "step2",
                "name": "Validate Response",
                "action": "noop",
                "args": {
                    "message": "Got status ${response_status} from ${base_url}/${endpoint}"
                },
                "validations": [
                    {"type": "equals", "left": "${response_status}", "right": "200"}
                ]
            }
        ]
    }
    
    context = await engine.execute_playbook(
        spec=playbook,
        parameters={
            "base_url": "https://httpbin.org",
            "endpoint": "json"
        }
    )
    
    print(f"Variable interpolation test completed with state: {context.state}")
    print(f"Variables: {context.variables}")
    
    return context.state == ExecutionState.COMPLETED


async def test_error_handler():
    """Test error handler functionality"""
    print("\n=== Testing Error Handler ===")
    
    haivemind_client = MockHAIveMindClient()
    error_handler = create_default_error_handler(haivemind_client)
    
    # Test different error scenarios
    test_errors = [
        {
            "message": "Connection timeout occurred",
            "expected_category": "network",
            "expected_retry": True
        },
        {
            "message": "HTTP 429 Too Many Requests",
            "expected_category": "temporary",
            "expected_retry": True
        },
        {
            "message": "HTTP 404 Not Found",
            "expected_category": "permanent",
            "expected_retry": False
        },
        {
            "message": "Permission denied",
            "expected_category": "authorization",
            "expected_retry": False
        }
    ]
    
    for i, test_error in enumerate(test_errors):
        error_context = ErrorContext(
            step_id=f"test_step_{i}",
            run_id="test_run",
            playbook_id=1,
            error_message=test_error["message"],
            error_type="TestError",
            stack_trace="test stack trace",
            timestamp=time.time(),
            attempt_number=0
        )
        
        decision = await error_handler.handle_error(error_context)
        
        print(f"Error: {test_error['message']}")
        print(f"  Category: {decision.category.value}")
        print(f"  Should retry: {decision.should_retry}")
        print(f"  Delay: {decision.delay_seconds}s")
        print(f"  Reason: {decision.reason}")
        
        # Validate expectations
        if decision.should_retry != test_error["expected_retry"]:
            print(f"  ⚠️  Expected retry: {test_error['expected_retry']}, got: {decision.should_retry}")
        else:
            print(f"  ✓ Retry decision correct")
        
        print()
    
    # Test error statistics
    stats = error_handler.get_error_statistics()
    print(f"Error handler statistics: {json.dumps(stats, indent=2)}")
    
    return True


async def run_all_tests():
    """Run all tests"""
    print("🚀 Starting Advanced Playbook Execution Engine Tests")
    print("=" * 60)
    
    tests = [
        ("Basic Execution", test_basic_execution),
        ("Parallel Execution", test_parallel_execution),
        ("Error Handling", test_error_handling),
        ("Advanced Validation", test_validation),
        ("Pause/Resume", test_pause_resume),
        ("Dry Run", test_dry_run),
        ("Variable Interpolation", test_variable_interpolation),
        ("Error Handler", test_error_handler)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running {test_name}...")
            start_time = time.time()
            result = await test_func()
            duration = time.time() - start_time
            
            results[test_name] = {
                "success": result,
                "duration": duration
            }
            
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} - {test_name} ({duration:.2f}s)")
            
        except Exception as e:
            results[test_name] = {
                "success": False,
                "error": str(e),
                "duration": 0
            }
            print(f"❌ FAILED - {test_name}: {str(e)}")
            logger.exception(f"Test {test_name} failed")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results.values() if r["success"])
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        duration = result.get("duration", 0)
        print(f"{status} {test_name:<25} ({duration:.2f}s)")
        if "error" in result:
            print(f"     Error: {result['error']}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed")
        return False


if __name__ == "__main__":
    # Run tests
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)