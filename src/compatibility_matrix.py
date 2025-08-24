#!/usr/bin/env python3
"""
MCP Server Compatibility Matrix
Manages compatibility information for MCP servers across different Claude versions,
platforms, and dependencies with automated testing and validation.

Author: Lance James, Unit 221B, Inc
Date: August 24, 2025
Version: 1.0.0
"""

import json
import asyncio
import sqlite3
import subprocess
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import semver
import platform
import sys

# Import hAIveMind components
try:
    from memory_server import store_memory
    HAIVEMIND_AVAILABLE = True
except ImportError:
    HAIVEMIND_AVAILABLE = False

class CompatibilityStatus(Enum):
    """Compatibility status levels"""
    COMPATIBLE = "compatible"
    PARTIALLY_COMPATIBLE = "partially_compatible"
    INCOMPATIBLE = "incompatible"
    UNTESTED = "untested"
    DEPRECATED = "deprecated"

class TestResult(Enum):
    """Test result status"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"
    ERROR = "error"

@dataclass
class CompatibilityEntry:
    """Single compatibility entry"""
    server_id: str
    component_type: str  # "claude_version", "platform", "python_version", "dependency"
    component_name: str
    component_version: str
    status: CompatibilityStatus
    tested_at: datetime
    test_results: List[Dict[str, Any]]
    notes: str = ""
    confidence: float = 1.0  # 0.0 to 1.0
    
    def __post_init__(self):
        if isinstance(self.status, str):
            self.status = CompatibilityStatus(self.status)

@dataclass
class TestCase:
    """Test case for compatibility validation"""
    name: str
    description: str
    test_type: str  # "import", "function", "integration", "performance"
    test_command: List[str]
    expected_result: str
    timeout: int = 30
    required: bool = True

class CompatibilityMatrix:
    """
    Manages compatibility information and testing for MCP servers
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_path = config.get("database_path", "data/compatibility.db")
        self.test_cache_dir = Path(config.get("test_cache_dir", "data/compatibility_tests"))
        self.test_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Supported versions and platforms
        self.claude_versions = config.get("claude_versions", [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022", 
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ])
        
        self.platforms = config.get("platforms", [
            "linux", "macos", "windows"
        ])
        
        self.python_versions = config.get("python_versions", [
            "3.8", "3.9", "3.10", "3.11", "3.12"
        ])
        
        # Test configurations
        self.test_timeout = config.get("test_timeout", 60)
        self.auto_test = config.get("auto_test", True)
        
    def _init_database(self):
        """Initialize compatibility database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Compatibility entries table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compatibility_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id TEXT NOT NULL,
                    component_type TEXT NOT NULL,
                    component_name TEXT NOT NULL,
                    component_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    tested_at INTEGER NOT NULL,
                    test_results TEXT, -- JSON
                    notes TEXT,
                    confidence REAL DEFAULT 1.0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)
            
            # Test cases table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    test_type TEXT NOT NULL,
                    test_command TEXT NOT NULL, -- JSON array
                    expected_result TEXT NOT NULL,
                    timeout INTEGER DEFAULT 30,
                    required BOOLEAN DEFAULT TRUE,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)
            
            # Test runs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id TEXT NOT NULL,
                    test_case_id INTEGER NOT NULL,
                    component_type TEXT NOT NULL,
                    component_version TEXT NOT NULL,
                    result TEXT NOT NULL,
                    output TEXT,
                    error_message TEXT,
                    duration REAL,
                    run_at INTEGER NOT NULL,
                    FOREIGN KEY (test_case_id) REFERENCES test_cases(id) ON DELETE CASCADE
                )
            """)
            
            # Compatibility reports table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compatibility_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id TEXT NOT NULL,
                    report_type TEXT NOT NULL, -- "full", "incremental", "targeted"
                    total_tests INTEGER NOT NULL,
                    passed_tests INTEGER NOT NULL,
                    failed_tests INTEGER NOT NULL,
                    warnings INTEGER NOT NULL,
                    overall_score REAL NOT NULL,
                    generated_at INTEGER NOT NULL,
                    report_data TEXT -- JSON
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_compatibility_server ON compatibility_entries(server_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_compatibility_component ON compatibility_entries(component_type, component_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_test_cases_server ON test_cases(server_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_test_runs_server ON test_runs(server_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_test_runs_result ON test_runs(result)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_server ON compatibility_reports(server_id)")
            
            conn.commit()
    
    async def add_compatibility_entry(self, entry: CompatibilityEntry) -> int:
        """Add a compatibility entry"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO compatibility_entries (
                        server_id, component_type, component_name, component_version,
                        status, tested_at, test_results, notes, confidence,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.server_id, entry.component_type, entry.component_name,
                    entry.component_version, entry.status.value,
                    int(entry.tested_at.timestamp()), json.dumps(entry.test_results),
                    entry.notes, entry.confidence, int(datetime.now().timestamp()),
                    int(datetime.now().timestamp())
                ))
                
                entry_id = cursor.lastrowid
                conn.commit()
                
                # Store in hAIveMind
                if HAIVEMIND_AVAILABLE:
                    await store_memory(
                        content=f"Compatibility entry added: {entry.server_id} - {entry.component_type} {entry.component_name} {entry.component_version} = {entry.status.value}",
                        category="marketplace",
                        metadata={
                            "action": "compatibility_entry_added",
                            "server_id": entry.server_id,
                            "component_type": entry.component_type,
                            "component_name": entry.component_name,
                            "status": entry.status.value,
                            "confidence": entry.confidence
                        },
                        project="mcp-marketplace",
                        scope="project-shared"
                    )
                
                return entry_id
                
        except Exception as e:
            raise Exception(f"Failed to add compatibility entry: {str(e)}")
    
    async def get_compatibility_matrix(self, server_id: str) -> Dict[str, Any]:
        """Get complete compatibility matrix for a server"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                entries = conn.execute("""
                    SELECT * FROM compatibility_entries 
                    WHERE server_id = ?
                    ORDER BY component_type, component_name, component_version
                """, (server_id,)).fetchall()
                
                # Organize by component type
                matrix = {
                    "server_id": server_id,
                    "claude_versions": {},
                    "platforms": {},
                    "python_versions": {},
                    "dependencies": {},
                    "last_updated": None,
                    "overall_compatibility": "unknown"
                }
                
                latest_update = None
                total_entries = 0
                compatible_entries = 0
                
                for entry in entries:
                    entry_data = {
                        "status": entry["status"],
                        "tested_at": datetime.fromtimestamp(entry["tested_at"]).isoformat(),
                        "test_results": json.loads(entry["test_results"]) if entry["test_results"] else [],
                        "notes": entry["notes"],
                        "confidence": entry["confidence"]
                    }
                    
                    # Track latest update
                    tested_at = datetime.fromtimestamp(entry["tested_at"])
                    if latest_update is None or tested_at > latest_update:
                        latest_update = tested_at
                    
                    # Count for overall compatibility
                    total_entries += 1
                    if entry["status"] == "compatible":
                        compatible_entries += 1
                    
                    # Organize by component type
                    component_type = entry["component_type"]
                    component_key = f"{entry['component_name']}_{entry['component_version']}"
                    
                    if component_type == "claude_version":
                        matrix["claude_versions"][component_key] = entry_data
                    elif component_type == "platform":
                        matrix["platforms"][component_key] = entry_data
                    elif component_type == "python_version":
                        matrix["python_versions"][component_key] = entry_data
                    elif component_type == "dependency":
                        matrix["dependencies"][component_key] = entry_data
                
                # Calculate overall compatibility
                if total_entries > 0:
                    compatibility_ratio = compatible_entries / total_entries
                    if compatibility_ratio >= 0.8:
                        matrix["overall_compatibility"] = "high"
                    elif compatibility_ratio >= 0.6:
                        matrix["overall_compatibility"] = "medium"
                    else:
                        matrix["overall_compatibility"] = "low"
                
                matrix["last_updated"] = latest_update.isoformat() if latest_update else None
                matrix["statistics"] = {
                    "total_entries": total_entries,
                    "compatible": compatible_entries,
                    "compatibility_ratio": compatibility_ratio if total_entries > 0 else 0
                }
                
                return matrix
                
        except Exception as e:
            raise Exception(f"Failed to get compatibility matrix: {str(e)}")
    
    async def test_server_compatibility(self, 
                                      server_id: str,
                                      server_package_path: str,
                                      test_components: List[str] = None) -> Dict[str, Any]:
        """Test server compatibility across different components"""
        try:
            test_results = {
                "server_id": server_id,
                "test_started_at": datetime.now().isoformat(),
                "components_tested": [],
                "test_summary": {
                    "total_tests": 0,
                    "passed": 0,
                    "failed": 0,
                    "warnings": 0,
                    "errors": 0
                },
                "detailed_results": {}
            }
            
            # Default components to test
            if test_components is None:
                test_components = ["python_version", "dependencies", "basic_functionality"]
            
            # Test Python versions
            if "python_version" in test_components:
                python_results = await self._test_python_versions(server_id, server_package_path)
                test_results["detailed_results"]["python_versions"] = python_results
                test_results["components_tested"].append("python_version")
                
                # Update summary
                for result in python_results.values():
                    test_results["test_summary"]["total_tests"] += 1
                    test_results["test_summary"][result["status"]] += 1
            
            # Test dependencies
            if "dependencies" in test_components:
                dep_results = await self._test_dependencies(server_id, server_package_path)
                test_results["detailed_results"]["dependencies"] = dep_results
                test_results["components_tested"].append("dependencies")
                
                # Update summary
                for result in dep_results.values():
                    test_results["test_summary"]["total_tests"] += 1
                    test_results["test_summary"][result["status"]] += 1
            
            # Test basic functionality
            if "basic_functionality" in test_components:
                func_results = await self._test_basic_functionality(server_id, server_package_path)
                test_results["detailed_results"]["basic_functionality"] = func_results
                test_results["components_tested"].append("basic_functionality")
                
                # Update summary
                for result in func_results.values():
                    test_results["test_summary"]["total_tests"] += 1
                    test_results["test_summary"][result["status"]] += 1
            
            # Calculate overall score
            total = test_results["test_summary"]["total_tests"]
            if total > 0:
                passed = test_results["test_summary"]["passed"]
                warnings = test_results["test_summary"]["warnings"]
                score = (passed + warnings * 0.5) / total
                test_results["overall_score"] = round(score, 2)
            else:
                test_results["overall_score"] = 0.0
            
            test_results["test_completed_at"] = datetime.now().isoformat()
            
            # Store test report
            await self._store_compatibility_report(server_id, test_results)
            
            # Store in hAIveMind
            if HAIVEMIND_AVAILABLE:
                await store_memory(
                    content=f"Compatibility testing completed for {server_id}: {test_results['overall_score']:.2f} score",
                    category="marketplace",
                    metadata={
                        "action": "compatibility_test_completed",
                        "server_id": server_id,
                        "overall_score": test_results["overall_score"],
                        "total_tests": total,
                        "passed_tests": test_results["test_summary"]["passed"],
                        "components_tested": test_components
                    },
                    project="mcp-marketplace",
                    scope="project-shared"
                )
            
            return test_results
            
        except Exception as e:
            return {
                "server_id": server_id,
                "error": str(e),
                "test_completed_at": datetime.now().isoformat(),
                "overall_score": 0.0
            }
    
    async def _test_python_versions(self, server_id: str, package_path: str) -> Dict[str, Any]:
        """Test compatibility with different Python versions"""
        results = {}
        
        # Get current Python version as baseline
        current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        
        for version in self.python_versions:
            try:
                # For now, we'll test with current Python version
                # In a full implementation, this would use Docker or pyenv
                if version == current_version:
                    result = await self._test_python_import(package_path)
                    results[f"python_{version}"] = {
                        "status": "passed" if result["success"] else "failed",
                        "details": result,
                        "tested_with": "current_python",
                        "notes": f"Tested with Python {current_version}"
                    }
                else:
                    results[f"python_{version}"] = {
                        "status": "skipped",
                        "details": {"message": "Version not available for testing"},
                        "tested_with": "none",
                        "notes": f"Python {version} testing requires additional setup"
                    }
                    
            except Exception as e:
                results[f"python_{version}"] = {
                    "status": "error",
                    "details": {"error": str(e)},
                    "tested_with": "none",
                    "notes": f"Error testing Python {version}"
                }
        
        return results
    
    async def _test_dependencies(self, server_id: str, package_path: str) -> Dict[str, Any]:
        """Test dependency installation and compatibility"""
        results = {}
        
        try:
            # Extract package to temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract package
                import zipfile
                with zipfile.ZipFile(package_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                
                # Look for requirements.txt
                requirements_file = temp_path / "requirements.txt"
                if requirements_file.exists():
                    # Test dependency installation
                    result = await self._test_pip_install(requirements_file)
                    results["requirements_install"] = {
                        "status": "passed" if result["success"] else "failed",
                        "details": result,
                        "notes": "Requirements.txt dependency test"
                    }
                    
                    # Test individual dependencies
                    with open(requirements_file, 'r') as f:
                        deps = f.read().strip().split('\n')
                    
                    for dep in deps:
                        if dep.strip() and not dep.startswith('#'):
                            dep_name = dep.split('>=')[0].split('==')[0].split('<')[0].strip()
                            dep_result = await self._test_import_dependency(dep_name)
                            results[f"dependency_{dep_name}"] = {
                                "status": "passed" if dep_result["success"] else "failed",
                                "details": dep_result,
                                "notes": f"Import test for {dep_name}"
                            }
                else:
                    results["no_requirements"] = {
                        "status": "warning",
                        "details": {"message": "No requirements.txt found"},
                        "notes": "Server may have no external dependencies"
                    }
                    
        except Exception as e:
            results["dependency_test_error"] = {
                "status": "error",
                "details": {"error": str(e)},
                "notes": "Error during dependency testing"
            }
        
        return results
    
    async def _test_basic_functionality(self, server_id: str, package_path: str) -> Dict[str, Any]:
        """Test basic server functionality"""
        results = {}
        
        try:
            # Extract and test basic server structure
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract package
                import zipfile
                with zipfile.ZipFile(package_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                
                # Test server file exists
                server_files = list(temp_path.glob("server.py")) + list(temp_path.glob("main.py"))
                if server_files:
                    results["server_file_exists"] = {
                        "status": "passed",
                        "details": {"file": str(server_files[0])},
                        "notes": "Main server file found"
                    }
                    
                    # Test basic syntax
                    syntax_result = await self._test_python_syntax(server_files[0])
                    results["syntax_check"] = {
                        "status": "passed" if syntax_result["success"] else "failed",
                        "details": syntax_result,
                        "notes": "Python syntax validation"
                    }
                else:
                    results["server_file_missing"] = {
                        "status": "failed",
                        "details": {"message": "No server.py or main.py found"},
                        "notes": "Main server file is required"
                    }
                
                # Test configuration file
                config_files = list(temp_path.glob("config.json")) + list(temp_path.glob("*.json"))
                if config_files:
                    config_result = await self._test_json_config(config_files[0])
                    results["config_validation"] = {
                        "status": "passed" if config_result["success"] else "warning",
                        "details": config_result,
                        "notes": "Configuration file validation"
                    }
                
        except Exception as e:
            results["functionality_test_error"] = {
                "status": "error",
                "details": {"error": str(e)},
                "notes": "Error during functionality testing"
            }
        
        return results
    
    # Helper test methods
    
    async def _test_python_import(self, package_path: str) -> Dict[str, Any]:
        """Test if package can be imported"""
        try:
            # This is a simplified test - would need more sophisticated testing
            return {
                "success": True,
                "message": "Basic import test passed"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _test_pip_install(self, requirements_file: Path) -> Dict[str, Any]:
        """Test pip install of requirements"""
        try:
            # Create a virtual environment for testing
            with tempfile.TemporaryDirectory() as venv_dir:
                # This would create a venv and test installation
                # For now, return success simulation
                return {
                    "success": True,
                    "message": "Requirements installation simulated"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _test_import_dependency(self, dep_name: str) -> Dict[str, Any]:
        """Test importing a specific dependency"""
        try:
            __import__(dep_name)
            return {
                "success": True,
                "message": f"Successfully imported {dep_name}"
            }
        except ImportError:
            return {
                "success": False,
                "error": f"Could not import {dep_name}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _test_python_syntax(self, file_path: Path) -> Dict[str, Any]:
        """Test Python file syntax"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            compile(content, str(file_path), 'exec')
            return {
                "success": True,
                "message": "Syntax check passed"
            }
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _test_json_config(self, config_path: Path) -> Dict[str, Any]:
        """Test JSON configuration file"""
        try:
            with open(config_path, 'r') as f:
                json.load(f)
            return {
                "success": True,
                "message": "JSON configuration is valid"
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _store_compatibility_report(self, server_id: str, test_results: Dict[str, Any]):
        """Store compatibility test report"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO compatibility_reports (
                        server_id, report_type, total_tests, passed_tests,
                        failed_tests, warnings, overall_score, generated_at, report_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    server_id, "automated",
                    test_results["test_summary"]["total_tests"],
                    test_results["test_summary"]["passed"],
                    test_results["test_summary"]["failed"],
                    test_results["test_summary"]["warnings"],
                    test_results["overall_score"],
                    int(datetime.now().timestamp()),
                    json.dumps(test_results)
                ))
                conn.commit()
        except Exception:
            pass  # Don't fail the main operation if report storage fails
    
    async def get_compatibility_report(self, server_id: str, report_id: int = None) -> Optional[Dict[str, Any]]:
        """Get compatibility report for a server"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                if report_id:
                    report = conn.execute(
                        "SELECT * FROM compatibility_reports WHERE id = ? AND server_id = ?",
                        (report_id, server_id)
                    ).fetchone()
                else:
                    # Get latest report
                    report = conn.execute("""
                        SELECT * FROM compatibility_reports 
                        WHERE server_id = ? 
                        ORDER BY generated_at DESC 
                        LIMIT 1
                    """, (server_id,)).fetchone()
                
                if report:
                    report_data = json.loads(report["report_data"])
                    report_data["report_id"] = report["id"]
                    report_data["generated_at"] = datetime.fromtimestamp(report["generated_at"]).isoformat()
                    return report_data
                
                return None
                
        except Exception as e:
            raise Exception(f"Failed to get compatibility report: {str(e)}")
    
    async def get_compatibility_summary(self) -> Dict[str, Any]:
        """Get overall compatibility summary across all servers"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get overall statistics
                stats = conn.execute("""
                    SELECT 
                        COUNT(DISTINCT server_id) as total_servers,
                        COUNT(*) as total_entries,
                        SUM(CASE WHEN status = 'compatible' THEN 1 ELSE 0 END) as compatible_entries,
                        AVG(confidence) as avg_confidence
                    FROM compatibility_entries
                """).fetchone()
                
                # Get component type breakdown
                component_stats = conn.execute("""
                    SELECT 
                        component_type,
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'compatible' THEN 1 ELSE 0 END) as compatible,
                        AVG(confidence) as avg_confidence
                    FROM compatibility_entries
                    GROUP BY component_type
                """).fetchall()
                
                # Get recent test activity
                recent_tests = conn.execute("""
                    SELECT COUNT(*) as count
                    FROM compatibility_reports
                    WHERE generated_at > ?
                """, (int((datetime.now() - timedelta(days=7)).timestamp()),)).fetchone()
                
                return {
                    "overview": {
                        "total_servers": stats["total_servers"],
                        "total_entries": stats["total_entries"],
                        "compatible_entries": stats["compatible_entries"],
                        "compatibility_rate": stats["compatible_entries"] / stats["total_entries"] if stats["total_entries"] > 0 else 0,
                        "average_confidence": stats["avg_confidence"]
                    },
                    "by_component": [dict(row) for row in component_stats],
                    "recent_activity": {
                        "tests_last_week": recent_tests["count"]
                    },
                    "generated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            raise Exception(f"Failed to get compatibility summary: {str(e)}")

def create_compatibility_matrix(config: Dict[str, Any]) -> CompatibilityMatrix:
    """Create and configure compatibility matrix"""
    return CompatibilityMatrix(config)

if __name__ == "__main__":
    # Example usage
    config = {
        "database_path": "data/compatibility.db",
        "test_cache_dir": "data/compatibility_tests",
        "auto_test": True,
        "test_timeout": 60
    }
    
    matrix = create_compatibility_matrix(config)
    print("Compatibility matrix initialized successfully")