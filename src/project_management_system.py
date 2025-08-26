"""
Project Management Integration System for hAIveMind DevOps Memory

Comprehensive project context management with scoped operations, health monitoring,
backup/restore functionality, and integration with existing vibe_kanban system.

Features:
- Project context switching for scoped operations
- Project metadata and configuration management
- Health monitoring and status tracking
- Project-specific backup and restore
- Integration with existing agent task system
- Cross-project knowledge sharing controls
- Project-scoped agent task delegation
"""

import sqlite3
import json
import logging
import time
import shutil
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import yaml
import requests
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class Project:
    id: str
    name: str
    description: str
    status: str  # "active", "archived", "maintenance", "error"
    git_repo_path: Optional[str]
    config_path: Optional[str]
    setup_script: Optional[str]
    cleanup_script: Optional[str]
    dev_script: Optional[str]
    health_checks: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_health_check: Optional[datetime]
    
@dataclass
class ProjectHealth:
    project_id: str
    status: str  # "healthy", "warning", "critical", "unknown"
    checks_passed: int
    checks_failed: int
    total_checks: int
    issues: List[Dict[str, Any]]
    last_check: datetime
    response_time_ms: float
    
@dataclass
class ProjectBackup:
    id: str
    project_id: str
    backup_path: str
    backup_type: str  # "full", "config_only", "data_only"
    size_mb: float
    created_at: datetime
    metadata: Dict[str, Any]

