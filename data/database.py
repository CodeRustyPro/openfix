"""Database models and schema for OpenFix."""
import sqlite3
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from pathlib import Path


class Database:
    """SQLite database manager for OpenFix."""
    
    def __init__(self, db_path: str):
        """Initialize database connection."""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """Create database schema if it doesn't exist."""
        cursor = self.conn.cursor()
        
        # Repositories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                github_url TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                language TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Issues table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repository_id INTEGER NOT NULL,
                github_issue_number INTEGER NOT NULL,
                title TEXT NOT NULL,
                body TEXT,
                labels TEXT,  -- JSON array
                status TEXT DEFAULT 'NEW',  -- NEW, ANALYZING, PATCHED, PR_CREATED, MERGED
                difficulty_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (repository_id) REFERENCES repositories(id),
                UNIQUE(repository_id, github_issue_number)
            )
        """)
        
        # Patches table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id INTEGER NOT NULL,
                run_id TEXT NOT NULL,
                diff_content TEXT NOT NULL,
                status TEXT DEFAULT 'GENERATED',  -- GENERATED, VALIDATED, APPLIED, PR_CREATED, MERGED, FAILED
                validation_passed BOOLEAN,
                tests_run INTEGER,
                tests_passed INTEGER,
                lint_warnings INTEGER,
                pr_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (issue_id) REFERENCES issues(id)
            )
        """)
        
        # Runs table - tracks each execution
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT UNIQUE NOT NULL,
                repository_id INTEGER NOT NULL,
                issue_id INTEGER,
                status TEXT DEFAULT 'RUNNING',  -- RUNNING, SUCCESS, FAILED
                prompt_tokens INTEGER,
                response_tokens INTEGER,
                cost_usd REAL,
                chunks_selected INTEGER,
                artifacts_path TEXT,
                error_message TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (repository_id) REFERENCES repositories(id),
                FOREIGN KEY (issue_id) REFERENCES issues(id)
            )
        """)
        
        self.conn.commit()
    
    def insert_repository(self, github_url: str, name: str, language: Optional[str] = None) -> int:
        """Insert or get repository."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO repositories (github_url, name, language) VALUES (?, ?, ?)",
            (github_url, name, language)
        )
        self.conn.commit()
        
        cursor.execute("SELECT id FROM repositories WHERE github_url = ?", (github_url,))
        return cursor.fetchone()[0]
    
    def insert_issue(self, repository_id: int, github_issue_number: int, 
                    title: str, body: str, labels: List[str]) -> int:
        """Insert or get issue."""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR IGNORE INTO issues 
               (repository_id, github_issue_number, title, body, labels) 
               VALUES (?, ?, ?, ?, ?)""",
            (repository_id, github_issue_number, title, body, json.dumps(labels))
        )
        self.conn.commit()
        
        cursor.execute(
            "SELECT id FROM issues WHERE repository_id = ? AND github_issue_number = ?",
            (repository_id, github_issue_number)
        )
        return cursor.fetchone()[0]
    
    def insert_run(self, run_id: str, repository_id: int, issue_id: Optional[int] = None) -> int:
        """Insert a new run."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO runs (run_id, repository_id, issue_id) VALUES (?, ?, ?)",
            (run_id, repository_id, issue_id)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def update_run(self, run_id: str, **kwargs):
        """Update run with metrics and status."""
        valid_fields = {
            'status', 'prompt_tokens', 'response_tokens', 'cost_usd',
            'chunks_selected', 'artifacts_path', 'error_message', 'completed_at'
        }
        
        updates = {k: v for k, v in kwargs.items() if k in valid_fields}
        if not updates:
            return
        
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [run_id]
        
        cursor = self.conn.cursor()
        cursor.execute(f"UPDATE runs SET {set_clause} WHERE run_id = ?", values)
        self.conn.commit()
    
    def insert_patch(self, issue_id: int, run_id: str, diff_content: str, **kwargs) -> int:
        """Insert a generated patch."""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO patches 
               (issue_id, run_id, diff_content, validation_passed, tests_run, 
                tests_passed, lint_warnings, status) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (issue_id, run_id, diff_content,
             kwargs.get('validation_passed'),
             kwargs.get('tests_run'),
             kwargs.get('tests_passed'),
             kwargs.get('lint_warnings'),
             kwargs.get('status', 'GENERATED'))
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_issue(self, issue_id: int) -> Optional[Dict]:
        """Get issue by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM issues WHERE id = ?", (issue_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def close(self):
        """Close database connection."""
        self.conn.close()
