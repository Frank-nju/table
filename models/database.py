"""
数据库模型模块

封装所有数据库操作
"""

import json
import logging
import threading
import uuid
import pymysql
from pymysql import cursors

from config import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE,
    MYSQL_CONNECT_TIMEOUT, MYSQL_READ_TIMEOUT, MYSQL_WRITE_TIMEOUT,
    AUTO_REGISTER_COLUMNS
)
from utils import DatabaseError

logger = logging.getLogger(__name__)


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

    def _connect(self, database=None):
        """创建数据库连接"""
        return pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=database,
            charset="utf8mb4",
            autocommit=True,
            cursorclass=cursors.DictCursor,
            connect_timeout=MYSQL_CONNECT_TIMEOUT,
            read_timeout=MYSQL_READ_TIMEOUT,
            write_timeout=MYSQL_WRITE_TIMEOUT,
        )

    def _get_conn(self):
        """获取当前线程的数据库连接"""
        conn = getattr(self._local, "conn", None)
        if conn is None or not getattr(conn, "open", False):
            conn = self._connect(MYSQL_DATABASE)
            self._local.conn = conn
        else:
            conn.ping(reconnect=True)
        return conn

    def _bootstrap(self):
        """初始化数据库和表结构"""
        # 校验数据库名，防止 SQL 注入
        if not MYSQL_DATABASE or not MYSQL_DATABASE.isidentifier():
            raise ValueError(f"Invalid database name: {MYSQL_DATABASE!r}")
        server_conn = self._connect(None)
        try:
            with server_conn.cursor() as cursor:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
        finally:
            server_conn.close()

        conn = self._connect(MYSQL_DATABASE)
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS app_rows (
                        table_name VARCHAR(191) NOT NULL,
                        row_id VARCHAR(64) NOT NULL,
                        row_data JSON NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (table_name, row_id),
                        KEY idx_table_updated (table_name, updated_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS app_table_columns (
                        table_name VARCHAR(191) NOT NULL,
                        column_name VARCHAR(191) NOT NULL,
                        PRIMARY KEY (table_name, column_name)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
        finally:
            conn.close()

    def _sync_columns(self, table_name, columns):
        """同步列定义到 app_table_columns"""
        clean_columns = [str(item).strip() for item in (columns or []) if str(item).strip()]
        if not clean_columns:
            return
        conn = self._get_conn()
        with conn.cursor() as cursor:
            cursor.executemany(
                "INSERT IGNORE INTO app_table_columns (table_name, column_name) VALUES (%s, %s)",
                [(table_name, column_name) for column_name in clean_columns],
            )

    def _auto_register_columns(self):
        """启动时自动注册列"""
        for table_name, columns in AUTO_REGISTER_COLUMNS.items():
            try:
                self._sync_columns(table_name, columns)
            except Exception as e:
                logger.warning("Auto register columns for %s failed: %s", table_name, e)
        logger.info("Auto register columns completed")

    # ===== CRUD 操作 =====

    def list_rows(self, table_name):
        """获取表中所有行"""
        conn = self._get_conn()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT row_id, row_data FROM app_rows WHERE table_name=%s ORDER BY created_at ASC",
                (table_name,),
            )
            rows = cursor.fetchall() or []
        result = []
        for row in rows:
            payload = row.get("row_data")
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    continue
            if isinstance(payload, dict):
                payload["_id"] = row.get("row_id")
                result.append(payload)
        return result

    def get_row(self, table_name, row_id):
        """获取单行"""
        conn = self._get_conn()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT row_id, row_data FROM app_rows WHERE table_name=%s AND row_id=%s",
                (table_name, row_id),
            )
            row = cursor.fetchone()
        if not row:
            return None
        payload = row.get("row_data")
        if isinstance(payload, str):
            payload = json.loads(payload)
        if isinstance(payload, dict):
            payload["_id"] = row.get("row_id")
        return payload

    def append_row(self, table_name, row_data):
        """新增行"""
        row_id = uuid.uuid4().hex
        payload = dict(row_data or {})
        payload.pop("_id", None)
        conn = self._get_conn()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO app_rows (table_name, row_id, row_data) VALUES (%s, %s, %s)",
                (table_name, row_id, json.dumps(payload, ensure_ascii=False)),
            )
        # 写入后同步列定义，确保后续 _filter_append_row_data 不会过滤新列
        self._sync_columns(table_name, payload.keys())
        return {"_id": row_id, **payload}

    def update_row(self, table_name, row_id, row_data):
        """更新行"""
        payload = dict(row_data or {})
        payload.pop("_id", None)
        conn = self._get_conn()
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE app_rows SET row_data=%s WHERE table_name=%s AND row_id=%s",
                (json.dumps(payload, ensure_ascii=False), table_name, row_id),
            )
            affected = cursor.rowcount > 0
        # 写入后同步列定义
        self._sync_columns(table_name, payload.keys())
        return {"_id": row_id, **payload} if affected else None

    def delete_row(self, table_name, row_id):
        """删除行"""
        conn = self._get_conn()
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM app_rows WHERE table_name=%s AND row_id=%s",
                (table_name, row_id),
            )
            return cursor.rowcount > 0

    def get_registered_columns(self, table_name):
        """获取已注册的列"""
        conn = self._get_conn()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM app_table_columns WHERE table_name=%s",
                (table_name,),
            )
            return {row.get("column_name") for row in (cursor.fetchall() or [])}

    def list_columns(self, table_name):
        """列出已注册列（兼容 SeaTable 接口）"""
        columns = self.get_registered_columns(table_name)
        return [{"name": col} for col in sorted(columns)]

    def add_table(self, table_name, *args):
        """添加表（MySQL 模式无操作，仅兼容 SeaTable 接口）"""
        return {"name": table_name, "ok": True}

    def insert_column(self, table_name, column_name, *args):
        """插入列（MySQL 模式仅同步列定义，兼容 SeaTable 接口）"""
        self._sync_columns(table_name, [column_name])
        return {"table": table_name, "column": column_name, "ok": True}


# 单例实例
db = Database()