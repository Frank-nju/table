import contextlib
import os
import threading
import uuid
from collections import Counter

import redis as redis_lib
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from seatable_api import Base


load_dotenv()

SERVER_URL = os.getenv("SEATABLE_SERVER_URL", "https://table.nju.edu.cn").rstrip("/")
API_TOKEN = os.getenv("SEATABLE_API_TOKEN", "")
TABLE_NAME = os.getenv("SEATABLE_TABLE_NAME", "报名表")
COL_NAME = os.getenv("COL_NAME", "姓名")
COL_STUDENT_ID = os.getenv("COL_STUDENT_ID", "学号")
COL_ITEM = os.getenv("COL_ITEM", "子项")
ITEM_LIMIT = int(os.getenv("ITEM_LIMIT", "15"))
FORM_ITEMS = [x.strip() for x in os.getenv("FORM_ITEMS", "A,B,C").split(",") if x.strip()]

# Redis distributed lock configuration (optional).
# Set REDIS_URL to enable cross-process locking (required for multi-worker gunicorn).
# Falls back to a threading.Lock when Redis is not configured (single-process only).
REDIS_URL = os.getenv("REDIS_URL", "")
REDIS_LOCK_KEY = os.getenv("REDIS_LOCK_KEY", "table_signup_lock")
REDIS_LOCK_TIMEOUT = int(os.getenv("REDIS_LOCK_TIMEOUT", "10"))

if not API_TOKEN:
    raise RuntimeError("SEATABLE_API_TOKEN is required. Please set it in .env.")


base = Base(API_TOKEN, SERVER_URL)
try:
    base.auth()
except Exception as exc:
    raise RuntimeError(
        "SeaTable 认证失败。请确认使用的是 Base 的 API Token（不是账号令牌），"
        "并且该 Token 对目标表有读写权限。"
    ) from exc

app = Flask(__name__)

# In-process fallback lock (only effective within a single process/thread).
_local_lock = threading.Lock()

# Redis client (None when Redis is not configured).
_redis_client: redis_lib.Redis | None = None
if REDIS_URL:
    try:
        _redis_client = redis_lib.from_url(REDIS_URL, decode_responses=True)
        _redis_client.ping()
    except Exception as exc:
        app.logger.warning("Redis 连接失败，回退到本地锁（仅单进程安全）：%s", exc)
        _redis_client = None


@contextlib.contextmanager
def _submit_lock():
    """Distributed lock backed by Redis, with a threading.Lock fallback.

    Redis lock uses the SET NX PX pattern so the lock is automatically
    released if the process crashes within REDIS_LOCK_TIMEOUT seconds.
    """
    if _redis_client is not None:
        token = str(uuid.uuid4())
        acquired = False
        try:
            acquired = bool(
                _redis_client.set(
                    REDIS_LOCK_KEY,
                    token,
                    nx=True,
                    px=REDIS_LOCK_TIMEOUT * 1000,
                )
            )
            if not acquired:
                raise RuntimeError("系统繁忙，请稍后重试")
            yield
        finally:
            if acquired:
                # Only release the lock if we still own it (Lua script for atomicity).
                _lua_release = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """
                _redis_client.eval(_lua_release, 1, REDIS_LOCK_KEY, token)
    else:
        with _local_lock:
            yield


def _list_rows():
    rows = base.list_rows(TABLE_NAME)
    return rows or []


def _count_items(rows):
    counts = Counter()
    for row in rows:
        item = str(row.get(COL_ITEM, "")).strip()
        if item in FORM_ITEMS:
            counts[item] += 1
    return {item: counts.get(item, 0) for item in FORM_ITEMS}


def _full_flags(counts):
    return {item: (counts.get(item, 0) >= ITEM_LIMIT) for item in FORM_ITEMS}


@app.get("/")
def index():
    return render_template("index.html", items=FORM_ITEMS, limit=ITEM_LIMIT)


@app.get("/healthz")
def healthz():
    return jsonify({"ok": True}), 200


@app.get("/api/stats")
def api_stats():
    rows = _list_rows()
    counts = _count_items(rows)
    return jsonify(
        {
            "ok": True,
            "limit": ITEM_LIMIT,
            "counts": counts,
            "closed": _full_flags(counts),
        }
    )


@app.post("/api/submit")
def api_submit():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    student_id = str(data.get("student_id", "")).strip()
    item = str(data.get("item", "")).strip()

    if not name or not student_id or not item:
        return jsonify({"ok": False, "message": "请完整填写姓名、学号和子项"}), 400

    if item not in FORM_ITEMS:
        return jsonify({"ok": False, "message": "子项无效"}), 400

    try:
        with _submit_lock():
            rows = _list_rows()
            counts = _count_items(rows)

            if counts.get(item, 0) >= ITEM_LIMIT:
                return jsonify({"ok": False, "message": f"{item} 已满 {ITEM_LIMIT} 人，已停止报名"}), 409

            # Optional: block duplicate student IDs.
            for row in rows:
                sid = str(row.get(COL_STUDENT_ID, "")).strip()
                if sid and sid == student_id:
                    return jsonify({"ok": False, "message": "该学号已报名，不能重复提交"}), 409

            row_data = {
                COL_NAME: name,
                COL_STUDENT_ID: student_id,
                COL_ITEM: item,
            }
            base.append_row(TABLE_NAME, row_data)
    except RuntimeError as exc:
        return jsonify({"ok": False, "message": str(exc)}), 503

    return jsonify({"ok": True, "message": "报名成功"})


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "8080"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)
