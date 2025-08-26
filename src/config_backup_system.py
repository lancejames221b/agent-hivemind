"""
Config Backup System - Database Schema and Core Operations

Provides comprehensive configuration tracking, versioning, and drift detection
for hAIveMind distributed infrastructure management.
"""

import sqlite3
import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import asyncio
import difflib
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ConfigSnapshot:
    """Configuration snapshot data structure"""
    id: Optional[str] = None
    system_id: str = ""
    config_type: str = ""
    config_content: str = ""
    config_hash: str = ""
    timestamp: str = ""
    agent_id: str = ""
    metadata: Dict[str, Any] = None
    file_path: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.config_hash and self.config_content:
            self.config_hash = hashlib.sha256(self.config_content.encode()).hexdigest()
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

@dataclass
class ConfigDiff:
    """Configuration difference data structure"""
    id: Optional[str] = None
    snapshot_id_before: str = ""
    snapshot_id_after: str = ""
    diff_content: str = ""
    change_type: str = ""  # added, modified, deleted
    risk_score: float = 0.0
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

class ConfigBackupSystem:
    """
    Core configuration backup and tracking system
    
    Features:
    - Configuration versioning with hash-based deduplication
    - Drift detection and alerting
    - Point-in-time restore capabilities
    - Cross-system configuration correlation
    """
    
    def __init__(self, db_path: str = "data/config_backup.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database with optimized schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Systems registry table
                CREATE TABLE IF NOT EXISTS config_systems (
                    system_id TEXT PRIMARY KEY,
                    system_name TEXT NOT NULL,
                    system_type TEXT NOT NULL,  -- nginx, mysql, kubernetes, etc
                    description TEXT,
                    agent_id TEXT,
                    last_backup TEXT,
                    backup_frequency INTEGER DEFAULT 3600,  -- seconds
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'  -- JSON metadata
                );
                
                -- Configuration snapshots table  
                CREATE TABLE IF NOT EXISTS config_snapshots (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    system_id TEXT NOT NULL,
                    config_type TEXT NOT NULL,
                    config_content TEXT NOT NULL,
                    config_hash TEXT NOT NULL,
                    file_path TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    agent_id TEXT,
                    metadata TEXT DEFAULT '{}',  -- JSON metadata
                    size INTEGER,
                    FOREIGN KEY (system_id) REFERENCES config_systems (system_id),
                    UNIQUE (system_id, config_hash)  -- Deduplication
                );
                
                -- Configuration diffs table
                CREATE TABLE IF NOT EXISTS config_diffs (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    snapshot_id_before TEXT,
                    snapshot_id_after TEXT NOT NULL,
                    diff_content TEXT NOT NULL,
                    change_type TEXT NOT NULL,  -- added, modified, deleted, renamed
                    risk_score REAL DEFAULT 0.0,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    lines_added INTEGER DEFAULT 0,
                    lines_removed INTEGER DEFAULT 0,
                    files_changed INTEGER DEFAULT 1,
                    FOREIGN KEY (snapshot_id_before) REFERENCES config_snapshots (id),
                    FOREIGN KEY (snapshot_id_after) REFERENCES config_snapshots (id)
                );
                
                -- Drift detection alerts table
                CREATE TABLE IF NOT EXISTS config_drift_alerts (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    system_id TEXT NOT NULL,
                    drift_type TEXT NOT NULL,  -- unauthorized_change, config_mismatch, etc
                    severity TEXT NOT NULL,   -- low, medium, high, critical
                    description TEXT NOT NULL,
                    snapshot_id TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TEXT,
                    resolved_by TEXT,
                    FOREIGN KEY (system_id) REFERENCES config_systems (system_id),
                    FOREIGN KEY (snapshot_id) REFERENCES config_snapshots (id)
                );
                
                -- Performance indexes
                CREATE INDEX IF NOT EXISTS idx_snapshots_system_time ON config_snapshots (system_id, timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_snapshots_hash ON config_snapshots (config_hash);
                CREATE INDEX IF NOT EXISTS idx_diffs_after ON config_diffs (snapshot_id_after);
                CREATE INDEX IF NOT EXISTS idx_diffs_timestamp ON config_diffs (timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_systems_type ON config_systems (system_type);
                CREATE INDEX IF NOT EXISTS idx_alerts_system ON config_drift_alerts (system_id, resolved);
                CREATE INDEX IF NOT EXISTS idx_alerts_severity ON config_drift_alerts (severity, timestamp DESC);
            """)
            
            logger.info("📊 Config backup database schema initialized")
    
    def register_system(self, system_id: str, system_name: str, system_type: str, 
                       agent_id: str = "", description: str = "", 
                       backup_frequency: int = 3600, metadata: Dict = None) -> bool:
        """Register a new system for configuration tracking"""
        if metadata is None:
            metadata = {}
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO config_systems 
                    (system_id, system_name, system_type, description, agent_id, backup_frequency, metadata, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (system_id, system_name, system_type, description, agent_id, 
                      backup_frequency, json.dumps(metadata), datetime.now().isoformat()))
                
            logger.info(f"📝 Registered system {system_id} ({system_type})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to register system {system_id}: {e}")
            return False
    
    def create_snapshot(self, snapshot: ConfigSnapshot) -> Optional[str]:
        """Create a new configuration snapshot with deduplication"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if identical config already exists (deduplication)
                existing = conn.execute("""
                    SELECT id FROM config_snapshots 
                    WHERE system_id = ? AND config_hash = ?
                    ORDER BY timestamp DESC LIMIT 1
                """, (snapshot.system_id, snapshot.config_hash)).fetchone()
                
                if existing:
                    logger.debug(f"🔄 Config unchanged for {snapshot.system_id}, skipping duplicate")
                    return existing[0]
                
                # Insert new snapshot
                cursor = conn.execute("""
                    INSERT INTO config_snapshots 
                    (system_id, config_type, config_content, config_hash, file_path, agent_id, metadata, size)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (snapshot.system_id, snapshot.config_type, snapshot.config_content,
                      snapshot.config_hash, snapshot.file_path, snapshot.agent_id,
                      json.dumps(snapshot.metadata), len(snapshot.config_content)))
                
                snapshot_id = cursor.lastrowid
                
                # Update system's last backup time
                conn.execute("""
                    UPDATE config_systems SET last_backup = ? WHERE system_id = ?
                """, (datetime.now().isoformat(), snapshot.system_id))
                
                # Create diff if previous snapshot exists
                self._create_diff_if_needed(conn, snapshot_id, snapshot)
                
                logger.info(f"📸 Created config snapshot {snapshot_id} for {snapshot.system_id}")
                return str(snapshot_id)
                
        except Exception as e:
            logger.error(f"❌ Failed to create snapshot for {snapshot.system_id}: {e}")
            return None
    
    def _create_diff_if_needed(self, conn: sqlite3.Connection, new_snapshot_id: str, 
                              new_snapshot: ConfigSnapshot):
        """Create diff between new snapshot and previous one"""
        try:
            # Get previous snapshot
            prev_snapshot = conn.execute("""
                SELECT id, config_content FROM config_snapshots 
                WHERE system_id = ? AND id != ?
                ORDER BY timestamp DESC LIMIT 1
            """, (new_snapshot.system_id, new_snapshot_id)).fetchone()
            
            if not prev_snapshot:
                return  # First snapshot, no diff needed
                
            prev_id, prev_content = prev_snapshot
            
            # Calculate diff
            diff_lines = list(difflib.unified_diff(
                prev_content.splitlines(keepends=True),
                new_snapshot.config_content.splitlines(keepends=True),
                fromfile=f"previous/{new_snapshot.system_id}",
                tofile=f"current/{new_snapshot.system_id}",
                n=3
            ))
            
            if not diff_lines:
                return  # No changes
                
            diff_content = ''.join(diff_lines)
            
            # Count changes
            lines_added = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
            lines_removed = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
            
            # Calculate risk score based on change magnitude
            total_changes = lines_added + lines_removed
            total_lines = len(new_snapshot.config_content.splitlines())
            change_ratio = total_changes / max(total_lines, 1)
            risk_score = min(1.0, change_ratio * 2)  # Scale to 0-1
            
            # Determine change type
            if lines_added > 0 and lines_removed > 0:
                change_type = "modified"
            elif lines_added > 0:
                change_type = "added"  
            else:
                change_type = "deleted"
                
            # Insert diff record
            conn.execute("""
                INSERT INTO config_diffs 
                (snapshot_id_before, snapshot_id_after, diff_content, change_type, 
                 risk_score, lines_added, lines_removed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (prev_id, new_snapshot_id, diff_content, change_type, 
                  risk_score, lines_added, lines_removed))
            
            logger.info(f"📊 Created diff: {change_type}, risk: {risk_score:.2f}, +{lines_added}/-{lines_removed}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create diff: {e}")
    
    def get_system_history(self, system_id: str, limit: int = 50) -> List[Dict]:
        """Get configuration history for a system"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                rows = conn.execute("""
                    SELECT s.*, d.change_type, d.risk_score, d.lines_added, d.lines_removed
                    FROM config_snapshots s
                    LEFT JOIN config_diffs d ON s.id = d.snapshot_id_after
                    WHERE s.system_id = ?
                    ORDER BY s.timestamp DESC
                    LIMIT ?
                """, (system_id, limit)).fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Failed to get history for {system_id}: {e}")
            return []
    
    def get_current_config(self, system_id: str) -> Optional[Dict]:
        """Get the most recent configuration for a system"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                row = conn.execute("""
                    SELECT * FROM config_snapshots 
                    WHERE system_id = ?
                    ORDER BY timestamp DESC LIMIT 1
                """, (system_id,)).fetchone()
                
                return dict(row) if row else None
                
        except Exception as e:
            logger.error(f"❌ Failed to get current config for {system_id}: {e}")
            return None
    
    def detect_drift(self, system_id: str = None, hours_back: int = 24) -> List[Dict]:
        """Detect configuration drift and potential issues"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Build query based on system filter
                if system_id:
                    where_clause = "WHERE d.timestamp > datetime('now', '-{} hours') AND s.system_id = ?".format(hours_back)
                    params = (system_id,)
                else:
                    where_clause = "WHERE d.timestamp > datetime('now', '-{} hours')".format(hours_back)
                    params = ()
                
                rows = conn.execute(f"""
                    SELECT d.*, s.system_id, s.config_type, sys.system_name, sys.system_type
                    FROM config_diffs d
                    JOIN config_snapshots s ON d.snapshot_id_after = s.id
                    JOIN config_systems sys ON s.system_id = sys.system_id
                    {where_clause}
                    ORDER BY d.risk_score DESC, d.timestamp DESC
                """, params).fetchall()
                
                drift_issues = []
                for row in rows:
                    drift_issues.append({
                        **dict(row),
                        'drift_detected': True,
                        'analysis': self._analyze_drift(dict(row))
                    })
                
                logger.info(f"🔍 Detected {len(drift_issues)} configuration changes")
                return drift_issues
                
        except Exception as e:
            logger.error(f"❌ Failed to detect drift: {e}")
            return []
    
    def _analyze_drift(self, diff_data: Dict) -> Dict:
        """Advanced drift analysis with pattern recognition"""
        analysis = {
            'severity': 'low',
            'recommendations': [],
            'risk_factors': [],
            'patterns_detected': [],
            'confidence': 0.0
        }
        
        risk_score = diff_data.get('risk_score', 0.0)
        change_type = diff_data.get('change_type', '')
        lines_changed = (diff_data.get('lines_added', 0) + 
                        diff_data.get('lines_removed', 0))
        diff_content = diff_data.get('diff_content', '')
        system_type = diff_data.get('system_type', '')
        
        # Enhanced severity calculation
        if risk_score > 0.8:
            analysis['severity'] = 'critical'
        elif risk_score > 0.6:
            analysis['severity'] = 'high'
        elif risk_score > 0.3:
            analysis['severity'] = 'medium'
            
        # Pattern detection in diff content
        patterns = self._detect_change_patterns(diff_content, system_type)
        analysis['patterns_detected'] = patterns
        
        # Calculate confidence based on pattern recognition
        analysis['confidence'] = min(0.95, len(patterns) * 0.2 + risk_score * 0.6)
        
        # Enhanced risk factors
        if lines_changed > 100:
            analysis['risk_factors'].append('Very large configuration change')
        elif lines_changed > 50:
            analysis['risk_factors'].append('Large configuration change')
        elif lines_changed > 20:
            analysis['risk_factors'].append('Moderate configuration change')
            
        if change_type == 'deleted':
            analysis['risk_factors'].append('Configuration removal detected')
            analysis['severity'] = 'high'  # Escalate deletions
            
        # Pattern-based risk factors
        for pattern in patterns:
            if pattern['type'] == 'security_change':
                analysis['risk_factors'].append(f"Security configuration change: {pattern['detail']}")
                analysis['severity'] = 'critical'
            elif pattern['type'] == 'service_disable':
                analysis['risk_factors'].append(f"Service disabled: {pattern['detail']}")
            elif pattern['type'] == 'port_change':
                analysis['risk_factors'].append(f"Network port change: {pattern['detail']}")
            elif pattern['type'] == 'auth_change':
                analysis['risk_factors'].append(f"Authentication change: {pattern['detail']}")
        
        # Enhanced recommendations
        if analysis['severity'] == 'critical':
            analysis['recommendations'].extend([
                'IMMEDIATE ACTION REQUIRED',
                'Stop all automated deployments',
                'Verify system security and functionality',
                'Consider emergency rollback'
            ])
        elif analysis['severity'] == 'high':
            analysis['recommendations'].extend([
                'Review change immediately',
                'Test system functionality thoroughly',
                'Verify security implications',
                'Monitor system behavior closely'
            ])
        elif analysis['severity'] == 'medium':
            analysis['recommendations'].extend([
                'Review change within 4 hours',
                'Verify functionality',
                'Document change rationale'
            ])
        
        # Pattern-specific recommendations
        if any(p['type'] == 'security_change' for p in patterns):
            analysis['recommendations'].append('Security team review required')
        if any(p['type'] == 'service_disable' for p in patterns):
            analysis['recommendations'].append('Verify dependent services')
        if any(p['type'] == 'port_change' for p in patterns):
            analysis['recommendations'].append('Update firewall and monitoring rules')
            
        return analysis
    
    def _detect_change_patterns(self, diff_content: str, system_type: str) -> List[Dict]:
        """Detect common configuration change patterns"""
        patterns = []
        
        if not diff_content:
            return patterns
            
        lines = diff_content.split('\n')
        
        # Security-related patterns
        security_keywords = [
            'password', 'auth', 'ssl', 'tls', 'cert', 'key', 'token', 
            'secret', 'credential', 'permission', 'access', 'security'
        ]
        
        # Service-related patterns  
        service_keywords = [
            'enable', 'disable', 'start', 'stop', 'restart', 'service',
            'daemon', 'process'
        ]
        
        # Network-related patterns
        network_keywords = [
            'port', 'bind', 'listen', 'host', 'ip', 'address', 'network',
            'firewall', 'iptables'
        ]
        
        for line in lines:
            line_lower = line.lower()
            
            # Skip diff headers
            if line.startswith('@@') or line.startswith('+++') or line.startswith('---'):
                continue
                
            # Check for added or removed lines
            if line.startswith('+') or line.startswith('-'):
                change_type = 'added' if line.startswith('+') else 'removed'
                content = line[1:].strip()
                
                # Security changes
                for keyword in security_keywords:
                    if keyword in line_lower:
                        patterns.append({
                            'type': 'security_change',
                            'detail': f"{keyword} configuration {change_type}",
                            'line': content,
                            'severity': 'high'
                        })
                        break
                
                # Service changes
                for keyword in service_keywords:
                    if keyword in line_lower:
                        if 'disable' in line_lower or 'stop' in line_lower:
                            patterns.append({
                                'type': 'service_disable',
                                'detail': f"Service disabled/stopped: {content}",
                                'line': content,
                                'severity': 'medium'
                            })
                        else:
                            patterns.append({
                                'type': 'service_change',
                                'detail': f"Service configuration {change_type}",
                                'line': content,
                                'severity': 'low'
                            })
                        break
                
                # Network changes
                for keyword in network_keywords:
                    if keyword in line_lower:
                        if 'port' in line_lower:
                            patterns.append({
                                'type': 'port_change',
                                'detail': f"Port configuration {change_type}",
                                'line': content,
                                'severity': 'medium'
                            })
                        else:
                            patterns.append({
                                'type': 'network_change',
                                'detail': f"Network configuration {change_type}",
                                'line': content,
                                'severity': 'medium'
                            })
                        break
                
                # System-specific patterns
                if system_type == 'nginx':
                    if any(word in line_lower for word in ['server_name', 'proxy_pass', 'upstream']):
                        patterns.append({
                            'type': 'nginx_routing',
                            'detail': f"Nginx routing {change_type}",
                            'line': content,
                            'severity': 'medium'
                        })
                elif system_type == 'mysql':
                    if any(word in line_lower for word in ['user', 'grant', 'privilege']):
                        patterns.append({
                            'type': 'database_permission',
                            'detail': f"Database permission {change_type}",
                            'line': content,
                            'severity': 'high'
                        })
                elif system_type == 'kubernetes':
                    if any(word in line_lower for word in ['replicas', 'image', 'resource']):
                        patterns.append({
                            'type': 'k8s_resource',
                            'detail': f"Kubernetes resource {change_type}",
                            'line': content,
                            'severity': 'medium'
                        })
        
        return patterns
    
    def create_drift_alert_with_analysis(self, system_id: str, drift_data: Dict) -> bool:
        """Create advanced drift alert with full analysis"""
        try:
            analysis = self._analyze_drift(drift_data)
            
            # Create alert description with analysis
            description_parts = [
                f"Configuration drift detected with {analysis['severity']} severity",
                f"Risk score: {drift_data.get('risk_score', 0.0):.2f}",
                f"Change type: {drift_data.get('change_type', 'unknown')}"
            ]
            
            if analysis['patterns_detected']:
                patterns_str = ', '.join([p['detail'] for p in analysis['patterns_detected'][:3]])
                description_parts.append(f"Patterns: {patterns_str}")
            
            if analysis['risk_factors']:
                factors_str = ', '.join(analysis['risk_factors'][:2])
                description_parts.append(f"Risk factors: {factors_str}")
            
            description = '. '.join(description_parts)
            
            # Determine drift type
            drift_type = 'configuration_change'
            if any(p['type'] == 'security_change' for p in analysis['patterns_detected']):
                drift_type = 'security_drift'
            elif any(p['type'] == 'service_disable' for p in analysis['patterns_detected']):
                drift_type = 'service_drift'
                
            return self.create_drift_alert(
                system_id=system_id,
                drift_type=drift_type,
                severity=analysis['severity'],
                description=description,
                snapshot_id=drift_data.get('snapshot_id_after')
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to create analyzed drift alert: {e}")
            return False
    
    def get_drift_trends(self, system_id: str = None, days_back: int = 7) -> Dict:
        """Analyze drift trends over time"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Build query based on system filter
                if system_id:
                    where_clause = "WHERE d.timestamp > datetime('now', '-{} days') AND s.system_id = ?".format(days_back)
                    params = (system_id,)
                else:
                    where_clause = "WHERE d.timestamp > datetime('now', '-{} days')".format(days_back)
                    params = ()
                
                rows = conn.execute(f"""
                    SELECT d.*, s.system_id, s.config_type, sys.system_name, sys.system_type,
                           DATE(d.timestamp) as drift_date
                    FROM config_diffs d
                    JOIN config_snapshots s ON d.snapshot_id_after = s.id
                    JOIN config_systems sys ON s.system_id = sys.system_id
                    {where_clause}
                    ORDER BY d.timestamp
                """, params).fetchall()
                
                # Analyze trends
                daily_drift = {}
                severity_trends = {}
                system_trends = {}
                
                for row in rows:
                    date = row['drift_date']
                    system = row['system_id']
                    analysis = self._analyze_drift(dict(row))
                    severity = analysis['severity']
                    
                    # Daily drift counts
                    if date not in daily_drift:
                        daily_drift[date] = 0
                    daily_drift[date] += 1
                    
                    # Severity trends
                    if severity not in severity_trends:
                        severity_trends[severity] = 0
                    severity_trends[severity] += 1
                    
                    # System trends
                    if system not in system_trends:
                        system_trends[system] = {'count': 0, 'risk_score': 0.0}
                    system_trends[system]['count'] += 1
                    system_trends[system]['risk_score'] += row.get('risk_score', 0.0)
                
                # Calculate average risk scores
                for system in system_trends:
                    count = system_trends[system]['count']
                    if count > 0:
                        system_trends[system]['avg_risk'] = system_trends[system]['risk_score'] / count
                
                return {
                    'period_days': days_back,
                    'total_changes': len(rows),
                    'daily_drift': daily_drift,
                    'severity_distribution': severity_trends,
                    'system_breakdown': system_trends,
                    'most_active_systems': sorted(
                        [(s, data['count']) for s, data in system_trends.items()],
                        key=lambda x: x[1], reverse=True
                    )[:5],
                    'highest_risk_systems': sorted(
                        [(s, data.get('avg_risk', 0.0)) for s, data in system_trends.items()],
                        key=lambda x: x[1], reverse=True
                    )[:5]
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to analyze drift trends: {e}")
            return {'error': str(e)}
    
    def get_systems(self) -> List[Dict]:
        """Get all registered systems"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                rows = conn.execute("""
                    SELECT s.*, 
                           COUNT(cs.id) as snapshot_count,
                           MAX(cs.timestamp) as last_snapshot
                    FROM config_systems s
                    LEFT JOIN config_snapshots cs ON s.system_id = cs.system_id
                    GROUP BY s.system_id
                    ORDER BY s.system_name
                """).fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Failed to get systems: {e}")
            return []
    
    def create_drift_alert(self, system_id: str, drift_type: str, severity: str,
                          description: str, snapshot_id: str = None) -> bool:
        """Create a drift alert"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO config_drift_alerts 
                    (system_id, drift_type, severity, description, snapshot_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (system_id, drift_type, severity, description, snapshot_id))
                
            logger.warning(f"🚨 Drift alert: {severity} - {description}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create alert: {e}")
            return False
    
    def get_active_alerts(self, system_id: str = None) -> List[Dict]:
        """Get active drift alerts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                if system_id:
                    rows = conn.execute("""
                        SELECT a.*, s.system_name 
                        FROM config_drift_alerts a
                        JOIN config_systems s ON a.system_id = s.system_id
                        WHERE a.resolved = FALSE AND a.system_id = ?
                        ORDER BY a.timestamp DESC
                    """, (system_id,)).fetchall()
                else:
                    rows = conn.execute("""
                        SELECT a.*, s.system_name 
                        FROM config_drift_alerts a
                        JOIN config_systems s ON a.system_id = s.system_id
                        WHERE a.resolved = FALSE
                        ORDER BY a.severity, a.timestamp DESC
                    """).fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Failed to get alerts: {e}")
            return []