class ProjectManagementSystem:
    """Comprehensive project management with context switching and health monitoring"""
    
    def __init__(self, db_path: str = "data/project_management.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Current context
        self.current_project = None
        self.project_cache = {}
        
        # Integration with vibe_kanban
        self.vibe_kanban_available = self._check_vibe_kanban_integration()
        
        logger.info("📁 Project Management System initialized")
    
    def _init_database(self):
        """Initialize SQLite database with project management schema"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        
        try:
            # Projects table (extends vibe_kanban projects)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'maintenance', 'error')),
                    git_repo_path TEXT,
                    config_path TEXT,
                    setup_script TEXT,
                    cleanup_script TEXT,
                    dev_script TEXT,
                    health_checks TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_health_check TIMESTAMP
                )
            ''')
            
            # Project configurations
            conn.execute('''
                CREATE TABLE IF NOT EXISTS project_configs (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    project_id TEXT NOT NULL,
                    config_type TEXT NOT NULL,
                    config_name TEXT NOT NULL,
                    config_data TEXT NOT NULL,
                    config_hash TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                    UNIQUE (project_id, config_type, config_name)
                )
            ''')
            
            # Project health monitoring
            conn.execute('''
                CREATE TABLE IF NOT EXISTS project_health (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    project_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    checks_passed INTEGER DEFAULT 0,
                    checks_failed INTEGER DEFAULT 0,
                    total_checks INTEGER DEFAULT 0,
                    issues TEXT DEFAULT '[]',
                    response_time_ms REAL DEFAULT 0,
                    check_details TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
                )
            ''')
            
            # Project backups
            conn.execute('''
                CREATE TABLE IF NOT EXISTS project_backups (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    project_id TEXT NOT NULL,
                    backup_path TEXT NOT NULL,
                    backup_type TEXT DEFAULT 'full' CHECK (backup_type IN ('full', 'config_only', 'data_only')),
                    size_mb REAL DEFAULT 0,
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
                )
            ''')
            
            # Project context sessions (for scoped operations)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS project_sessions (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    project_id TEXT NOT NULL,
                    session_type TEXT DEFAULT 'context_switch',
                    user_id TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    operations TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
                )
            ''')
            
            # Project dependencies
            conn.execute('''
                CREATE TABLE IF NOT EXISTS project_dependencies (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    project_id TEXT NOT NULL,
                    dependency_type TEXT NOT NULL, -- 'service', 'database', 'external_api', 'library'
                    dependency_name TEXT NOT NULL,
                    dependency_version TEXT,
                    is_critical BOOLEAN DEFAULT TRUE,
                    status TEXT DEFAULT 'unknown', -- 'healthy', 'unhealthy', 'unknown'
                    last_checked TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
                )
            ''')
            
            # Create indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_projects_status ON projects (status)",
                "CREATE INDEX IF NOT EXISTS idx_projects_updated ON projects (updated_at)",
                "CREATE INDEX IF NOT EXISTS idx_configs_project ON project_configs (project_id, config_type)",
                "CREATE INDEX IF NOT EXISTS idx_health_project ON project_health (project_id, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_backups_project ON project_backups (project_id, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_sessions_project ON project_sessions (project_id, started_at)",
                "CREATE INDEX IF NOT EXISTS idx_dependencies_project ON project_dependencies (project_id, dependency_type)"
            ]
            
            for index_sql in indexes:
                conn.execute(index_sql)
            
            conn.commit()
            logger.info("📊 Project Management database schema initialized")
            
        finally:
            conn.close()
    
    def _check_vibe_kanban_integration(self) -> bool:
        """Check if vibe_kanban integration is available"""
        try:
            # Try to import and test vibe_kanban functionality
            import requests
            response = requests.get("http://localhost:8900/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    # ===== PROJECT MANAGEMENT TOOLS =====
    
    def create_project(self, name: str, description: str, 
                      git_repo_path: Optional[str] = None,
                      config_path: Optional[str] = None,
                      setup_script: Optional[str] = None,
                      cleanup_script: Optional[str] = None,
                      dev_script: Optional[str] = None,
                      health_checks: Optional[List[Dict[str, Any]]] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> str:
        """Initialize new project context"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Generate project ID
            project_id = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()
            
            # Insert project
            conn.execute('''
                INSERT INTO projects 
                (id, name, description, git_repo_path, config_path, setup_script, 
                 cleanup_script, dev_script, health_checks, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_id, name, description, git_repo_path, config_path,
                setup_script, cleanup_script, dev_script,
                json.dumps(health_checks or []), json.dumps(metadata or {})
            ))
            
            # If vibe_kanban is available, create corresponding kanban project
            if self.vibe_kanban_available:
                self._create_vibe_kanban_project(project_id, name, git_repo_path)
            
            # Initialize default configurations
            self._create_default_configs(project_id, conn)
            
            # Run setup script if provided
            if setup_script and Path(setup_script).exists():
                self._run_project_script(setup_script, project_id)
            
            conn.commit()
            logger.info(f"📁 Project created: {name} (ID: {project_id})")
            return project_id
            
        finally:
            conn.close()
    
    def _create_vibe_kanban_project(self, project_id: str, name: str, git_repo_path: Optional[str]):
        """Create corresponding vibe_kanban project"""
        try:
            # This would integrate with the MCP vibe_kanban tools
            # For now, just log the integration
            logger.info(f"🔗 Would create vibe_kanban project for: {name}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to create vibe_kanban project: {e}")
    
    def _create_default_configs(self, project_id: str, conn: sqlite3.Connection):
        """Create default project configurations"""
        default_configs = [
            {
                'config_type': 'environment',
                'config_name': 'development',
                'config_data': json.dumps({
                    'NODE_ENV': 'development',
                    'DEBUG': 'true',
                    'LOG_LEVEL': 'info'
                })
            },
            {
                'config_type': 'deployment',
                'config_name': 'docker',
                'config_data': json.dumps({
                    'dockerfile': 'Dockerfile',
                    'compose_file': 'docker-compose.yml',
                    'build_context': '.'
                })
            }
        ]
        
        for config in default_configs:
            config_hash = hashlib.md5(config['config_data'].encode()).hexdigest()
            
            conn.execute('''
                INSERT OR IGNORE INTO project_configs 
                (project_id, config_type, config_name, config_data, config_hash)
                VALUES (?, ?, ?, ?, ?)
            ''', (project_id, config['config_type'], config['config_name'], 
                  config['config_data'], config_hash))
    
    def list_projects(self, status_filter: Optional[str] = None, 
                     include_metadata: bool = True) -> List[Dict[str, Any]]:
        """Show all projects with metadata"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            if status_filter:
                projects = conn.execute(
                    'SELECT * FROM projects WHERE status = ? ORDER BY updated_at DESC',
                    (status_filter,)
                ).fetchall()
            else:
                projects = conn.execute(
                    'SELECT * FROM projects ORDER BY updated_at DESC'
                ).fetchall()
            
            result = []
            for project in projects:
                project_dict = dict(project)
                
                if include_metadata:
                    project_dict['health_checks'] = json.loads(project_dict.get('health_checks', '[]'))
                    project_dict['metadata'] = json.loads(project_dict.get('metadata', '{}'))
                    
                    # Get latest health status
                    health = conn.execute('''
                        SELECT status, checks_passed, checks_failed, total_checks, created_at
                        FROM project_health 
                        WHERE project_id = ? 
                        ORDER BY created_at DESC LIMIT 1
                    ''', (project['id'],)).fetchone()
                    
                    if health:
                        project_dict['health_status'] = dict(health)
                    else:
                        project_dict['health_status'] = {'status': 'unknown'}
                
                result.append(project_dict)
            
            return result
            
        finally:
            conn.close()
    
    def switch_project_context(self, project_id: str, user_id: str = "system") -> bool:
        """Change active project scope"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Verify project exists
            project = conn.execute(
                'SELECT * FROM projects WHERE id = ?', (project_id,)
            ).fetchone()
            
            if not project:
                logger.error(f"❌ Project {project_id} not found")
                return False
            
            # End current session if exists
            if self.current_project:
                conn.execute('''
                    UPDATE project_sessions 
                    SET ended_at = CURRENT_TIMESTAMP 
                    WHERE project_id = ? AND ended_at IS NULL
                ''', (self.current_project,))
            
            # Start new session
            conn.execute('''
                INSERT INTO project_sessions (project_id, user_id)
                VALUES (?, ?)
            ''', (project_id, user_id))
            
            # Update current context
            self.current_project = project_id
            self.project_cache[project_id] = dict(project)
            
            conn.commit()
            
            logger.info(f"🔄 Switched to project context: {project[1]} ({project_id})")
            return True
            
        finally:
            conn.close()
    
    def project_health_check(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Analyze project status and issues"""
        if not project_id:
            project_id = self.current_project
            
        if not project_id:
            return {"error": "No project specified and no active project context"}
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Get project details
            project = conn.execute(
                'SELECT * FROM projects WHERE id = ?', (project_id,)
            ).fetchone()
            
            if not project:
                return {"error": f"Project {project_id} not found"}
            
            start_time = time.time()
            health_checks = json.loads(project['health_checks'])
            
            results = {
                'project_id': project_id,
                'project_name': project['name'],
                'status': 'unknown',
                'checks_passed': 0,
                'checks_failed': 0,
                'total_checks': len(health_checks),
                'issues': [],
                'check_details': [],
                'response_time_ms': 0
            }
            
            # Run health checks
            for check in health_checks:
                check_result = self._run_health_check(check, project)
                results['check_details'].append(check_result)
                
                if check_result['passed']:
                    results['checks_passed'] += 1
                else:
                    results['checks_failed'] += 1
                    results['issues'].append({
                        'check': check['name'],
                        'issue': check_result['error'],
                        'severity': check.get('severity', 'medium')
                    })
            
            # Determine overall status
            if results['checks_failed'] == 0:
                results['status'] = 'healthy'
            elif results['checks_failed'] <= results['total_checks'] * 0.3:
                results['status'] = 'warning'
            else:
                results['status'] = 'critical'
            
            results['response_time_ms'] = (time.time() - start_time) * 1000
            
            # Store health check result
            conn.execute('''
                INSERT INTO project_health 
                (project_id, status, checks_passed, checks_failed, total_checks, 
                 issues, response_time_ms, check_details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_id, results['status'], results['checks_passed'],
                results['checks_failed'], results['total_checks'],
                json.dumps(results['issues']), results['response_time_ms'],
                json.dumps(results['check_details'])
            ))
            
            # Update project last health check
            conn.execute('''
                UPDATE projects 
                SET last_health_check = CURRENT_TIMESTAMP, 
                    status = CASE 
                        WHEN ? = 'critical' THEN 'error'
                        WHEN ? = 'warning' THEN 'maintenance'
                        ELSE status
                    END
                WHERE id = ?
            ''', (results['status'], results['status'], project_id))
            
            conn.commit()
            
            logger.info(f"🔍 Health check completed for {project['name']}: {results['status']}")
            return results
            
        finally:
            conn.close()
    
    def _run_health_check(self, check: Dict[str, Any], project: sqlite3.Row) -> Dict[str, Any]:
        """Run individual health check"""
        check_type = check.get('type', 'http')
        
        try:
            if check_type == 'http':
                return self._health_check_http(check)
            elif check_type == 'script':
                return self._health_check_script(check, project)
            elif check_type == 'file_exists':
                return self._health_check_file_exists(check, project)
            elif check_type == 'service':
                return self._health_check_service(check)
            else:
                return {
                    'check': check.get('name', 'unknown'),
                    'passed': False,
                    'error': f'Unknown check type: {check_type}'
                }
                
        except Exception as e:
            return {
                'check': check.get('name', 'unknown'),
                'passed': False,
                'error': str(e)
            }
    
    def _health_check_http(self, check: Dict[str, Any]) -> Dict[str, Any]:
        """HTTP endpoint health check"""
        url = check['url']
        expected_status = check.get('expected_status', 200)
        timeout = check.get('timeout', 10)
        
        try:
            response = requests.get(url, timeout=timeout)
            passed = response.status_code == expected_status
            
            return {
                'check': check['name'],
                'passed': passed,
                'response_code': response.status_code,
                'response_time': response.elapsed.total_seconds() * 1000,
                'error': None if passed else f'Expected {expected_status}, got {response.status_code}'
            }
            
        except Exception as e:
            return {
                'check': check['name'],
                'passed': False,
                'error': str(e)
            }
    
    def _health_check_script(self, check: Dict[str, Any], project: sqlite3.Row) -> Dict[str, Any]:
        """Script-based health check"""
        script_path = check['script_path']
        
        # Make path relative to project if needed
        if not Path(script_path).is_absolute() and project['git_repo_path']:
            script_path = Path(project['git_repo_path']) / script_path
        
        try:
            result = subprocess.run(
                [script_path], 
                capture_output=True, 
                text=True, 
                timeout=check.get('timeout', 30)
            )
            
            passed = result.returncode == 0
            
            return {
                'check': check['name'],
                'passed': passed,
                'exit_code': result.returncode,
                'stdout': result.stdout[:500],  # Limit output
                'stderr': result.stderr[:500] if result.stderr else None,
                'error': result.stderr if not passed else None
            }
            
        except Exception as e:
            return {
                'check': check['name'],
                'passed': False,
                'error': str(e)
            }
    
    def _health_check_file_exists(self, check: Dict[str, Any], project: sqlite3.Row) -> Dict[str, Any]:
        """File existence check"""
        file_path = check['file_path']
        
        # Make path relative to project if needed
        if not Path(file_path).is_absolute() and project['git_repo_path']:
            file_path = Path(project['git_repo_path']) / file_path
        
        try:
            exists = Path(file_path).exists()
            
            return {
                'check': check['name'],
                'passed': exists,
                'file_path': str(file_path),
                'error': f"File not found: {file_path}" if not exists else None
            }
            
        except Exception as e:
            return {
                'check': check['name'],
                'passed': False,
                'error': str(e)
            }
    
    def _health_check_service(self, check: Dict[str, Any]) -> Dict[str, Any]:
        """Service status check"""
        service_name = check['service_name']
        
        try:
            # Check if service is running (Linux systemctl)
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True,
                text=True
            )
            
            is_active = result.returncode == 0 and 'active' in result.stdout
            
            return {
                'check': check['name'],
                'passed': is_active,
                'service_status': result.stdout.strip(),
                'error': f"Service {service_name} is not active" if not is_active else None
            }
            
        except Exception as e:
            return {
                'check': check['name'],
                'passed': False,
                'error': str(e)
            }
    
    def backup_project(self, project_id: Optional[str] = None, 
                      backup_type: str = "full",
                      backup_path: Optional[str] = None) -> str:
        """Complete project backup including configs"""
        if not project_id:
            project_id = self.current_project
            
        if not project_id:
            raise ValueError("No project specified and no active project context")
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Get project details
            project = conn.execute(
                'SELECT * FROM projects WHERE id = ?', (project_id,)
            ).fetchone()
            
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Generate backup path
            if not backup_path:
                backup_dir = Path("data/project_backups") / project[1]
                backup_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = backup_dir / f"{backup_type}_backup_{timestamp}.tar.gz"
            
            backup_id = hashlib.md5(f"{project_id}{backup_type}{time.time()}".encode()).hexdigest()
            
            # Create backup based on type
            if backup_type == "full":
                backup_size = self._create_full_backup(project, backup_path)
            elif backup_type == "config_only":
                backup_size = self._create_config_backup(project_id, backup_path, conn)
            elif backup_type == "data_only":
                backup_size = self._create_data_backup(project, backup_path)
            else:
                raise ValueError(f"Unknown backup type: {backup_type}")
            
            # Record backup
            conn.execute('''
                INSERT INTO project_backups 
                (id, project_id, backup_path, backup_type, size_mb, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                backup_id, project_id, str(backup_path), backup_type, 
                backup_size, json.dumps({'created_by': 'project_management_system'})
            ))
            
            conn.commit()
            
            logger.info(f"💾 Project backup created: {backup_path} ({backup_size:.1f}MB)")
            return backup_id
            
        finally:
            conn.close()
    
    def _create_full_backup(self, project: sqlite3.Row, backup_path: Path) -> float:
        """Create full project backup"""
        if not project[4]:  # git_repo_path
            raise ValueError("Project has no git repository path for full backup")
        
        repo_path = Path(project[4])
        
        # Create tar.gz backup
        import tarfile
        
        with tarfile.open(backup_path, 'w:gz') as tar:
            tar.add(repo_path, arcname=project[1])
        
        return backup_path.stat().st_size / (1024 * 1024)  # Size in MB
    
    def _create_config_backup(self, project_id: str, backup_path: Path, conn: sqlite3.Connection) -> float:
        """Create configuration-only backup"""
        # Get all project configurations
        configs = conn.execute('''
            SELECT config_type, config_name, config_data 
            FROM project_configs 
            WHERE project_id = ?
        ''', (project_id,)).fetchall()
        
        # Create config backup
        backup_data = {
            'project_id': project_id,
            'backup_type': 'config_only',
            'created_at': datetime.now().isoformat(),
            'configurations': [
                {
                    'type': config[0],
                    'name': config[1],
                    'data': json.loads(config[2])
                }
                for config in configs
            ]
        }
        
        # Write to compressed JSON
        import gzip
        
        with gzip.open(backup_path, 'wt') as f:
            json.dump(backup_data, f, indent=2)
        
        return backup_path.stat().st_size / (1024 * 1024)  # Size in MB
    
    def _create_data_backup(self, project: sqlite3.Row, backup_path: Path) -> float:
        """Create data-only backup"""
        # This would backup project-specific data files
        # For now, create a minimal backup
        
        backup_data = {
            'project_id': project[0],
            'project_name': project[1],
            'backup_type': 'data_only',
            'created_at': datetime.now().isoformat(),
            'note': 'Data-only backup - implement specific data collection logic'
        }
        
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        return backup_path.stat().st_size / (1024 * 1024)  # Size in MB
    
    def restore_project(self, backup_id: str, target_project_id: Optional[str] = None) -> bool:
        """Restore project state from backup"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Get backup details
            backup = conn.execute('''
                SELECT pb.*, p.name as project_name 
                FROM project_backups pb
                JOIN projects p ON pb.project_id = p.id
                WHERE pb.id = ?
            ''', (backup_id,)).fetchone()
            
            if not backup:
                logger.error(f"❌ Backup {backup_id} not found")
                return False
            
            backup_path = Path(backup[2])  # backup_path column
            backup_type = backup[3]       # backup_type column
            source_project_id = backup[1] # project_id column
            
            if not backup_path.exists():
                logger.error(f"❌ Backup file not found: {backup_path}")
                return False
            
            # Use source project if no target specified
            if not target_project_id:
                target_project_id = source_project_id
            
            # Restore based on backup type
            if backup_type == "full":
                success = self._restore_full_backup(backup_path, target_project_id, conn)
            elif backup_type == "config_only":
                success = self._restore_config_backup(backup_path, target_project_id, conn)
            elif backup_type == "data_only":
                success = self._restore_data_backup(backup_path, target_project_id, conn)
            else:
                logger.error(f"❌ Unknown backup type: {backup_type}")
                return False
            
            if success:
                # Update project status
                conn.execute('''
                    UPDATE projects 
                    SET updated_at = CURRENT_TIMESTAMP, status = 'active'
                    WHERE id = ?
                ''', (target_project_id,))
                
                conn.commit()
                logger.info(f"✅ Project restored from backup: {backup[6]} -> {target_project_id}")
            
            return success
            
        finally:
            conn.close()
    
    def _restore_full_backup(self, backup_path: Path, project_id: str, conn: sqlite3.Connection) -> bool:
        """Restore full project backup"""
        try:
            # Get project repo path
            project = conn.execute('SELECT git_repo_path FROM projects WHERE id = ?', (project_id,)).fetchone()
            if not project or not project[0]:
                logger.error(f"❌ Project {project_id} has no git repository path")
                return False
            
            repo_path = Path(project[0])
            
            # Extract backup
            import tarfile
            
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(repo_path.parent)
            
            logger.info(f"✅ Full backup restored to: {repo_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to restore full backup: {e}")
            return False
    
    def _restore_config_backup(self, backup_path: Path, project_id: str, conn: sqlite3.Connection) -> bool:
        """Restore configuration backup"""
        try:
            # Load backup data
            import gzip
            
            with gzip.open(backup_path, 'rt') as f:
                backup_data = json.load(f)
            
            # Clear existing configurations
            conn.execute('DELETE FROM project_configs WHERE project_id = ?', (project_id,))
            
            # Restore configurations
            for config in backup_data.get('configurations', []):
                config_hash = hashlib.md5(json.dumps(config['data']).encode()).hexdigest()
                
                conn.execute('''
                    INSERT INTO project_configs 
                    (project_id, config_type, config_name, config_data, config_hash)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    project_id, config['type'], config['name'],
                    json.dumps(config['data']), config_hash
                ))
            
            conn.commit()
            logger.info(f"✅ Configuration backup restored: {len(backup_data.get('configurations', []))} configs")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to restore config backup: {e}")
            return False
    
    def _restore_data_backup(self, backup_path: Path, project_id: str, conn: sqlite3.Connection) -> bool:
        """Restore data backup"""
        try:
            # Load backup data
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)
            
            logger.info(f"✅ Data backup restored (placeholder): {backup_data.get('note', '')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to restore data backup: {e}")
            return False
    
    def _run_project_script(self, script_path: str, project_id: str):
        """Run project setup/cleanup script"""
        try:
            result = subprocess.run(
                [script_path],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                env={**dict(os.environ), 'PROJECT_ID': project_id}
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Script executed successfully: {script_path}")
            else:
                logger.warning(f"⚠️ Script failed: {script_path} (exit code: {result.returncode})")
                logger.warning(f"Error output: {result.stderr}")
                
        except Exception as e:
            logger.error(f"❌ Failed to run script {script_path}: {e}")
    
    # ===== UTILITY METHODS =====
    
    def get_current_project(self) -> Optional[Dict[str, Any]]:
        """Get current project context"""
        if not self.current_project:
            return None
        
        if self.current_project in self.project_cache:
            return self.project_cache[self.current_project]
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            project = conn.execute(
                'SELECT * FROM projects WHERE id = ?', (self.current_project,)
            ).fetchone()
            
            if project:
                project_dict = dict(project)
                self.project_cache[self.current_project] = project_dict
                return project_dict
            
            return None
            
        finally:
            conn.close()
    
    def get_project_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get project management analytics"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            since_date = datetime.now() - timedelta(days=days)
            
            analytics = {
                'total_projects': 0,
                'active_projects': 0,
                'health_summary': {},
                'backup_summary': {},
                'recent_activity': []
            }
            
            # Project counts
            counts = conn.execute('''
                SELECT status, COUNT(*) as count 
                FROM projects 
                GROUP BY status
            ''').fetchall()
            
            for row in counts:
                if row['status'] == 'active':
                    analytics['active_projects'] = row['count']
                analytics['total_projects'] += row['count']
            
            # Health summary
            health_stats = conn.execute('''
                SELECT status, COUNT(*) as count
                FROM project_health 
                WHERE created_at >= ?
                GROUP BY status
            ''', (since_date,)).fetchall()
            
            analytics['health_summary'] = {row['status']: row['count'] for row in health_stats}
            
            # Backup summary
            backup_stats = conn.execute('''
                SELECT backup_type, COUNT(*) as count, SUM(size_mb) as total_size
                FROM project_backups 
                WHERE created_at >= ?
                GROUP BY backup_type
            ''', (since_date,)).fetchall()
            
            analytics['backup_summary'] = {
                row['backup_type']: {
                    'count': row['count'],
                    'total_size_mb': row['total_size']
                }
                for row in backup_stats
            }
            
            return analytics
            
        finally:
            conn.close()