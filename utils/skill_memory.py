import sqlite3
import os
import json
import time
from typing import List, Dict, Optional

class SkillMemory:
    """
    轻量 SQLite 经验反思库 (SkillMemory v2)
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
                ON skill_records(plugin_name, task_type, is_success);
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

    def query_experience(self, plugin_name: str, task_type: Optional[str] = None, 
                         error_signature: Optional[str] = None, is_success: Optional[bool] = None,
                         limit: int = 5) -> List[Dict]:
        safe_limit = max(1, min(limit if isinstance(limit, int) else 5, 50))
        conditions = ["plugin_name = ?"]
        params = [plugin_name]

        if task_type:
            conditions.append("task_type = ?")
            params.append(task_type)
        if error_signature:
            conditions.append("error_signature LIKE ?")
            params.append(f"%{error_signature}%")
        if is_success is not None:
            conditions.append("is_success = ?")
            params.append(1 if is_success else 0)

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT id, task_type, target_file, error_signature, resolution_summary, is_success, created_at
            FROM skill_records
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(safe_limit)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, tuple(params))
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
