"""
Agent Kanban System for hAIveMind DevOps Memory System

This module provides a comprehensive kanban board system for managing tasks 
across multiple AI agents with capability-based assignment, WIP limits, 
dependency tracking, and real-time collaboration features.

Features:
- Agent registration and capability tracking
- Task creation with priority, dependencies, and time estimates  
- Intelligent task assignment based on agent capabilities
- Kanban board with customizable columns and WIP limits
- Real-time updates and collaborative editing
- Performance analytics and SLA monitoring
- Task dependency management and blocking
"""

import sqlite3
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import uuid
import hashlib
from enum import Enum

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    BACKLOG = "backlog"
    ASSIGNED = "assigned" 
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AgentStatus(Enum):
    ACTIVE = "active"
    BUSY = "busy"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"

@dataclass
class AgentCapability:
    name: str
    level: int  # 1-5 proficiency level
    description: str
    
@dataclass
class Agent:
    id: str
    name: str
    machine_id: str
    status: AgentStatus
    capabilities: List[AgentCapability]
    current_workload: int
    max_workload: int
    last_seen: datetime
    metadata: Dict[str, Any]
    
@dataclass 
class Task:
    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assigned_agent: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
    due_date: Optional[datetime]
    estimated_hours: Optional[int]
    actual_hours: Optional[int]
    dependencies: List[str]  # List of task IDs this task depends on
    blocked_by: List[str]    # List of task IDs blocking this task
    tags: List[str]
    metadata: Dict[str, Any]

@dataclass
class KanbanBoard:
    id: str
    name: str
    columns: List[str]
    wip_limits: Dict[str, int]  # Column name -> WIP limit
    agents: List[str]           # Agent IDs on this board
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class TaskDependency:
    id: str
    source_task: str
    target_task: str
    dependency_type: str  # "blocks", "requires", "subtask"
    created_at: datetime

