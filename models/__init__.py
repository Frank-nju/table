"""
模型模块

导出数据库操作和模型类
"""

from models.database import db, Database
from utils import DatabaseError

__all__ = [
    "db", "Database", "DatabaseError",
]