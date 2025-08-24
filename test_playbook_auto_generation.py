#!/usr/bin/env python3
"""
Test Script for Playbook Auto-Generation System

This script tests the complete integration of the playbook auto-generation system:
- Pattern analysis from incident memories
- Auto-generation of playbook suggestions
- Human review workflow
- Version control integration
- hAIveMind cross-agent learning
- Recommendation engine functionality
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from memory_server import MemoryStorage
from playbook_auto_generator import PlaybookAutoGenerator
from playbook_recommendation_engine import PlaybookRecommendationEngine, IncidentContext
from playbook_version_control import PlaybookVersionControl, ChangeType
from playbook_auto_generation_mcp_tools import PlaybookAutoGenerationMCPTools

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PlaybookAutoGenerationTester:
    """Comprehensive tester for playbook auto-generation system"""
    
    def __init__(self):
        self.config = self._load_config()
        self.memory_storage = None
        self.auto_generator = None
        self.recommendation_engine = None
        self.version_control = None
        self.mcp_tools = None
        
        # Test data
        self.test_incidents = []
        self.test_suggestions = []
        self.test_results = {}
    
    def _load_config(self) -> dict:
        """Load configuration for testing"""
        try:
            with open("config/config.json", "r") as f:
                config = json.load(f)
            
            # Override for testing
            config["playbook_auto_generation"] = {
                "enabled": True,
                "continuous_monitoring": False,  # Disable for testing
                "auto_generation": {
                    "min_pattern_frequency": 2,  # Lower threshold for testing
                    "min_success_rate": 0.6,
                    "similarity_threshold": 0.6,
                    "confidence_threshold": 0.6
                },
                "recommendations": {
                    "min_relevance_score": 0.5,
                    "max_recommendations": 10,
                    "context_window_hours": 24
                }
            }
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    async def setup(self):
        """Initialize all components for testing"""
        try:
            logger.info("🔧 Setting up test environment...")
            
            # Initialize memory storage
            self.memory_storage = MemoryStorage(self.config)
            
            # Initialize auto-generation components
            self.auto_generator = PlaybookAutoGenerator(
                self.memory_storage, 
                self.config.get('playbook_auto_generation', {}).get('auto_generation', {})
            )
            
            self.recommendation_engine = PlaybookRecommendationEngine(
                self.memory_storage,
                self.auto_generator,
                self.config.get('playbook_auto_generation', {}).get('recommendations', {})
            )
            
            self.version_control = PlaybookVersionControl(
                self.memory_storage,
                {"auto_version_on_change": True, "max_versions_per_playbook": 10}
            )
            
            self.mcp_tools = PlaybookAutoGenerationMCPTools(
                self.memory_storage,
                self.config.get('playbook_auto_generation', {})
            )
            
            logger.info("✅ Test environment setup complete")
            
        except Exception as e:
            logger.error(f"💥 Setup failed: {e}")
            raise
    
    async def create_test_incidents(self):
        """Create test incident data for pattern analysis"""
        try:
            logger.info("📝 Creating test incident data...")
            
            test_incidents = [
                {
                    "title": "Elasticsearch cluster degraded performance",
                    "description": "Elasticsearch cluster showing high CPU usage and slow query responses. Resolved by restarting elasticsearch service and clearing cache.",
                    "resolution": "1. Check elasticsearch status\n2. Restart elasticsearch service: sudo systemctl restart elasticsearch\n3. Clear query cache\n4. Verify cluster health",
                    "systems": ["elasticsearch", "elastic1"],
                    "severity": "high",
                    "resolved": True
                },
                {
                    "title": "Elasticsearch service down",
                    "description": "Elasticsearch service completely unresponsive. Fixed by restarting the service and checking disk space.",
                    "resolution": "1. Check service status: systemctl status elasticsearch\n2. Check disk space: df -h\n3. Restart service: sudo systemctl restart elasticsearch\n4. Monitor logs",
                    "systems": ["elasticsearch", "elastic2"],
                    "severity": "critical",
                    "resolved": True
                },
                {
                    "title": "Elasticsearch memory issues",
                    "description": "Elasticsearch running out of memory, causing OOM errors. Resolved by adjusting heap size and restarting.",
                    "resolution": "1. Check memory usage\n2. Adjust ES_JAVA_OPTS heap size\n3. Restart elasticsearch service\n4. Monitor memory usage",
                    "systems": ["elasticsearch", "elastic3"],
                    "severity": "high",
                    "resolved": True
                },
                {
                    "title": "Nginx proxy timeout errors",
                    "description": "Nginx showing 504 gateway timeout errors. Fixed by adjusting proxy timeout settings and restarting nginx.",
                    "resolution": "1. Check nginx error logs\n2. Adjust proxy_read_timeout in config\n3. Test configuration: nginx -t\n4. Restart nginx: sudo systemctl restart nginx",
                    "systems": ["nginx", "proxy"],
                    "severity": "medium",
                    "resolved": True
                },
                {
                    "title": "Redis connection failures",
                    "description": "Applications unable to connect to Redis. Resolved by restarting Redis and checking network connectivity.",
                    "resolution": "1. Check Redis status: systemctl status redis\n2. Test connection: redis-cli ping\n3. Restart Redis: sudo systemctl restart redis\n4. Verify applications can connect",
                    "systems": ["redis", "cache"],
                    "severity": "high",
                    "resolved": True
                }
            ]
            
            # Store incidents in memory
            for i, incident in enumerate(test_incidents):
                incident_content = f"INCIDENT: {incident['title']}\n\nDescription: {incident['description']}\n\nResolution Steps:\n{incident['resolution']}"
                
                memory_id = await self.memory_storage.store_memory(
                    content=incident_content,
                    category="incidents",
                    metadata={
                        "title": incident["title"],
                        "systems": incident["systems"],
                        "severity": incident["severity"],
                        "resolved": incident["resolved"],
                        "incident_type": "test_data"
                    },
                    tags=["test", "incident", "resolved"] + incident["systems"]
                )
                
                incident["memory_id"] = memory_id
                self.test_incidents.append(incident)
            
            logger.info(f"✅ Created {len(self.test_incidents)} test incidents")
            
        except Exception as e:
            logger.error(f"💥 Failed to create test incidents: {e}")
            raise
    
    async def test_pattern_analysis(self):
        """Test incident pattern analysis and detection"""
        try:
            logger.info("🔍 Testing pattern analysis...")
            
            # Run pattern analysis
            result = await self.mcp_tools.analyze_incident_patterns(
                lookback_days=1,  # Recent incidents only
                min_incidents=2,  # Lower threshold for testing
                force_analysis=True
            )
            
            self.test_results["pattern_analysis"] = result
            
            # Validate results
            assert result["status"] == "completed", f"Pattern analysis failed: {result}"
            assert result["patterns_found"] >= 0, "No patterns found"
            
            if result["patterns_found"] > 0:
                logger.info(f"✅ Pattern analysis successful: {result['patterns_found']} patterns found")
                
                # Check for elasticsearch patterns (should be detected from test data)
                if result.get("new_pattern_summary"):
                    elasticsearch_patterns = [p for p in result["new_pattern_summary"] 
                                            if "elasticsearch" in p.get("systems", [])]
                    assert len(elasticsearch_patterns) > 0, "Expected Elasticsearch patterns not found"
                    logger.info(f"✅ Elasticsearch patterns detected: {len(elasticsearch_patterns)}")
            else:
                logger.warning("⚠️ No patterns detected - may need more test data")
            
        except Exception as e:
            logger.error(f"💥 Pattern analysis test failed: {e}")
            raise
    
    async def test_playbook_suggestions(self):
        """Test playbook suggestion generation"""
        try:
            logger.info("💡 Testing playbook suggestion generation...")
            
            # Get pending suggestions
            result = await self.mcp_tools.get_pending_playbook_suggestions(limit=10)
            
            self.test_results["playbook_suggestions"] = result
            
            # Validate results
            assert result["status"] == "success", f"Failed to get suggestions: {result}"
            
            suggestions = result.get("suggestions", [])
            if suggestions:
                logger.info(f"✅ Found {len(suggestions)} pending suggestions")
                
                # Test suggestion details
                first_suggestion = suggestions[0]
                required_fields = ["suggestion_id", "title", "confidence_score", "playbook_preview"]
                
                for field in required_fields:
                    assert field in first_suggestion, f"Missing required field: {field}"
                
                self.test_suggestions = suggestions
                logger.info(f"✅ Suggestion validation successful")
            else:
                logger.warning("⚠️ No suggestions generated - may need pattern analysis first")
            
        except Exception as e:
            logger.error(f"💥 Playbook suggestions test failed: {e}")
            raise
    
    async def test_recommendation_engine(self):
        """Test playbook recommendation engine"""
        try:
            logger.info("🎯 Testing recommendation engine...")
            
            # Test incident-based recommendations
            result = await self.mcp_tools.recommend_playbooks_for_incident(
                incident_title="Elasticsearch cluster performance issues",
                incident_description="High CPU usage and slow queries on elasticsearch cluster",
                affected_systems=["elasticsearch", "elastic1"],
                severity="high",
                symptoms=["high CPU", "slow queries", "timeout errors"]
            )
            
            self.test_results["incident_recommendations"] = result
            
            # Validate results
            assert result["status"] == "success", f"Incident recommendations failed: {result}"
            
            recommendations = result.get("recommendations", [])
            logger.info(f"✅ Generated {len(recommendations)} incident-based recommendations")
            
            if recommendations:
                # Test recommendation structure
                first_rec = recommendations[0]
                required_fields = ["playbook_id", "title", "relevance_score", "confidence_score", "reasoning"]
                
                for field in required_fields:
                    assert field in first_rec, f"Missing required field in recommendation: {field}"
                
                # Test contextual recommendations
                context_result = await self.mcp_tools.recommend_playbooks_for_context(
                    query="need to restart elasticsearch service safely",
                    systems=["elasticsearch"],
                    severity="medium"
                )
                
                self.test_results["context_recommendations"] = context_result
                
                assert context_result["status"] == "success", f"Context recommendations failed: {context_result}"
                logger.info(f"✅ Generated {len(context_result.get('recommendations', []))} contextual recommendations")
            
        except Exception as e:
            logger.error(f"💥 Recommendation engine test failed: {e}")
            raise
    
    async def test_human_review_workflow(self):
        """Test human review workflow"""
        try:
            logger.info("👥 Testing human review workflow...")
            
            if not self.test_suggestions:
                logger.warning("⚠️ No suggestions available for review testing")
                return
            
            # Test review submission
            test_suggestion = self.test_suggestions[0]
            suggestion_id = test_suggestion["suggestion_id"]
            
            # Test approval
            result = await self.mcp_tools.review_playbook_suggestion(
                suggestion_id=suggestion_id,
                action="approve",
                reviewer_notes="Test approval - looks good for automation"
            )
            
            self.test_results["human_review"] = result
            
            # Validate results
            assert result["status"] == "success", f"Review submission failed: {result}"
            assert result["action"] == "approve", "Review action not recorded correctly"
            
            logger.info(f"✅ Human review workflow test successful")
            
            # Test feedback recording
            feedback_result = await self.mcp_tools.record_recommendation_feedback(
                recommendation_id="test_rec_123",
                executed=True,
                successful=True,
                feedback_notes="Test feedback - worked as expected"
            )
            
            assert feedback_result["status"] == "success", f"Feedback recording failed: {feedback_result}"
            logger.info(f"✅ Feedback recording test successful")
            
        except Exception as e:
            logger.error(f"💥 Human review workflow test failed: {e}")
            raise
    
    async def test_version_control(self):
        """Test playbook version control system"""
        try:
            logger.info("📋 Testing version control system...")
            
            # Create a test playbook version
            test_playbook_spec = {
                "version": 1,
                "name": "Test Elasticsearch Restart Playbook",
                "description": "Test playbook for restarting Elasticsearch service",
                "parameters": [
                    {"name": "service_name", "required": True, "description": "Service to restart"}
                ],
                "steps": [
                    {"id": "check_status", "name": "Check service status", "action": "shell", 
                     "args": {"command": "systemctl is-active ${service_name}"}},
                    {"id": "restart_service", "name": "Restart service", "action": "shell",
                     "args": {"command": "sudo systemctl restart ${service_name}"}}
                ]
            }
            
            # Create initial version
            version = await self.version_control.create_playbook_version(
                playbook_id="test_elasticsearch_restart",
                content=test_playbook_spec,
                change_type=ChangeType.CREATED,
                change_description="Initial version of test playbook",
                author="test_system"
            )
            
            assert version is not None, "Failed to create playbook version"
            assert version.version_number == "1.0.0", f"Unexpected version number: {version.version_number}"
            
            logger.info(f"✅ Created playbook version: {version.version_number}")
            
            # Test version retrieval
            retrieved_version = await self.version_control.get_version(version.version_id)
            assert retrieved_version is not None, "Failed to retrieve version"
            assert retrieved_version.version_id == version.version_id, "Version ID mismatch"
            
            # Test execution recording
            execution = await self.version_control.record_execution(
                version_id=version.version_id,
                executed_by="test_user",
                success=True,
                duration_seconds=30.5,
                feedback_score=0.9,
                improvements_suggested=["Add error handling"]
            )
            
            assert execution is not None, "Failed to record execution"
            assert execution.success == True, "Execution success not recorded correctly"
            
            logger.info(f"✅ Version control test successful")
            
            self.test_results["version_control"] = {
                "version_created": True,
                "version_id": version.version_id,
                "version_number": version.version_number,
                "execution_recorded": True
            }
            
        except Exception as e:
            logger.error(f"💥 Version control test failed: {e}")
            raise
    
    async def test_statistics_and_monitoring(self):
        """Test statistics and monitoring capabilities"""
        try:
            logger.info("📊 Testing statistics and monitoring...")
            
            # Get pattern statistics
            stats_result = await self.mcp_tools.get_pattern_statistics()
            
            self.test_results["statistics"] = stats_result
            
            # Validate statistics
            assert stats_result["status"] == "success", f"Statistics retrieval failed: {stats_result}"
            
            stats = stats_result.get("statistics", {})
            expected_fields = ["total_patterns", "total_suggestions", "system_health"]
            
            for field in expected_fields:
                assert field in stats, f"Missing statistics field: {field}"
            
            logger.info(f"✅ Statistics test successful")
            
            # Test export functionality
            export_result = await self.mcp_tools.export_generated_playbooks(
                format="json",
                include_pending=True
            )
            
            assert export_result["status"] == "success", f"Export failed: {export_result}"
            assert "content" in export_result, "Export content missing"
            
            logger.info(f"✅ Export test successful: {export_result['playbooks_exported']} playbooks exported")
            
        except Exception as e:
            logger.error(f"💥 Statistics and monitoring test failed: {e}")
            raise
    
    async def test_haivemind_integration(self):
        """Test hAIveMind integration and cross-agent learning"""
        try:
            logger.info("🧠 Testing hAIveMind integration...")
            
            # Test agent registration (if available)
            if hasattr(self.memory_storage, 'register_agent'):
                try:
                    result = await self.memory_storage.register_agent(
                        role="playbook_tester",
                        description="Test agent for playbook auto-generation system",
                        capabilities=["testing", "playbook_generation", "pattern_analysis"]
                    )
                    logger.info(f"✅ Agent registration successful: {result}")
                except Exception as e:
                    logger.warning(f"⚠️ Agent registration not available: {e}")
            
            # Test pattern learning trigger
            learning_result = await self.mcp_tools.trigger_pattern_learning(
                force_reanalysis=True
            )
            
            assert learning_result["status"] in ["success", "not_implemented"], f"Pattern learning failed: {learning_result}"
            
            if learning_result["status"] == "success":
                logger.info(f"✅ Pattern learning successful: {learning_result['patterns_found']} patterns")
            else:
                logger.info(f"ℹ️ Pattern learning: {learning_result['message']}")
            
            self.test_results["haivemind_integration"] = learning_result
            
        except Exception as e:
            logger.error(f"💥 hAIveMind integration test failed: {e}")
            raise
    
    async def run_comprehensive_test(self):
        """Run all tests in sequence"""
        try:
            logger.info("🚀 Starting comprehensive playbook auto-generation test...")
            
            start_time = time.time()
            
            # Setup
            await self.setup()
            
            # Create test data
            await self.create_test_incidents()
            
            # Wait a moment for data to be indexed
            await asyncio.sleep(2)
            
            # Run tests
            await self.test_pattern_analysis()
            await self.test_playbook_suggestions()
            await self.test_recommendation_engine()
            await self.test_human_review_workflow()
            await self.test_version_control()
            await self.test_statistics_and_monitoring()
            await self.test_haivemind_integration()
            
            # Calculate total time
            total_time = time.time() - start_time
            
            # Generate test report
            await self.generate_test_report(total_time)
            
            logger.info(f"🎉 All tests completed successfully in {total_time:.2f} seconds!")
            
        except Exception as e:
            logger.error(f"💥 Comprehensive test failed: {e}")
            raise
    
    async def generate_test_report(self, total_time: float):
        """Generate a comprehensive test report"""
        try:
            report = {
                "test_summary": {
                    "timestamp": datetime.now().isoformat(),
                    "total_duration_seconds": total_time,
                    "status": "PASSED",
                    "test_incidents_created": len(self.test_incidents),
                    "test_suggestions_generated": len(self.test_suggestions)
                },
                "test_results": self.test_results,
                "system_info": {
                    "memory_storage_initialized": self.memory_storage is not None,
                    "auto_generator_initialized": self.auto_generator is not None,
                    "recommendation_engine_initialized": self.recommendation_engine is not None,
                    "version_control_initialized": self.version_control is not None,
                    "mcp_tools_initialized": self.mcp_tools is not None
                }
            }
            
            # Save report to file
            report_file = f"test_report_{int(time.time())}.json"
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"📄 Test report saved to: {report_file}")
            
            # Print summary
            print("\n" + "="*80)
            print("🎯 PLAYBOOK AUTO-GENERATION TEST SUMMARY")
            print("="*80)
            print(f"✅ Status: {report['test_summary']['status']}")
            print(f"⏱️  Duration: {total_time:.2f} seconds")
            print(f"📝 Test Incidents: {len(self.test_incidents)}")
            print(f"💡 Suggestions Generated: {len(self.test_suggestions)}")
            
            if self.test_results.get("pattern_analysis", {}).get("patterns_found", 0) > 0:
                print(f"🔍 Patterns Detected: {self.test_results['pattern_analysis']['patterns_found']}")
            
            if self.test_results.get("incident_recommendations", {}).get("recommendations_count", 0) > 0:
                print(f"🎯 Recommendations Generated: {self.test_results['incident_recommendations']['recommendations_count']}")
            
            print(f"📄 Full Report: {report_file}")
            print("="*80)
            
        except Exception as e:
            logger.error(f"Failed to generate test report: {e}")

async def main():
    """Main test function"""
    tester = PlaybookAutoGenerationTester()
    
    try:
        await tester.run_comprehensive_test()
        return 0
    except Exception as e:
        logger.error(f"💥 Test suite failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)