"""
数据库模型模块

封装所有数据库操作
"""

import json
import threading
import uuid
import sqlite3

from config import (
    AUTO_REGISTER_COLUMNS
)
from utils import DatabaseError


class Database:
    """数据库操作封装类"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._local = threading.local()
        self._bootstrap()
        self._auto_register_columns()
        self._initialized = True

    def _connect(self):
        """创建数据库连接"""
        return sqlite3.connect(
            'table_signup.db',
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )

    def _get_conn(self):
        """获取当前线程的数据库连接"""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._connect()
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def _bootstrap(self):
        """初始化数据库和表结构"""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS app_rows (
                        table_name TEXT NOT NULL,
                        row_id TEXT NOT NULL,
                        row_data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (table_name, row_id)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS app_table_columns (
                        table_name TEXT NOT NULL,
                        column_name TEXT NOT NULL,
                        PRIMARY KEY (table_name, column_name)
                    )
                    """
                )
                # 创建索引
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_table_updated ON app_rows (table_name, updated_at)"
                )
            finally:
                cursor.close()
        finally:
            conn.close()

    def _sync_columns(self, table_name, columns):
        """同步列定义到 app_table_columns"""
        clean_columns = [str(item).strip() for item in (columns or []) if str(item).strip()]
        if not clean_columns:
            return
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            for column_name in clean_columns:
                cursor.execute(
                    "INSERT OR IGNORE INTO app_table_columns (table_name, column_name) VALUES (?, ?)",
                    (table_name, column_name)
                )
            conn.commit()
        finally:
            cursor.close()

    def _auto_register_columns(self):
        """启动时自动注册列"""
        for table_name, columns in AUTO_REGISTER_COLUMNS.items():
            try:
                self._sync_columns(table_name, columns)
            except Exception as e:
                print(f"[WARN] Auto register columns for {table_name} failed: {e}")
        print("[INFO] Auto register columns completed")

    # ===== CRUD 操作 =====

    def list_rows(self, table_name):
        """获取表中所有行"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT row_id, row_data FROM app_rows WHERE table_name=? ORDER BY created_at ASC",
                (table_name,),
            )
            rows = cursor.fetchall() or []
        finally:
            cursor.close()
        result = []
        for row in rows:
            payload = row["row_data"]
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    continue
            if isinstance(payload, dict):
                payload["_id"] = row["row_id"]
                result.append(payload)
        return result

    def get_row(self, table_name, row_id):
        """获取单行"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT row_id, row_data FROM app_rows WHERE table_name=? AND row_id=?",
                (table_name, row_id),
            )
            row = cursor.fetchone()
        finally:
            cursor.close()
        if not row:
            return None
        payload = row["row_data"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        if isinstance(payload, dict):
            payload["_id"] = row["row_id"]
        return payload

    def append_row(self, table_name, row_data):
        """新增行"""
        row_id = uuid.uuid4().hex
        payload = dict(row_data or {})
        payload.pop("_id", None)
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO app_rows (table_name, row_id, row_data) VALUES (?, ?, ?)",
                (table_name, row_id, json.dumps(payload, ensure_ascii=False)),
            )
            conn.commit()
        finally:
            cursor.close()
        return row_id

    def update_row(self, table_name, row_id, row_data):
        """更新行"""
        payload = dict(row_data or {})
        payload.pop("_id", None)
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE app_rows SET row_data=?, updated_at=CURRENT_TIMESTAMP WHERE table_name=? AND row_id=?",
                (json.dumps(payload, ensure_ascii=False), table_name, row_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()

    def delete_row(self, table_name, row_id):
        """删除行"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM app_rows WHERE table_name=? AND row_id=?",
                (table_name, row_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()

    def get_registered_columns(self, table_name):
        """获取已注册的列"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT column_name FROM app_table_columns WHERE table_name=?",
                (table_name,),
            )
            return {row["column_name"] for row in (cursor.fetchall() or [])}
        finally:
            cursor.close()


# 单例实例
db = Database()