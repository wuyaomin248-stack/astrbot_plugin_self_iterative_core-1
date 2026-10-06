import sqlite3
import os
import json
import time
from typing import List, Dict, Optional

class SkillMemory:
    """
    轻量 SQLite 经验反思库 (SkillMemory)
    记录每次排障、迭代的成败特征与自愈方案，防止重复踩坑
    由 日海 & 橙子汐 架构贡献设计
    """
    def __init__(self, db_path: str = "./data/skill_memory.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skill_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_name TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    target_file TEXT,
                    error_signature TEXT,
                    resolution_summary TEXT NOT NULL,
                    is_success INTEGER NOT NULL,
                    created_at REAL NOT NULL
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_plugin_err 
                ON skill_records(plugin_name, is_success);
            """)
            conn.commit()

    def record_experience(self, plugin_name: str, task_type: str, resolution_summary: str, 
                          is_success: bool = True, target_file: str = "", error_signature: str = ""):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO skill_records 
                (plugin_name, task_type, target_file, error_signature, resolution_summary, is_success, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (plugin_name, task_type, target_file, error_signature, resolution_summary, 1 if is_success else 0, time.time()))
            conn.commit()

    def query_experience(self, plugin_name: str, limit: int = 5) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, task_type, target_file, error_signature, resolution_summary, is_success, created_at
                FROM skill_records
                WHERE plugin_name = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (plugin_name, limit))
            rows = cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "task_type": r[1],
                    "target_file": r[2],
                    "error_signature": r[3],
                    "resolution_summary": r[4],
                    "is_success": bool(r[5]),
                    "created_at": r[6]
                }
                for r in rows
            ]
