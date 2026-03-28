"""
模型模块

导出数据库操作和模型类
"""

import os

from models.database import db, Database
from utils import DatabaseError

# ===== 输出活动记录表常量 =====
OUTPUT_RECORD_TABLE_NAME = os.getenv("OUTPUT_RECORD_TABLE_NAME", "输出活动记录")
OUTPUT_RECORD_COL_NAME = os.getenv("OUTPUT_RECORD_COL_NAME", "姓名")
OUTPUT_RECORD_COL_TYPE = os.getenv("OUTPUT_RECORD_COL_TYPE", "输出类型")
OUTPUT_RECORD_COL_DATE = os.getenv("OUTPUT_RECORD_COL_DATE", "输出日期")
OUTPUT_RECORD_COL_NOTE = os.getenv("OUTPUT_RECORD_COL_NOTE", "备注")

__all__ = [
    "db", "Database", "DatabaseError",
    "OUTPUT_RECORD_TABLE_NAME", "OUTPUT_RECORD_COL_NAME",
    "OUTPUT_RECORD_COL_TYPE", "OUTPUT_RECORD_COL_DATE", "OUTPUT_RECORD_COL_NOTE"
]