class AgentKanbanSystem:
    """Agent Kanban Task Management System with intelligent assignment and collaboration"""
    
    def __init__(self, db_path: str = "data/agent_kanban.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        logger.info("📊 Agent Kanban system initialized")
    
    def _init_database(self):
        """Initialize the SQLite database with comprehensive kanban schema"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        
        try:
            # Agent Registry Table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    machine_id TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('active', 'busy', 'offline', 'maintenance')),
                    current_workload INTEGER DEFAULT 0,
                    max_workload INTEGER DEFAULT 5,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Agent Capabilities Table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS agent_capabilities (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    agent_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    level INTEGER NOT NULL CHECK (level BETWEEN 1 AND 5),
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (agent_id) REFERENCES agents (id) ON DELETE CASCADE,
                    UNIQUE (agent_id, name)
                )
            ''')
            
            # Kanban Boards Table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS kanban_boards (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    name TEXT NOT NULL UNIQUE,
                    columns TEXT DEFAULT '["backlog", "assigned", "in_progress", "review", "done"]',
                    wip_limits TEXT DEFAULT '{}',
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Board Agents Association Table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS board_agents (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    board_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (board_id) REFERENCES kanban_boards (id) ON DELETE CASCADE,
                    FOREIGN KEY (agent_id) REFERENCES agents (id) ON DELETE CASCADE,
                    UNIQUE (board_id, agent_id)
                )
            ''')
            
            # Agent Tasks Table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS agent_tasks (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL DEFAULT 'backlog' CHECK (status IN ('backlog', 'assigned', 'in_progress', 'review', 'done', 'blocked', 'cancelled')),
                    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
                    assigned_agent TEXT,
                    created_by TEXT NOT NULL,
                    board_id TEXT DEFAULT NULL,
                    due_date TIMESTAMP,
                    estimated_hours INTEGER,
                    actual_hours INTEGER,
                    tags TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (assigned_agent) REFERENCES agents (id) ON SET NULL,
                    FOREIGN KEY (board_id) REFERENCES kanban_boards (id) ON SET NULL
                )
            ''')
            
            # Task Dependencies Table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    source_task TEXT NOT NULL,
                    target_task TEXT NOT NULL,
                    dependency_type TEXT DEFAULT 'blocks' CHECK (dependency_type IN ('blocks', 'requires', 'subtask')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_task) REFERENCES agent_tasks (id) ON DELETE CASCADE,
                    FOREIGN KEY (target_task) REFERENCES agent_tasks (id) ON DELETE CASCADE,
                    UNIQUE (source_task, target_task, dependency_type)
                )
            ''')
            
            # Task History Table (for audit trail)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS task_history (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    task_id TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    changed_by TEXT,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES agent_tasks (id) ON DELETE CASCADE
                )
            ''')
            
            # Task Time Tracking Table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS task_time_entries (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    task_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    duration_minutes INTEGER,
                    description TEXT,
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES agent_tasks (id) ON DELETE CASCADE,
                    FOREIGN KEY (agent_id) REFERENCES agents (id) ON DELETE CASCADE
                )
            ''')
            
            # Create optimized indexes for performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_agents_machine_status ON agents (machine_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_agents_workload ON agents (current_workload, max_workload)",
                "CREATE INDEX IF NOT EXISTS idx_capabilities_agent_name ON agent_capabilities (agent_id, name)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_status_priority ON agent_tasks (status, priority)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_assigned_agent ON agent_tasks (assigned_agent)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON agent_tasks (created_at)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_board_status ON agent_tasks (board_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_dependencies_source ON task_dependencies (source_task)",
                "CREATE INDEX IF NOT EXISTS idx_dependencies_target ON task_dependencies (target_task)",
                "CREATE INDEX IF NOT EXISTS idx_history_task_time ON task_history (task_id, changed_at)",
                "CREATE INDEX IF NOT EXISTS idx_time_entries_task_agent ON task_time_entries (task_id, agent_id)",
                "CREATE INDEX IF NOT EXISTS idx_time_entries_start_time ON task_time_entries (start_time)"
            ]
            
            for index_sql in indexes:
                conn.execute(index_sql)
            
            # Create default kanban board
            conn.execute('''
                INSERT OR IGNORE INTO kanban_boards (id, name, columns, wip_limits) 
                VALUES ('default', 'Default Board', '["backlog", "assigned", "in_progress", "review", "done"]', '{"in_progress": 3, "review": 2}')
            ''')
            
            conn.commit()
            logger.info("📊 Agent Kanban database schema initialized")
            
        finally:
            conn.close()
    
    # ===== AGENT MANAGEMENT =====
    
    def register_agent(self, agent_id: str, name: str, machine_id: str, 
                      capabilities: List[Dict[str, Any]], max_workload: int = 5,
                      metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Register a new agent with capabilities"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        
        try:
            # Insert agent
            conn.execute('''
                INSERT OR REPLACE INTO agents (id, name, machine_id, status, max_workload, metadata)
                VALUES (?, ?, ?, 'active', ?, ?)
            ''', (agent_id, name, machine_id, max_workload, json.dumps(metadata or {})))
            
            # Clear existing capabilities
            conn.execute("DELETE FROM agent_capabilities WHERE agent_id = ?", (agent_id,))
            
            # Insert capabilities
            for cap in capabilities:
                conn.execute('''
                    INSERT INTO agent_capabilities (agent_id, name, level, description)
                    VALUES (?, ?, ?, ?)
                ''', (agent_id, cap['name'], cap.get('level', 3), cap.get('description', '')))
            
            conn.commit()
            logger.info(f"📊 Agent {name} registered with {len(capabilities)} capabilities")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Failed to register agent: {e}")
            return False
        finally:
            conn.close()
    
    def update_agent_status(self, agent_id: str, status: AgentStatus, 
                           current_workload: Optional[int] = None) -> bool:
        """Update agent status and workload"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            if current_workload is not None:
                conn.execute('''
                    UPDATE agents SET status = ?, current_workload = ?, 
                                    last_seen = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status.value, current_workload, agent_id))
            else:
                conn.execute('''
                    UPDATE agents SET status = ?, last_seen = CURRENT_TIMESTAMP, 
                                    updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status.value, agent_id))
            
            conn.commit()
            return conn.rowcount > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to update agent status: {e}")
            return False
        finally:
            conn.close()
    
    def get_available_agents(self, required_capabilities: Optional[List[str]] = None,
                           min_capability_level: int = 1) -> List[Dict[str, Any]]:
        """Get available agents with optional capability filtering"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            if required_capabilities:
                # Complex query to find agents with all required capabilities
                placeholders = ','.join(['?' for _ in required_capabilities])
                sql = f'''
                    SELECT a.*, GROUP_CONCAT(ac.name || ':' || ac.level) as capabilities_str
                    FROM agents a
                    LEFT JOIN agent_capabilities ac ON a.id = ac.agent_id
                    WHERE a.status = 'active' AND a.current_workload < a.max_workload
                    AND a.id IN (
                        SELECT agent_id FROM agent_capabilities 
                        WHERE name IN ({placeholders}) AND level >= ?
                        GROUP BY agent_id
                        HAVING COUNT(DISTINCT name) = ?
                    )
                    GROUP BY a.id
                    ORDER BY a.current_workload ASC, a.last_seen DESC
                '''
                cursor = conn.execute(sql, required_capabilities + [min_capability_level, len(required_capabilities)])
            else:
                cursor = conn.execute('''
                    SELECT a.*, GROUP_CONCAT(ac.name || ':' || ac.level) as capabilities_str
                    FROM agents a
                    LEFT JOIN agent_capabilities ac ON a.id = ac.agent_id
                    WHERE a.status = 'active' AND a.current_workload < a.max_workload
                    GROUP BY a.id
                    ORDER BY a.current_workload ASC, a.last_seen DESC
                ''')
            
            agents = []
            for row in cursor.fetchall():
                agent_data = dict(row)
                if agent_data['capabilities_str']:
                    caps = []
                    for cap_str in agent_data['capabilities_str'].split(','):
                        name, level = cap_str.split(':')
                        caps.append({'name': name, 'level': int(level)})
                    agent_data['capabilities'] = caps
                else:
                    agent_data['capabilities'] = []
                del agent_data['capabilities_str']
                agents.append(agent_data)
            
            return agents
            
        finally:
            conn.close()
    
    # ===== TASK MANAGEMENT =====
    
    def create_task(self, title: str, description: str, created_by: str,
                   priority: TaskPriority = TaskPriority.MEDIUM,
                   board_id: str = "default", dependencies: Optional[List[str]] = None,
                   estimated_hours: Optional[int] = None, due_date: Optional[datetime] = None,
                   tags: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new task"""
        task_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        
        try:
            # Insert task
            conn.execute('''
                INSERT INTO agent_tasks (id, title, description, priority, created_by, board_id,
                                       estimated_hours, due_date, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (task_id, title, description, priority.value, created_by, board_id,
                  estimated_hours, due_date, json.dumps(tags or []), json.dumps(metadata or {})))
            
            # Add dependencies
            if dependencies:
                for dep_id in dependencies:
                    conn.execute('''
                        INSERT INTO task_dependencies (source_task, target_task, dependency_type)
                        VALUES (?, ?, 'blocks')
                    ''', (dep_id, task_id))
            
            conn.commit()
            logger.info(f"📊 Task '{title}' created with ID {task_id}")
            return task_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Failed to create task: {e}")
            raise
        finally:
            conn.close()
    
    def assign_task(self, task_id: str, agent_id: Optional[str] = None,
                   auto_assign: bool = True) -> bool:
        """Assign task to agent (auto-assign finds best available agent)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Get task details
            task = conn.execute('SELECT * FROM agent_tasks WHERE id = ?', (task_id,)).fetchone()
            if not task:
                logger.error(f"❌ Task {task_id} not found")
                return False
            
            # Check if task has blocking dependencies
            blocking_deps = conn.execute('''
                SELECT COUNT(*) as blocked_count FROM task_dependencies td
                JOIN agent_tasks at ON td.source_task = at.id
                WHERE td.target_task = ? AND at.status NOT IN ('done', 'cancelled')
            ''', (task_id,)).fetchone()['blocked_count']
            
            if blocking_deps > 0:
                logger.warning(f"⚠️ Task {task_id} has {blocking_deps} blocking dependencies")
                return False
            
            if auto_assign and not agent_id:
                # Find best available agent
                # TODO: Add capability-based matching logic here
                available_agents = conn.execute('''
                    SELECT id FROM agents WHERE status = 'active' AND current_workload < max_workload
                    ORDER BY current_workload ASC, last_seen DESC LIMIT 1
                ''').fetchone()
                
                if not available_agents:
                    logger.warning("⚠️ No available agents for auto-assignment")
                    return False
                    
                agent_id = available_agents['id']
            
            if not agent_id:
                logger.error("❌ No agent specified for task assignment")
                return False
            
            # Assign task and update workload
            conn.execute('BEGIN TRANSACTION')
            
            conn.execute('''
                UPDATE agent_tasks SET assigned_agent = ?, status = 'assigned', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (agent_id, task_id))
            
            conn.execute('''
                UPDATE agents SET current_workload = current_workload + 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (agent_id,))
            
            # Add to task history
            conn.execute('''
                INSERT INTO task_history (task_id, field_name, new_value, changed_by)
                VALUES (?, 'assigned_agent', ?, 'system')
            ''', (task_id, agent_id))
            
            conn.commit()
            logger.info(f"📊 Task {task_id} assigned to agent {agent_id}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Failed to assign task: {e}")
            return False
        finally:
            conn.close()
    
    def move_task(self, task_id: str, new_status: TaskStatus, moved_by: str) -> bool:
        """Move task to different status/column"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Get current task state
            task = conn.execute('SELECT * FROM agent_tasks WHERE id = ?', (task_id,)).fetchone()
            if not task:
                return False
            
            old_status = task['status']
            
            # Check WIP limits if moving to in_progress or review
            if new_status in [TaskStatus.IN_PROGRESS, TaskStatus.REVIEW]:
                board_id = task['board_id'] or 'default'
                board = conn.execute('SELECT wip_limits FROM kanban_boards WHERE id = ?', (board_id,)).fetchone()
                if board:
                    wip_limits = json.loads(board['wip_limits'])
                    limit = wip_limits.get(new_status.value)
                    if limit:
                        current_count = conn.execute('''
                            SELECT COUNT(*) as count FROM agent_tasks 
                            WHERE board_id = ? AND status = ?
                        ''', (board_id, new_status.value)).fetchone()['count']
                        
                        if current_count >= limit:
                            logger.warning(f"⚠️ WIP limit reached for {new_status.value} ({current_count}/{limit})")
                            return False
            
            # Update task status
            conn.execute('BEGIN TRANSACTION')
            
            conn.execute('''
                UPDATE agent_tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
            ''', (new_status.value, task_id))
            
            # Update agent workload when task is completed or cancelled
            if new_status in [TaskStatus.DONE, TaskStatus.CANCELLED] and task['assigned_agent']:
                conn.execute('''
                    UPDATE agents SET current_workload = MAX(0, current_workload - 1)
                    WHERE id = ?
                ''', (task['assigned_agent'],))
            
            # Add to history
            conn.execute('''
                INSERT INTO task_history (task_id, field_name, old_value, new_value, changed_by)
                VALUES (?, 'status', ?, ?, ?)
            ''', (task_id, old_status, new_status.value, moved_by))
            
            conn.commit()
            logger.info(f"📊 Task {task_id} moved from {old_status} to {new_status.value}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Failed to move task: {e}")
            return False
        finally:
            conn.close()
    
    def get_kanban_board(self, board_id: str = "default", include_metrics: bool = True) -> Dict[str, Any]:
        """Get complete kanban board state"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Get board info
            board = conn.execute('SELECT * FROM kanban_boards WHERE id = ?', (board_id,)).fetchone()
            if not board:
                return {}
            
            columns = json.loads(board['columns'])
            wip_limits = json.loads(board['wip_limits'])
            
            # Get tasks by column
            board_data = {
                'id': board['id'],
                'name': board['name'],
                'columns': columns,
                'wip_limits': wip_limits,
                'tasks': {},
                'agents': []
            }
            
            # Get all tasks for this board
            tasks = conn.execute('''
                SELECT t.*, a.name as agent_name FROM agent_tasks t
                LEFT JOIN agents a ON t.assigned_agent = a.id
                WHERE t.board_id = ? OR (t.board_id IS NULL AND ? = 'default')
                ORDER BY t.priority DESC, t.created_at ASC
            ''', (board_id, board_id)).fetchall()
            
            # Group tasks by status
            for column in columns:
                board_data['tasks'][column] = []
            
            for task in tasks:
                task_data = dict(task)
                task_data['tags'] = json.loads(task_data.get('tags', '[]'))
                task_data['metadata'] = json.loads(task_data.get('metadata', '{}'))
                
                status = task_data['status']
                if status in board_data['tasks']:
                    board_data['tasks'][status].append(task_data)
            
            # Get board agents
            agents = conn.execute('''
                SELECT a.* FROM agents a
                JOIN board_agents ba ON a.id = ba.agent_id
                WHERE ba.board_id = ?
            ''', (board_id,)).fetchall()
            
            board_data['agents'] = [dict(agent) for agent in agents]
            
            if include_metrics:
                board_data['metrics'] = self._get_board_metrics(board_id, conn)
            
            return board_data
            
        finally:
            conn.close()
    
    def _get_board_metrics(self, board_id: str, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Calculate board performance metrics"""
        metrics = {}
        
        # Task counts by status
        status_counts = conn.execute('''
            SELECT status, COUNT(*) as count FROM agent_tasks 
            WHERE board_id = ? OR (board_id IS NULL AND ? = 'default')
            GROUP BY status
        ''', (board_id, board_id)).fetchall()
        
        metrics['status_counts'] = {row['status']: row['count'] for row in status_counts}
        
        # Average cycle time (created to done)
        cycle_times = conn.execute('''
            SELECT AVG(julianday(updated_at) - julianday(created_at)) * 24 as avg_cycle_hours
            FROM agent_tasks 
            WHERE status = 'done' AND (board_id = ? OR (board_id IS NULL AND ? = 'default'))
        ''', (board_id, board_id)).fetchone()
        
        metrics['avg_cycle_time_hours'] = cycle_times['avg_cycle_hours'] or 0
        
        # Throughput (tasks completed in last 7 days)
        throughput = conn.execute('''
            SELECT COUNT(*) as completed_count FROM agent_tasks
            WHERE status = 'done' AND updated_at >= datetime('now', '-7 days')
            AND (board_id = ? OR (board_id IS NULL AND ? = 'default'))
        ''', (board_id, board_id)).fetchone()
        
        metrics['weekly_throughput'] = throughput['completed_count']
        
        return metrics
    
    # ===== REPORTING AND ANALYTICS =====
    
    def get_agent_workload_report(self) -> List[Dict[str, Any]]:
        """Generate agent workload and performance report"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            agents = conn.execute('''
                SELECT a.*, 
                       COUNT(t.id) as total_tasks,
                       COUNT(CASE WHEN t.status = 'done' THEN 1 END) as completed_tasks,
                       COUNT(CASE WHEN t.status IN ('assigned', 'in_progress') THEN 1 END) as active_tasks,
                       AVG(CASE WHEN t.status = 'done' THEN julianday(t.updated_at) - julianday(t.created_at) END) * 24 as avg_completion_hours
                FROM agents a
                LEFT JOIN agent_tasks t ON a.id = t.assigned_agent
                GROUP BY a.id
                ORDER BY a.current_workload DESC
            ''').fetchall()
            
            return [dict(agent) for agent in agents]
            
        finally:
            conn.close()
    
    def get_task_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get task analytics for the specified time period"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            since_date = datetime.now() - timedelta(days=days)
            
            # Task creation trends
            creation_trends = conn.execute('''
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM agent_tasks 
                WHERE created_at >= ?
                GROUP BY DATE(created_at)
                ORDER BY date
            ''', (since_date,)).fetchall()
            
            # Completion trends  
            completion_trends = conn.execute('''
                SELECT DATE(updated_at) as date, COUNT(*) as count
                FROM agent_tasks
                WHERE status = 'done' AND updated_at >= ?
                GROUP BY DATE(updated_at)
                ORDER BY date
            ''', (since_date,)).fetchall()
            
            # Priority distribution
            priority_dist = conn.execute('''
                SELECT priority, COUNT(*) as count
                FROM agent_tasks
                WHERE created_at >= ?
                GROUP BY priority
            ''', (since_date,)).fetchall()
            
            return {
                'creation_trends': [dict(row) for row in creation_trends],
                'completion_trends': [dict(row) for row in completion_trends],
                'priority_distribution': [dict(row) for row in priority_dist]
            }
            
        finally:
            conn.close()