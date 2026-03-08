import os
import threading
from collections import Counter

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

# Protect check+insert in single-process deployment to reduce race conditions.
submit_lock = threading.Lock()


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

    with submit_lock:
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

    return jsonify({"ok": True, "message": "报名成功"})


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "8080"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)
