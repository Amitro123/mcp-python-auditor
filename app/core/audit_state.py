import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)

class AuditStatus(Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class AuditStateManager:
    """
    Manages audit state persistence using SQLite.
    Handles audit runs, tool results, usage metrics, and artifacts.
    """
    def __init__(self, db_path: str = ".audit_state.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema with all required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Enable WAL mode for better concurrency
                conn.execute("PRAGMA journal_mode=WAL;")

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_runs (
                        id TEXT PRIMARY KEY,
                        project_path TEXT,
                        status TEXT,
                        total_tools INTEGER,
                        completed_tools INTEGER DEFAULT 0,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        error TEXT
                    )
                """)
                
                # Simple migration checking
                try:
                    conn.execute("SELECT total_tools FROM audit_runs LIMIT 1")
                except sqlite3.OperationalError:
                    conn.execute("ALTER TABLE audit_runs ADD COLUMN total_tools INTEGER")
                    conn.execute("ALTER TABLE audit_runs ADD COLUMN completed_tools INTEGER DEFAULT 0")
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tool_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        audit_id TEXT,
                        tool_name TEXT,
                        status TEXT,
                        result_json TEXT,
                        duration REAL,
                        error TEXT,
                        created_at TIMESTAMP,
                        FOREIGN KEY (audit_id) REFERENCES audit_runs(id)
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_summary (
                        audit_id TEXT PRIMARY KEY,
                        score INTEGER,
                        grade TEXT,
                        failed_tools TEXT,
                        metrics_json TEXT,
                        FOREIGN KEY (audit_id) REFERENCES audit_runs(id)
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS artifacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        audit_id TEXT,
                        artifact_type TEXT,
                        file_path TEXT,
                        created_at TIMESTAMP,
                        FOREIGN KEY (audit_id) REFERENCES audit_runs(id)
                    )
                """)
        except Exception as e:
            logger.error(f"Failed to initialize audit state DB: {e}")
            raise
    
    def create_audit(self, audit_id: str, project_path: str, total_tools: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO audit_runs (id, project_path, status, total_tools, started_at)
                VALUES (?, ?, ?, ?, ?)
            """, (audit_id, project_path, AuditStatus.SCHEDULED.value, total_tools, datetime.now().isoformat()))
    
    def start_audit(self, audit_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE audit_runs SET status = ? WHERE id = ?
            """, (AuditStatus.IN_PROGRESS.value, audit_id))

    def save_tool_result(self, audit_id: str, tool_name: str, result: dict, duration: float, status: str = 'success', error: str = None):
        """Save execution result for a single tool and update progress."""
        # Use simple string for timestamp to avoid adapter issues
        now_ts = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO tool_results (audit_id, tool_name, status, result_json, duration, error, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (audit_id, tool_name, status, json.dumps(result, default=str), duration, error, now_ts))
            
            # Increment completed count
            conn.execute("""
                UPDATE audit_runs 
                SET completed_tools = completed_tools + 1
                WHERE id = ?
            """, (audit_id,))
            
            conn.commit()
            logger.info(f"[DEBUG] Committed result for {tool_name} (audit={audit_id})")
            
    def get_audit_progress(self, audit_id: str) -> Optional[dict]:
        """Check progress - for polling"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT total_tools, completed_tools, status
                FROM audit_runs WHERE id = ?
            """, (audit_id,))
            row = cursor.fetchone()
            if row:
                total, completed, status = row
                return {
                    'total': total,
                    'completed': completed,
                    'progress': (completed / total * 100) if total > 0 else 0,
                    'is_complete': completed >= total,
                    'status': status
                }
            return None
    
    def get_tool_results(self, audit_id: str) -> Dict[str, dict]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT tool_name, result_json, status, error, duration 
                FROM tool_results
                WHERE audit_id = ? 
                ORDER BY created_at
            """, (audit_id,))
            
            results = {}
            for row in cursor:
                tool_name, result_json, status, error, duration = row
                if status == 'success':
                    try:
                        data = json.loads(result_json)
                        # Inject duration if missing
                        if isinstance(data, dict) and 'duration_seconds' not in data:
                            data['duration_seconds'] = duration
                        results[tool_name] = data
                    except json.JSONDecodeError:
                        results[tool_name] = {'error': "JSON Decode Error", 'status': 'failed'}
                else:
                    results[tool_name] = {'error': error, 'status': 'failed'}
            return results
    
    def complete_audit(self, audit_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE audit_runs 
                SET status = ?, completed_at = ?
                WHERE id = ?
            """, (AuditStatus.COMPLETED.value, datetime.now().isoformat(), audit_id))
    
    def fail_audit(self, audit_id: str, error: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE audit_runs 
                SET status = ?, error = ?, completed_at = ?
                WHERE id = ?
            """, (AuditStatus.FAILED.value, error, datetime.now().isoformat(), audit_id))
    
    def save_audit_summary(self, audit_id: str, summary: dict):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO audit_summary 
                (audit_id, score, grade, failed_tools, metrics_json)
                VALUES (?, ?, ?, ?, ?)
            """, (
                audit_id,
                summary['score'],
                summary['grade'],
                json.dumps(summary.get('failed_tools', [])),
                json.dumps(summary.get('metrics', {}), default=str)
            ))
    
    def save_artifact(self, audit_id: str, artifact_type: str, file_path: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO artifacts (audit_id, artifact_type, file_path, created_at)
                VALUES (?, ?, ?, ?)
            """, (audit_id, artifact_type, file_path, datetime.now().isoformat()))

    def get_audit_status(self, audit_id: str) -> Optional[Dict[str, Any]]:
        """Get full status of a specific audit row."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, project_path, status, started_at, completed_at, error, total_tools, completed_tools 
                FROM audit_runs WHERE id = ?
            """, (audit_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "project_path": row[1],
                    "status": row[2],
                    "started_at": row[3],
                    "completed_at": row[4],
                    "error": row[5],
                    "total_tools": row[6],
                    "completed_tools": row[7]
                }
            return None
