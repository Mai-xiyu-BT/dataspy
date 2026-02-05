#!/usr/bin/env python3
"""
DataSpy - Data Monitoring Service
Monitor any URL/endpoint for changes, send alerts on detection
"""

import json
import hashlib
import sqlite3
import requests
import smtplib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import threading
from dataclasses import dataclass, asdict
from enum import Enum

CONFIG_DIR = Path.home() / ".config" / "dataspy"
DATA_DIR = Path.home() / ".local" / "share" / "dataspy"

class ChangeType(Enum):
    CONTENT_CHANGED = "content_changed"
    PRICE_DROPPED = "price_dropped"
    PRICE_ROSE = "price_rose"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    NEW_ELEMENT = "new_element"

@dataclass
class MonitorTask:
    id: str
    name: str
    url: str
    check_type: str  # 'full_page', 'selector', 'json_api', 'price'
    selector: Optional[str] = None  # CSS selector for targeted monitoring
    json_path: Optional[str] = None  # JSON path for API monitoring
    check_interval: int = 3600  # seconds
    last_check: Optional[datetime] = None
    last_content_hash: Optional[str] = None
    last_value: Optional[str] = None
    enabled: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class ChangeEvent:
    id: str
    task_id: str
    timestamp: datetime
    change_type: ChangeType
    old_value: Optional[str]
    new_value: Optional[str]
    screenshot_path: Optional[str] = None
    diff_summary: str = ""

