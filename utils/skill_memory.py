import sqlite3
import os
import json
import time
from typing import List, Dict, Optional

class SkillMemory:
    """
    轻量 SQLite 经验反思库 (SkillMemory v2.1)
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
        """
        静态安全查询经验记录，避免动态拼接 SQL 触发静态安全扫描警报 (针对 Sourcery-AI 强化)
        """
        safe_limit = max(1, min(limit if isinstance(limit, int) else 5, 50))
        
        # 静态参数化 SQL 模板，纯依靠参数占位符 (?) 匹配，消除动态拼接风险
        sql = """
            SELECT id, task_type, target_file, error_signature, resolution_summary, is_success, created_at
            FROM skill_records
            WHERE plugin_name = ?
              AND (? IS NULL OR task_type = ?)
              AND (? IS NULL OR error_signature LIKE ?)
              AND (? IS NULL OR is_success = ?)
            ORDER BY created_at DESC
            LIMIT ?
        """
        pattern = f"%{error_signature}%" if error_signature else None
        succ_val = 1 if is_success is True else (0 if is_success is False else None)
        
        params = (
            plugin_name,
            task_type, task_type,
            pattern, pattern,
            succ_val, succ_val,
            safe_limit
        )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
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
