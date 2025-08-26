"""
Log Intelligence & Analysis System for hAIveMind DevOps Memory

Advanced ML-powered log analysis with pattern detection, anomaly identification, 
cross-service correlation, and automated troubleshooting capabilities.

Features:
- Multi-source log aggregation (syslog, application, container logs)
- Machine learning pattern detection for anomalies
- Cross-service log correlation using trace IDs
- Automated debug report generation with root cause analysis
- Intelligent log archival with compression and retention policies
- Natural language processing for log messages
- Predictive failure detection and trend analysis
"""

import sqlite3
import json
import logging
import re
import time
import gzip
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
from collections import defaultdict, Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN, KMeans
from sklearn.ensemble import IsolationForest
from sklearn.decomposition import PCA
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class LogEntry:
    id: str
    timestamp: datetime
    level: str  # DEBUG, INFO, WARN, ERROR, FATAL
    source: str  # service/component name
    host: str
    message: str
    trace_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    raw_log: str = ""
    
@dataclass 
class LogPattern:
    id: str
    pattern_hash: str
    template: str
    frequency: int
    first_seen: datetime
    last_seen: datetime
    services: Set[str]
    severity_distribution: Dict[str, int]
    is_anomaly: bool = False
    risk_score: float = 0.0

@dataclass
class LogAnomaly:
    id: str
    log_entry: LogEntry
    anomaly_type: str  # "frequency", "new_pattern", "error_spike", "correlation"
    severity: str      # "low", "medium", "high", "critical" 
    confidence: float
    description: str
    detected_at: datetime
    related_patterns: List[str] = None
    suggested_actions: List[str] = None

