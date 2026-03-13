import json
import os
import uuid

from dotenv import load_dotenv

try:
    import pymysql
except Exception as exc:
    raise RuntimeError("缺少 pymysql 依赖，请先安装 requirements.txt") from exc

try:
    from seatable_api import Base
except Exception as exc:
    raise RuntimeError("缺少 seatable-api 依赖，请先安装 requirements.txt") from exc


load_dotenv()

SERVER_URL = os.getenv("SEATABLE_SERVER_URL", "https://table.nju.edu.cn").rstrip("/")
API_TOKEN = os.getenv("SEATABLE_API_TOKEN", "").strip()

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1").strip()
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root").strip()
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "").strip()
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "table_signup").strip()

TABLE_NAMES = [
    os.getenv("ACTIVITY_TABLE_NAME", "分享会活动"),
    os.getenv("SIGNUP_TABLE_NAME", "分享会报名"),
    os.getenv("REVIEW_RATING_TABLE_NAME", "评议评分"),
    os.getenv("OUTPUT_RECORD_TABLE_NAME", "输出活动记录"),
    os.getenv("USER_PROFILE_TABLE_NAME", "用户档案"),
    os.getenv("INTEREST_GROUP_TABLE_NAME", "兴趣组"),
    os.getenv("GROUP_MEMBER_TABLE_NAME", "兴趣组成员"),
    os.getenv("REVIEW_INVITE_TABLE_NAME", "评议邀请"),
]


def get_mysql_conn(database=None):
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=database,
        charset="utf8mb4",
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )


def bootstrap_mysql():
    conn = get_mysql_conn(None)
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    finally:
        conn.close()

    conn = get_mysql_conn(MYSQL_DATABASE)
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


def migrate_table(base, conn, table_name):
    rows = base.list_rows(table_name) or []
    if not rows:
        print(f"[SKIP] {table_name}: 0 rows")
        return

    row_values = []
    all_columns = set()
    for row in rows:
        row_id = str(row.get("_id") or uuid.uuid4().hex)
        payload = dict(row)
        payload.pop("_id", None)
        all_columns.update(payload.keys())
        row_values.append((table_name, row_id, json.dumps(payload, ensure_ascii=False)))

    with conn.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO app_rows (table_name, row_id, row_data)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE row_data=VALUES(row_data), updated_at=CURRENT_TIMESTAMP
            """,
            row_values,
        )
        if all_columns:
            cursor.executemany(
                "INSERT IGNORE INTO app_table_columns (table_name, column_name) VALUES (%s, %s)",
                [(table_name, str(col).strip()) for col in all_columns if str(col).strip()],
            )

    print(f"[OK] {table_name}: migrated {len(rows)} rows")


def main():
    if not API_TOKEN:
        raise RuntimeError("SEATABLE_API_TOKEN 为空，无法迁移")

    base = Base(API_TOKEN, SERVER_URL)
    base.auth()

    bootstrap_mysql()
    conn = get_mysql_conn(MYSQL_DATABASE)
    try:
        for table_name in TABLE_NAMES:
            migrate_table(base, conn, table_name)
    finally:
        conn.close()

    print("迁移完成。请将 DB_BACKEND=mysql 后重启服务。")


if __name__ == "__main__":
    main()