class DataSpyCore:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "snapshots").mkdir(exist_ok=True)
        self.init_database()
        self.tasks: Dict[str, MonitorTask] = {}
        self.load_tasks()
    
    def init_database(self):
        """Initialize SQLite database."""
        db_path = DATA_DIR / "dataspy.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                check_type TEXT NOT NULL,
                selector TEXT,
                json_path TEXT,
                check_interval INTEGER DEFAULT 3600,
                last_check TIMESTAMP,
                last_content_hash TEXT,
                last_value TEXT,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                change_type TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                diff_summary TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS snapshots (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                content_hash TEXT NOT NULL,
                content_path TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def load_tasks(self):
        """Load tasks from database."""
        db_path = DATA_DIR / "dataspy.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tasks")
        rows = cursor.fetchall()
        
        for row in rows:
            task = MonitorTask(
                id=row[0],
                name=row[1],
                url=row[2],
                check_type=row[3],
                selector=row[4],
                json_path=row[5],
                check_interval=row[6],
                last_check=datetime.fromisoformat(row[7]) if row[7] else None,
                last_content_hash=row[8],
                last_value=row[9],
                enabled=bool(row[10]),
                created_at=datetime.fromisoformat(row[11]) if row[11] else datetime.now()
            )
            self.tasks[task.id] = task
        
        conn.close()
    
    def add_task(self, task: MonitorTask) -> Dict:
        """Add a new monitoring task."""
        # Save to database
        db_path = DATA_DIR / "dataspy.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO tasks 
            (id, name, url, check_type, selector, json_path, check_interval, enabled, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task.id, task.name, task.url, task.check_type,
            task.selector, task.json_path, task.check_interval,
            task.enabled, task.created_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        self.tasks[task.id] = task
        return {"success": True, "task_id": task.id}
    
    def check_task(self, task_id: str) -> Optional[ChangeEvent]:
        """Check a single task for changes."""
        task = self.tasks.get(task_id)
        if not task or not task.enabled:
            return None
        
        try:
            # Fetch content
            response = requests.get(task.url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            content = response.text
            
            # Calculate hash
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            # Check for changes
            if task.last_content_hash and task.last_content_hash != content_hash:
                # Content changed
                event = ChangeEvent(
                    id=f"evt_{int(time.time())}_{task_id}",
                    task_id=task_id,
                    timestamp=datetime.now(),
                    change_type=ChangeType.CONTENT_CHANGED,
                    old_value=task.last_content_hash[:16] + "...",
                    new_value=content_hash[:16] + "...",
                    diff_summary=f"Content changed ({len(content)} bytes)"
                )
                
                # Save snapshot
                self._save_snapshot(task_id, content, content_hash)
                
                # Update task
                task.last_content_hash = content_hash
                task.last_check = datetime.now()
                self._update_task_in_db(task)
                
                # Save event
                self._save_event(event)
                
                return event
            else:
                # No change, just update last_check
                task.last_check = datetime.now()
                self._update_task_in_db(task)
                return None
                
        except Exception as e:
            print(f"Error checking task {task_id}: {e}")
            return None
    
    def _save_snapshot(self, task_id: str, content: str, content_hash: str):
        """Save content snapshot."""
        snapshot_id = f"snap_{int(time.time())}_{task_id}"
        snapshot_path = DATA_DIR / "snapshots" / f"{snapshot_id}.html"
        snapshot_path.write_text(content)
        
        db_path = DATA_DIR / "dataspy.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO snapshots (id, task_id, content_hash, content_path)
            VALUES (?, ?, ?, ?)
        ''', (snapshot_id, task_id, content_hash, str(snapshot_path)))
        conn.commit()
        conn.close()
    
    def _save_event(self, event: ChangeEvent):
        """Save change event to database."""
        db_path = DATA_DIR / "dataspy.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO events (id, task_id, timestamp, change_type, old_value, new_value, diff_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.id, event.task_id, event.timestamp.isoformat(),
            event.change_type.value, event.old_value, event.new_value, event.diff_summary
        ))
        conn.commit()
        conn.close()
    
    def _update_task_in_db(self, task: MonitorTask):
        """Update task in database."""
        db_path = DATA_DIR / "dataspy.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE tasks SET 
                last_check = ?, last_content_hash = ?, last_value = ?
            WHERE id = ?
        ''', (
            task.last_check.isoformat() if task.last_check else None,
            task.last_content_hash,
            task.last_value,
            task.id
        ))
        conn.commit()
        conn.close()
    
    def run_monitor(self, interval: int = 60):
        """Main monitoring loop."""
        print(f"DataSpy monitor started (check interval: {interval}s)")
        while True:
            for task_id, task in self.tasks.items():
                if not task.enabled:
                    continue
                
                # Check if it's time to check this task
                if task.last_check:
                    time_since_check = (datetime.now() - task.last_check).total_seconds()
                    if time_since_check < task.check_interval:
                        continue
                
                # Check the task
                event = self.check_task(task_id)
                if event:
                    print(f"🚨 CHANGE DETECTED: {task.name}")
                    print(f"   {event.diff_summary}")
                    # TODO: Send notification
                else:
                    print(f"✓ {task.name} - no change")
            
            time.sleep(interval)
    
    def get_events(self, task_id: Optional[str] = None, limit: int = 50) -> List[ChangeEvent]:
        """Get change events."""
        db_path = DATA_DIR / "dataspy.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        if task_id:
            cursor.execute(
                "SELECT * FROM events WHERE task_id = ? ORDER BY timestamp DESC LIMIT ?",
                (task_id, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
        
        rows = cursor.fetchall()
        conn.close()
        
        events = []
        for row in rows:
            events.append(ChangeEvent(
                id=row[0],
                task_id=row[1],
                timestamp=datetime.fromisoformat(row[2]),
                change_type=ChangeType(row[3]),
                old_value=row[4],
                new_value=row[5],
                diff_summary=row[6] if len(row) > 6 else ""
            ))
        return events


if __name__ == "__main__":
    spy = DataSpyCore()
    
    # Example: Add a test task
    test_task = MonitorTask(
        id="test_hn",
        name="Hacker News Top",
        url="https://news.ycombinator.com",
        check_type="full_page",
        check_interval=300  # 5 minutes for testing
    )
    
    spy.add_task(test_task)
    print("Test task added. Starting monitor...")
    
    # Run monitor
    spy.run_monitor()