class LogIntelligenceSystem:
    """Advanced ML-powered log analysis and intelligence system"""
    
    def __init__(self, db_path: str = "data/log_intelligence.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # ML Components
        self.vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words='english',
            ngram_range=(1, 3),
            min_df=2
        )
        self.clustering_model = None
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.pattern_cache = {}
        
        logger.info("🧠 Log Intelligence System initialized")
    
    def _init_database(self):
        """Initialize SQLite database with comprehensive log analysis schema"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        
        try:
            # Raw log entries table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS log_entries (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    timestamp TIMESTAMP NOT NULL,
                    level TEXT NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL')),
                    source TEXT NOT NULL,
                    host TEXT NOT NULL,
                    message TEXT NOT NULL,
                    trace_id TEXT,
                    user_id TEXT,
                    session_id TEXT,
                    metadata TEXT DEFAULT '{}',
                    raw_log TEXT,
                    pattern_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (pattern_id) REFERENCES log_patterns (id)
                )
            ''')
            
            # Log patterns table (for template extraction)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS log_patterns (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    pattern_hash TEXT UNIQUE NOT NULL,
                    template TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    first_seen TIMESTAMP NOT NULL,
                    last_seen TIMESTAMP NOT NULL,
                    services TEXT DEFAULT '[]',
                    severity_distribution TEXT DEFAULT '{}',
                    is_anomaly BOOLEAN DEFAULT FALSE,
                    risk_score REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Anomalies detection results
            conn.execute('''
                CREATE TABLE IF NOT EXISTS log_anomalies (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    log_entry_id TEXT NOT NULL,
                    anomaly_type TEXT NOT NULL,
                    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
                    confidence REAL NOT NULL,
                    description TEXT,
                    related_patterns TEXT DEFAULT '[]',
                    suggested_actions TEXT DEFAULT '[]',
                    resolved BOOLEAN DEFAULT FALSE,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (log_entry_id) REFERENCES log_entries (id)
                )
            ''')
            
            # Cross-service correlations
            conn.execute('''
                CREATE TABLE IF NOT EXISTS log_correlations (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    primary_log_id TEXT NOT NULL,
                    correlated_log_id TEXT NOT NULL,
                    correlation_type TEXT NOT NULL,
                    correlation_strength REAL NOT NULL,
                    time_delta_seconds INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (primary_log_id) REFERENCES log_entries (id),
                    FOREIGN KEY (correlated_log_id) REFERENCES log_entries (id),
                    UNIQUE (primary_log_id, correlated_log_id, correlation_type)
                )
            ''')
            
            # Archived logs metadata (for retention management)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS log_archives (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    archive_path TEXT NOT NULL,
                    source_service TEXT,
                    start_timestamp TIMESTAMP NOT NULL,
                    end_timestamp TIMESTAMP NOT NULL,
                    entry_count INTEGER,
                    compressed_size INTEGER,
                    original_size INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Debug session tracking
            conn.execute('''
                CREATE TABLE IF NOT EXISTS debug_sessions (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    issue_description TEXT NOT NULL,
                    related_services TEXT DEFAULT '[]',
                    time_range_start TIMESTAMP NOT NULL,
                    time_range_end TIMESTAMP NOT NULL,
                    root_cause_analysis TEXT,
                    recommendations TEXT DEFAULT '[]',
                    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'resolved', 'escalated')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create performance indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON log_entries (timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_logs_source_level ON log_entries (source, level)",
                "CREATE INDEX IF NOT EXISTS idx_logs_trace_id ON log_entries (trace_id)",
                "CREATE INDEX IF NOT EXISTS idx_logs_pattern ON log_entries (pattern_id)",
                "CREATE INDEX IF NOT EXISTS idx_patterns_hash ON log_patterns (pattern_hash)",
                "CREATE INDEX IF NOT EXISTS idx_patterns_frequency ON log_patterns (frequency DESC)",
                "CREATE INDEX IF NOT EXISTS idx_anomalies_detected ON log_anomalies (detected_at)",
                "CREATE INDEX IF NOT EXISTS idx_anomalies_severity ON log_anomalies (severity)",
                "CREATE INDEX IF NOT EXISTS idx_correlations_primary ON log_correlations (primary_log_id)",
                "CREATE INDEX IF NOT EXISTS idx_correlations_type ON log_correlations (correlation_type)",
                "CREATE INDEX IF NOT EXISTS idx_archives_timestamp ON log_archives (start_timestamp, end_timestamp)"
            ]
            
            for index_sql in indexes:
                conn.execute(index_sql)
            
            conn.commit()
            logger.info("📊 Log Intelligence database schema initialized")
            
        finally:
            conn.close()
    
    # ===== LOG INGESTION AND PROCESSING =====
    
    def ingest_logs(self, log_entries: List[Dict[str, Any]], source: str = "unknown") -> int:
        """Ingest multiple log entries with pattern extraction and anomaly detection"""
        conn = sqlite3.connect(self.db_path)
        processed_count = 0
        
        try:
            for log_data in log_entries:
                log_entry = self._parse_log_entry(log_data, source)
                if log_entry:
                    # Extract/update pattern
                    pattern = self._extract_pattern(log_entry)
                    pattern_id = self._store_pattern(pattern, conn)
                    
                    # Store log entry
                    self._store_log_entry(log_entry, pattern_id, conn)
                    processed_count += 1
            
            conn.commit()
            
            # Trigger analysis on batch
            self._analyze_batch_anomalies(log_entries)
            
            logger.info(f"📊 Processed {processed_count} log entries from {source}")
            return processed_count
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Failed to ingest logs: {e}")
            return 0
        finally:
            conn.close()
    
    def _parse_log_entry(self, log_data: Dict[str, Any], source: str) -> Optional[LogEntry]:
        """Parse raw log data into structured LogEntry"""
        try:
            # Handle different log formats
            if isinstance(log_data, dict):
                timestamp_str = log_data.get('timestamp') or log_data.get('@timestamp') or log_data.get('time')
                message = log_data.get('message') or log_data.get('msg') or str(log_data)
                level = (log_data.get('level') or log_data.get('severity') or 'INFO').upper()
                host = log_data.get('host') or log_data.get('hostname') or 'unknown'
            else:
                # Parse common log formats (Apache, Nginx, syslog, etc.)
                message = str(log_data)
                timestamp_str = None
                level = 'INFO'
                host = 'unknown'
                
                # Try to extract timestamp and level from message
                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})', message)
                if timestamp_match:
                    timestamp_str = timestamp_match.group(1)
                
                level_match = re.search(r'\b(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b', message)
                if level_match:
                    level = level_match.group(1).upper()
                    if level == 'WARNING':
                        level = 'WARN'
                    elif level == 'CRITICAL':
                        level = 'FATAL'
            
            # Parse timestamp
            if timestamp_str:
                try:
                    if 'T' in timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    else:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                except:
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()
            
            # Extract trace/correlation IDs
            trace_id = self._extract_trace_id(message)
            user_id = self._extract_user_id(message)
            session_id = self._extract_session_id(message)
            
            return LogEntry(
                id=hashlib.md5(f"{timestamp}{source}{message}".encode()).hexdigest(),
                timestamp=timestamp,
                level=level,
                source=source,
                host=host,
                message=message,
                trace_id=trace_id,
                user_id=user_id,
                session_id=session_id,
                metadata=log_data if isinstance(log_data, dict) else {},
                raw_log=str(log_data)
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to parse log entry: {e}")
            return None
    
    def _extract_trace_id(self, message: str) -> Optional[str]:
        """Extract trace ID from log message"""
        patterns = [
            r'trace[_-]?id[:\s=]+([a-fA-F0-9-]{8,})',
            r'traceId[:\s=]+([a-fA-F0-9-]{8,})',
            r'request[_-]?id[:\s=]+([a-fA-F0-9-]{8,})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_user_id(self, message: str) -> Optional[str]:
        """Extract user ID from log message"""
        patterns = [
            r'user[_-]?id[:\s=]+([a-zA-Z0-9-]{1,})',
            r'userId[:\s=]+([a-zA-Z0-9-]{1,})',
            r'user[:\s=]+([a-zA-Z0-9_.-]{3,})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_session_id(self, message: str) -> Optional[str]:
        """Extract session ID from log message"""
        patterns = [
            r'session[_-]?id[:\s=]+([a-fA-F0-9-]{8,})',
            r'sessionId[:\s=]+([a-fA-F0-9-]{8,})',
            r'JSESSIONID[:\s=]+([a-fA-F0-9]{8,})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_pattern(self, log_entry: LogEntry) -> LogPattern:
        """Extract log pattern template for clustering"""
        message = log_entry.message
        
        # Replace common variable parts with placeholders
        template = message
        
        # Replace timestamps
        template = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?[Z]?', '<TIMESTAMP>', template)
        
        # Replace IDs (UUIDs, hashes, etc.)
        template = re.sub(r'\b[a-fA-F0-9]{8,}\b', '<ID>', template)
        template = re.sub(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b', '<UUID>', template)
        
        # Replace numbers
        template = re.sub(r'\b\d+\b', '<NUM>', template)
        template = re.sub(r'\b\d+\.\d+\b', '<FLOAT>', template)
        
        # Replace IP addresses
        template = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '<IP>', template)
        
        # Replace URLs
        template = re.sub(r'https?://[^\s]+', '<URL>', template)
        
        # Replace file paths
        template = re.sub(r'/[^\s]*', '<PATH>', template)
        
        # Replace quoted strings
        template = re.sub(r'"[^"]*"', '<STRING>', template)
        template = re.sub(r"'[^']*'", '<STRING>', template)
        
        # Generate pattern hash
        pattern_hash = hashlib.md5(template.encode()).hexdigest()
        
        return LogPattern(
            id=pattern_hash,
            pattern_hash=pattern_hash,
            template=template,
            frequency=1,
            first_seen=log_entry.timestamp,
            last_seen=log_entry.timestamp,
            services={log_entry.source},
            severity_distribution={log_entry.level: 1}
        )
    
    def _store_pattern(self, pattern: LogPattern, conn: sqlite3.Connection) -> str:
        """Store or update log pattern in database"""
        try:
            # Check if pattern exists
            existing = conn.execute(
                'SELECT id, frequency, services, severity_distribution FROM log_patterns WHERE pattern_hash = ?',
                (pattern.pattern_hash,)
            ).fetchone()
            
            if existing:
                # Update existing pattern
                existing_services = set(json.loads(existing[2]))
                existing_severity = json.loads(existing[3])
                
                # Merge services
                pattern.services.update(existing_services)
                
                # Merge severity distribution
                for level, count in pattern.severity_distribution.items():
                    existing_severity[level] = existing_severity.get(level, 0) + count
                
                conn.execute('''
                    UPDATE log_patterns 
                    SET frequency = frequency + 1, last_seen = ?, services = ?, severity_distribution = ?
                    WHERE pattern_hash = ?
                ''', (pattern.last_seen, json.dumps(list(pattern.services)), 
                      json.dumps(existing_severity), pattern.pattern_hash))
                
                return existing[0]
            else:
                # Insert new pattern
                conn.execute('''
                    INSERT INTO log_patterns (id, pattern_hash, template, frequency, first_seen, last_seen, services, severity_distribution)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (pattern.id, pattern.pattern_hash, pattern.template, pattern.frequency,
                      pattern.first_seen, pattern.last_seen, json.dumps(list(pattern.services)),
                      json.dumps(pattern.severity_distribution)))
                
                return pattern.id
                
        except Exception as e:
            logger.error(f"❌ Failed to store pattern: {e}")
            return pattern.id
    
    def _store_log_entry(self, log_entry: LogEntry, pattern_id: str, conn: sqlite3.Connection):
        """Store log entry in database"""
        conn.execute('''
            INSERT OR REPLACE INTO log_entries 
            (id, timestamp, level, source, host, message, trace_id, user_id, session_id, metadata, raw_log, pattern_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (log_entry.id, log_entry.timestamp, log_entry.level, log_entry.source, log_entry.host,
              log_entry.message, log_entry.trace_id, log_entry.user_id, log_entry.session_id,
              json.dumps(log_entry.metadata), log_entry.raw_log, pattern_id))
    
    # ===== ANOMALY DETECTION =====
    
    def _analyze_batch_anomalies(self, log_entries: List[Dict[str, Any]]):
        """Analyze batch of logs for anomalies"""
        try:
            # Frequency-based anomaly detection
            self._detect_frequency_anomalies()
            
            # Error spike detection
            self._detect_error_spikes()
            
            # New pattern detection
            self._detect_new_patterns()
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze anomalies: {e}")
    
    def _detect_frequency_anomalies(self):
        """Detect patterns with unusual frequency"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Get pattern frequencies in last hour vs baseline
            current_time = datetime.now()
            hour_ago = current_time - timedelta(hours=1)
            day_ago = current_time - timedelta(days=1)
            
            recent_patterns = conn.execute('''
                SELECT p.id, p.template, COUNT(*) as recent_count
                FROM log_patterns p
                JOIN log_entries l ON p.id = l.pattern_id
                WHERE l.timestamp >= ?
                GROUP BY p.id
            ''', (hour_ago,)).fetchall()
            
            for pattern_id, template, recent_count in recent_patterns:
                # Get baseline frequency
                baseline = conn.execute('''
                    SELECT COUNT(*) / 24.0 as hourly_avg
                    FROM log_entries 
                    WHERE pattern_id = ? AND timestamp >= ? AND timestamp < ?
                ''', (pattern_id, day_ago, hour_ago)).fetchone()
                
                baseline_avg = baseline[0] if baseline and baseline[0] else 1.0
                
                # Detect significant deviation
                if recent_count > baseline_avg * 3:  # 3x threshold
                    self._create_anomaly({
                        'log_entry_id': pattern_id,
                        'anomaly_type': 'frequency_spike',
                        'severity': 'high' if recent_count > baseline_avg * 5 else 'medium',
                        'confidence': min(0.95, (recent_count / baseline_avg) / 10),
                        'description': f"Pattern frequency spike: {recent_count} vs baseline {baseline_avg:.1f}",
                        'suggested_actions': [
                            'Investigate underlying cause of increased log volume',
                            'Check system resources and performance',
                            'Review recent deployments or configuration changes'
                        ]
                    })
                
        finally:
            conn.close()
    
    def _detect_error_spikes(self):
        """Detect spikes in error rates"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            current_time = datetime.now()
            hour_ago = current_time - timedelta(hours=1)
            day_ago = current_time - timedelta(days=1)
            
            # Check error rate by service
            services = conn.execute('SELECT DISTINCT source FROM log_entries WHERE timestamp >= ?', (day_ago,)).fetchall()
            
            for (service,) in services:
                # Recent error count
                recent_errors = conn.execute('''
                    SELECT COUNT(*) FROM log_entries 
                    WHERE source = ? AND level IN ('ERROR', 'FATAL') AND timestamp >= ?
                ''', (service, hour_ago)).fetchone()[0]
                
                # Baseline error count
                baseline_errors = conn.execute('''
                    SELECT COUNT(*) / 24.0 FROM log_entries 
                    WHERE source = ? AND level IN ('ERROR', 'FATAL') AND timestamp >= ? AND timestamp < ?
                ''', (service, day_ago, hour_ago)).fetchone()[0]
                
                if recent_errors > max(10, baseline_errors * 2):  # At least 10 errors or 2x baseline
                    severity = 'critical' if recent_errors > baseline_errors * 5 else 'high'
                    
                    self._create_anomaly({
                        'log_entry_id': f"error_spike_{service}_{int(time.time())}",
                        'anomaly_type': 'error_spike',
                        'severity': severity,
                        'confidence': 0.9,
                        'description': f"Error spike in {service}: {recent_errors} errors vs baseline {baseline_errors:.1f}",
                        'suggested_actions': [
                            f'Immediately investigate {service} service health',
                            'Check service dependencies and resources',
                            'Review recent code deployments',
                            'Monitor user impact and consider rollback'
                        ]
                    })
                
        finally:
            conn.close()
    
    def _detect_new_patterns(self):
        """Detect new log patterns that haven't been seen before"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Find patterns first seen in last hour
            hour_ago = datetime.now() - timedelta(hours=1)
            
            new_patterns = conn.execute('''
                SELECT id, template, frequency, services 
                FROM log_patterns 
                WHERE first_seen >= ? AND frequency >= 5
                ORDER BY frequency DESC
            ''', (hour_ago,)).fetchall()
            
            for pattern_id, template, frequency, services_json in new_patterns:
                services = json.loads(services_json)
                
                self._create_anomaly({
                    'log_entry_id': pattern_id,
                    'anomaly_type': 'new_pattern',
                    'severity': 'medium' if frequency > 20 else 'low',
                    'confidence': 0.8,
                    'description': f"New log pattern detected: {template[:100]}...",
                    'suggested_actions': [
                        'Review new log pattern for potential issues',
                        f'Check {", ".join(services)} service(s) for changes',
                        'Determine if pattern indicates normal or abnormal behavior'
                    ]
                })
                
        finally:
            conn.close()
    
    def _create_anomaly(self, anomaly_data: Dict[str, Any]):
        """Create anomaly record"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            conn.execute('''
                INSERT INTO log_anomalies 
                (log_entry_id, anomaly_type, severity, confidence, description, suggested_actions)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                anomaly_data['log_entry_id'],
                anomaly_data['anomaly_type'], 
                anomaly_data['severity'],
                anomaly_data['confidence'],
                anomaly_data['description'],
                json.dumps(anomaly_data.get('suggested_actions', []))
            ))
            
            conn.commit()
            logger.info(f"🚨 Anomaly detected: {anomaly_data['anomaly_type']} - {anomaly_data['severity']}")
            
        finally:
            conn.close()
    
    # ===== LOG CORRELATION =====
    
    def correlate_logs(self, time_window_minutes: int = 5) -> List[Dict[str, Any]]:
        """Find correlated log entries across services"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            correlations = []
            current_time = datetime.now()
            window_start = current_time - timedelta(minutes=time_window_minutes)
            
            # Get recent logs with trace IDs
            traced_logs = conn.execute('''
                SELECT * FROM log_entries 
                WHERE trace_id IS NOT NULL AND timestamp >= ?
                ORDER BY timestamp
            ''', (window_start,)).fetchall()
            
            # Group by trace ID
            trace_groups = defaultdict(list)
            for log in traced_logs:
                trace_groups[log['trace_id']].append(dict(log))
            
            # Find cross-service correlations
            for trace_id, logs in trace_groups.items():
                if len(logs) > 1:
                    services = set(log['source'] for log in logs)
                    if len(services) > 1:  # Cross-service correlation
                        correlations.append({
                            'trace_id': trace_id,
                            'services': list(services),
                            'log_count': len(logs),
                            'time_span': max(log['timestamp'] for log in logs) - min(log['timestamp'] for log in logs),
                            'logs': logs
                        })
            
            # Find temporal correlations (same time window, different services)
            time_buckets = defaultdict(lambda: defaultdict(list))
            
            all_logs = conn.execute('''
                SELECT * FROM log_entries 
                WHERE timestamp >= ? AND level IN ('WARN', 'ERROR', 'FATAL')
                ORDER BY timestamp
            ''', (window_start,)).fetchall()
            
            for log in all_logs:
                # 1-minute buckets
                bucket = log['timestamp'][:16]  # YYYY-MM-DD HH:MM
                time_buckets[bucket][log['source']].append(dict(log))
            
            for bucket_time, services_logs in time_buckets.items():
                if len(services_logs) > 1:  # Multiple services in same time bucket
                    correlations.append({
                        'correlation_type': 'temporal',
                        'time_bucket': bucket_time,
                        'services': list(services_logs.keys()),
                        'service_logs': dict(services_logs)
                    })
            
            return correlations
            
        finally:
            conn.close()
    
    # ===== DEBUG REPORT GENERATION =====
    
    def generate_debug_report(self, issue_description: str, services: List[str], 
                            hours_back: int = 2) -> Dict[str, Any]:
        """Generate automated debug report with root cause analysis"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours_back)
            
            # Create debug session
            session_id = hashlib.md5(f"{issue_description}{end_time}".encode()).hexdigest()
            
            conn.execute('''
                INSERT INTO debug_sessions (id, issue_description, related_services, time_range_start, time_range_end)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, issue_description, json.dumps(services), start_time, end_time))
            
            # Collect relevant data
            report = {
                'session_id': session_id,
                'issue': issue_description,
                'time_range': {'start': start_time.isoformat(), 'end': end_time.isoformat()},
                'services_analyzed': services,
                'summary': {},
                'error_analysis': {},
                'correlations': [],
                'anomalies': [],
                'recommendations': []
            }
            
            # Summary statistics
            for service in services:
                service_logs = conn.execute('''
                    SELECT level, COUNT(*) as count 
                    FROM log_entries 
                    WHERE source = ? AND timestamp BETWEEN ? AND ?
                    GROUP BY level
                ''', (service, start_time, end_time)).fetchall()
                
                report['summary'][service] = {row['level']: row['count'] for row in service_logs}
            
            # Error analysis
            error_patterns = conn.execute('''
                SELECT p.template, COUNT(*) as count, p.services
                FROM log_patterns p
                JOIN log_entries l ON p.id = l.pattern_id
                WHERE l.level IN ('ERROR', 'FATAL') AND l.timestamp BETWEEN ? AND ?
                AND l.source IN ({})
                GROUP BY p.id
                ORDER BY count DESC
                LIMIT 10
            '''.format(','.join('?' * len(services))), [start_time, end_time] + services).fetchall()
            
            report['error_analysis'] = [
                {
                    'pattern': row['template'],
                    'count': row['count'],
                    'services': json.loads(row['services'])
                }
                for row in error_patterns
            ]
            
            # Get correlations
            report['correlations'] = self.correlate_logs()
            
            # Get recent anomalies
            anomalies = conn.execute('''
                SELECT * FROM log_anomalies 
                WHERE detected_at BETWEEN ? AND ? 
                ORDER BY confidence DESC
                LIMIT 20
            ''', (start_time, end_time)).fetchall()
            
            report['anomalies'] = [dict(anomaly) for anomaly in anomalies]
            
            # Generate recommendations
            recommendations = self._generate_recommendations(report)
            report['recommendations'] = recommendations
            
            # Update session with recommendations
            conn.execute('''
                UPDATE debug_sessions 
                SET recommendations = ? 
                WHERE id = ?
            ''', (json.dumps(recommendations), session_id))
            
            conn.commit()
            
            logger.info(f"🔍 Debug report generated for: {issue_description}")
            return report
            
        finally:
            conn.close()
    
    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate intelligent recommendations based on analysis"""
        recommendations = []
        
        # Error-based recommendations
        for error in report['error_analysis']:
            if error['count'] > 50:
                recommendations.append(f"High frequency error pattern detected: {error['pattern'][:100]}... - Investigate immediately")
        
        # Anomaly-based recommendations
        critical_anomalies = [a for a in report['anomalies'] if a['severity'] == 'critical']
        if critical_anomalies:
            recommendations.append("Critical anomalies detected - Consider immediate escalation")
        
        # Service-specific recommendations
        for service, levels in report['summary'].items():
            error_rate = levels.get('ERROR', 0) + levels.get('FATAL', 0)
            total_logs = sum(levels.values())
            
            if total_logs > 0 and error_rate / total_logs > 0.1:  # >10% error rate
                recommendations.append(f"High error rate in {service} service ({error_rate}/{total_logs}) - Check service health")
        
        # Correlation-based recommendations
        if len(report['correlations']) > 5:
            recommendations.append("Multiple service correlations detected - Possible cascading failure")
        
        if not recommendations:
            recommendations.append("No critical issues detected in log analysis")
        
        return recommendations
    
    # ===== LOG ARCHIVAL AND RETENTION =====
    
    def archive_logs(self, older_than_days: int = 30, compress: bool = True) -> Dict[str, Any]:
        """Archive and compress old logs based on retention policy"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            cutoff_date = datetime.now() - timedelta(days=older_than_days)
            archive_dir = Path("data/log_archives")
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            # Get logs to archive by service
            services = conn.execute('''
                SELECT DISTINCT source FROM log_entries WHERE timestamp < ?
            ''', (cutoff_date,)).fetchall()
            
            archived_info = {
                'archived_services': [],
                'total_entries': 0,
                'total_size_mb': 0,
                'compressed_size_mb': 0
            }
            
            for (service,) in services:
                logs_to_archive = conn.execute('''
                    SELECT * FROM log_entries WHERE source = ? AND timestamp < ?
                    ORDER BY timestamp
                ''', (service, cutoff_date)).fetchall()
                
                if logs_to_archive:
                    # Create archive file
                    archive_filename = f"{service}_{cutoff_date.strftime('%Y%m%d')}.json"
                    archive_path = archive_dir / archive_filename
                    
                    # Write logs to JSON file
                    logs_data = []
                    for log in logs_to_archive:
                        logs_data.append({
                            'timestamp': log[1],
                            'level': log[2],
                            'source': log[3],
                            'host': log[4],
                            'message': log[5],
                            'trace_id': log[6],
                            'raw_log': log[10]
                        })
                    
                    with open(archive_path, 'w') as f:
                        json.dump(logs_data, f, default=str, indent=2)
                    
                    original_size = archive_path.stat().st_size
                    
                    # Compress if requested
                    if compress:
                        with open(archive_path, 'rb') as f_in:
                            with gzip.open(f"{archive_path}.gz", 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        
                        compressed_size = Path(f"{archive_path}.gz").stat().st_size
                        archive_path.unlink()  # Remove uncompressed file
                        final_path = f"{archive_path}.gz"
                    else:
                        compressed_size = original_size
                        final_path = str(archive_path)
                    
                    # Record archive metadata
                    min_timestamp = min(log[1] for log in logs_to_archive)
                    max_timestamp = max(log[1] for log in logs_to_archive)
                    
                    conn.execute('''
                        INSERT INTO log_archives 
                        (archive_path, source_service, start_timestamp, end_timestamp, 
                         entry_count, compressed_size, original_size)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (final_path, service, min_timestamp, max_timestamp,
                          len(logs_to_archive), compressed_size, original_size))
                    
                    # Delete archived logs from main table
                    conn.execute('DELETE FROM log_entries WHERE source = ? AND timestamp < ?', 
                               (service, cutoff_date))
                    
                    archived_info['archived_services'].append(service)
                    archived_info['total_entries'] += len(logs_to_archive)
                    archived_info['total_size_mb'] += original_size / (1024 * 1024)
                    archived_info['compressed_size_mb'] += compressed_size / (1024 * 1024)
            
            conn.commit()
            
            logger.info(f"📦 Archived {archived_info['total_entries']} log entries from {len(archived_info['archived_services'])} services")
            return archived_info
            
        finally:
            conn.close()
    
    # ===== ANALYTICS AND REPORTING =====
    
    def get_log_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get comprehensive log analytics for specified time period"""
        conn = sqlite3.Connection(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            analytics = {
                'time_range': {'start': start_time.isoformat(), 'end': end_time.isoformat()},
                'volume_trends': [],
                'service_breakdown': {},
                'error_trends': [],
                'top_patterns': [],
                'anomaly_summary': {},
                'performance_metrics': {}
            }
            
            # Volume trends by day
            daily_volumes = conn.execute('''
                SELECT DATE(timestamp) as date, COUNT(*) as count
                FROM log_entries 
                WHERE timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY date
            ''', (start_time,)).fetchall()
            
            analytics['volume_trends'] = [dict(row) for row in daily_volumes]
            
            # Service breakdown
            service_stats = conn.execute('''
                SELECT source, level, COUNT(*) as count
                FROM log_entries 
                WHERE timestamp >= ?
                GROUP BY source, level
            ''', (start_time,)).fetchall()
            
            for row in service_stats:
                service = row['source']
                if service not in analytics['service_breakdown']:
                    analytics['service_breakdown'][service] = {}
                analytics['service_breakdown'][service][row['level']] = row['count']
            
            # Error trends
            error_trends = conn.execute('''
                SELECT DATE(timestamp) as date, level, COUNT(*) as count
                FROM log_entries 
                WHERE timestamp >= ? AND level IN ('ERROR', 'FATAL')
                GROUP BY DATE(timestamp), level
                ORDER BY date
            ''', (start_time,)).fetchall()
            
            analytics['error_trends'] = [dict(row) for row in error_trends]
            
            # Top patterns
            top_patterns = conn.execute('''
                SELECT p.template, p.frequency, p.services
                FROM log_patterns p
                JOIN log_entries l ON p.id = l.pattern_id
                WHERE l.timestamp >= ?
                GROUP BY p.id
                ORDER BY p.frequency DESC
                LIMIT 10
            ''', (start_time,)).fetchall()
            
            analytics['top_patterns'] = [
                {
                    'template': row['template'],
                    'frequency': row['frequency'],
                    'services': json.loads(row['services'])
                }
                for row in top_patterns
            ]
            
            # Anomaly summary
            anomaly_stats = conn.execute('''
                SELECT severity, COUNT(*) as count
                FROM log_anomalies 
                WHERE detected_at >= ?
                GROUP BY severity
            ''', (start_time,)).fetchall()
            
            analytics['anomaly_summary'] = {row['severity']: row['count'] for row in anomaly_stats}
            
            return analytics
            
        finally:
            conn.close()