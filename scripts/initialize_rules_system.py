#!/usr/bin/env python3
"""
hAIveMind Rules System Initialization Script
Sets up the comprehensive rules database and management system

Author: Lance James, Unit 221B Inc
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from rules_database import RulesDatabase
from rule_management_service import RuleManagementService
from rules_haivemind_integration import RulesHAIveMindIntegration

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize_rules_system():
    """Initialize the complete hAIveMind rules system"""
    
    logger.info("🚀 Initializing hAIveMind Rules Database and Management System")
    
    # Create data directories
    data_dir = Path("data")
    backup_dir = data_dir / "backups" / "rules"
    examples_dir = Path("examples") / "rules"
    
    data_dir.mkdir(exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)
    examples_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("📁 Created directory structure")
    
    # Initialize database
    db_path = data_dir / "rules.db"
    logger.info(f"🗄️  Initializing database at {db_path}")
    
    try:
        rules_db = RulesDatabase(str(db_path))
        logger.info("✅ Database initialized successfully")
        
        # Initialize management service
        rule_service = RuleManagementService(str(db_path))
        logger.info("✅ Rule management service initialized")
        
        # Initialize hAIveMind integration (without actual clients for now)
        haivemind_integration = RulesHAIveMindIntegration(rule_service)
        logger.info("✅ hAIveMind integration initialized")
        
        # Get database statistics
        stats = rules_db.get_rule_statistics()
        logger.info(f"📊 Database initialized with {stats.get('total_rules', 0)} default rules")
        
        # Show rule breakdown
        if stats.get('by_type'):
            logger.info("📋 Default rules by type:")
            for rule_type, count in stats['by_type'].items():
                logger.info(f"   - {rule_type}: {count} rules")
        
        # Show templates
        templates = rules_db.list_rule_templates()
        logger.info(f"📝 {len(templates)} rule templates available:")
        for template in templates:
            logger.info(f"   - {template.name} ({template.category})")
        
        # Create initial backup
        backup_file = backup_dir / f"initial_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        if rules_db.backup_database(str(backup_file)):
            logger.info(f"💾 Initial backup created: {backup_file}")
        
        # Example import
        example_files = list(examples_dir.glob("*.yaml")) + list(examples_dir.glob("*.json"))
        if example_files:
            logger.info(f"📄 Found {len(example_files)} example files:")
            for example_file in example_files:
                logger.info(f"   - {example_file.name}")
        
        logger.info("🎉 hAIveMind Rules System initialization complete!")
        
        # Print usage instructions
        print("\n" + "="*60)
        print("🔧 RULES SYSTEM READY")
        print("="*60)
        print("\n📚 Documentation: docs/RULES_DATABASE_SYSTEM.md")
        print("📁 Database: data/rules.db")
        print("💾 Backups: data/backups/rules/")
        print("📄 Examples: examples/rules/")
        print("\n🔗 MCP Tools Available:")
        print("   - create_rule, update_rule, get_rule")
        print("   - create_rule_from_yaml, create_rule_from_json")
        print("   - export_rules, import_rules")
        print("   - search_rules, get_rule_statistics")
        print("   - analyze_rule_effectiveness, discover_rule_patterns")
        print("   - sync_rules_network, get_network_rule_insights")
        print("\n🎯 Next Steps:")
        print("   1. Import example rules: import_rules with complete_rule_set.yaml")
        print("   2. Create custom rules using templates or YAML/JSON")
        print("   3. Assign rules to specific scopes (projects, agents, machines)")
        print("   4. Monitor effectiveness with analytics tools")
        print("   5. Sync rules across hAIveMind network")
        print("\n✨ Ready for comprehensive rule governance!")
        print("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        return False

def create_sample_rule():
    """Create a sample rule to demonstrate the system"""
    try:
        db_path = Path("data") / "rules.db"
        rule_service = RuleManagementService(str(db_path))
        
        sample_rule = {
            "name": "Sample Initialization Rule",
            "description": "Demonstrates rules system initialization and basic functionality",
            "rule_type": "operational",
            "scope": "global",
            "priority": 300,
            "conditions": [
                {
                    "field": "system_phase",
                    "operator": "eq",
                    "value": "initialization",
                    "case_sensitive": False
                }
            ],
            "actions": [
                {
                    "action_type": "set",
                    "target": "initialization_complete",
                    "value": True,
                    "parameters": {
                        "timestamp": datetime.now().isoformat(),
                        "version": "1.0.0"
                    }
                }
            ],
            "tags": ["sample", "initialization", "demonstration"],
            "metadata": {
                "created_during_init": True,
                "purpose": "demonstration",
                "system_version": "Story 6b Implementation"
            }
        }
        
        rule_id = rule_service.create_rule_from_dict(sample_rule, "initialization_script")
        logger.info(f"✅ Sample rule created with ID: {rule_id}")
        return rule_id
        
    except Exception as e:
        logger.error(f"❌ Failed to create sample rule: {e}")
        return None

def test_basic_operations():
    """Test basic rule operations"""
    logger.info("🧪 Testing basic rule operations")
    
    try:
        db_path = Path("data") / "rules.db"
        rules_db = RulesDatabase(str(db_path))
        rule_service = RuleManagementService(str(db_path))
        
        # Test statistics
        stats = rules_db.get_rule_statistics()
        logger.info(f"📊 Total rules: {stats['total_rules']}")
        
        # Test templates
        templates = rules_db.list_rule_templates()
        logger.info(f"📝 Templates available: {len(templates)}")
        
        # Test search (basic)
        search_results = rule_service.search_rules("authorship")
        logger.info(f"🔍 Search for 'authorship': {len(search_results)} results")
        
        logger.info("✅ Basic operations test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Basic operations test failed: {e}")
        return False

if __name__ == "__main__":
    print("hAIveMind Rules System Initialization")
    print("=====================================")
    
    # Initialize the system
    if initialize_rules_system():
        # Create sample rule
        sample_rule_id = create_sample_rule()
        
        # Test basic operations
        test_basic_operations()
        
        print("\n🎉 Rules system is ready for use!")
        sys.exit(0)
    else:
        print("\n❌ Initialization failed!")
        sys.exit(1)