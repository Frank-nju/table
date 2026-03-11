import os
import threading
from datetime import datetime, timedelta
from collections import Counter, defaultdict

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from seatable_api import Base


load_dotenv()

SERVER_URL = os.getenv("SEATABLE_SERVER_URL", "https://table.nju.edu.cn").rstrip("/")
API_TOKEN = os.getenv("SEATABLE_API_TOKEN", "")

# ===== 表名配置 =====
ACTIVITY_TABLE_NAME = os.getenv("ACTIVITY_TABLE_NAME", "分享会活动")
SIGNUP_TABLE_NAME = os.getenv("SIGNUP_TABLE_NAME", "分享会报名")

# ===== 活动表字段 =====
ACTIVITY_COL_DATE = os.getenv("ACTIVITY_COL_DATE", "活动日期")
ACTIVITY_COL_TIME = os.getenv("ACTIVITY_COL_TIME", "活动时间")
ACTIVITY_COL_SPEAKERS = os.getenv("ACTIVITY_COL_SPEAKERS", "分享者")
ACTIVITY_COL_TOPIC = os.getenv("ACTIVITY_COL_TOPIC", "活动主题")
ACTIVITY_COL_CLASSROOM = os.getenv("ACTIVITY_COL_CLASSROOM", "活动教室")
ACTIVITY_COL_VIDEOURL = os.getenv("ACTIVITY_COL_VIDEOURL", "线上视频号")
ACTIVITY_COL_CREATOR_STUDENT_ID = os.getenv("ACTIVITY_COL_CREATOR_STUDENT_ID", "组织者学号")

# ===== 报名表字段 =====
SIGNUP_COL_NAME = os.getenv("SIGNUP_COL_NAME", "姓名")
SIGNUP_COL_STUDENT_ID = os.getenv("SIGNUP_COL_STUDENT_ID", "学号")
SIGNUP_COL_ACTIVITY_ID = os.getenv("SIGNUP_COL_ACTIVITY_ID", "关联活动")
SIGNUP_COL_ROLE = os.getenv("SIGNUP_COL_ROLE", "角色")
SIGNUP_COL_PHONE = os.getenv("SIGNUP_COL_PHONE", "联系电话")

# ===== 报名限额配置 =====
REVIEWER_LIMIT = int(os.getenv("REVIEWER_LIMIT", "3"))
LISTENER_UNLIMITED = os.getenv("LISTENER_UNLIMITED", "true").lower() == "true"

# ===== 时间槽配置 =====
TIME_SLOTS = [x.strip() for x in os.getenv("TIME_SLOTS", "09:00,10:00,11:00,12:00,13:00,14:00,15:00,16:00,17:00,18:00,19:00,20:00,21:00,22:00").split(",") if x.strip()]

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


# ===== 活动相关函数 =====
def _list_activities():
    """获取所有活动信息"""
    try:
        rows = base.list_rows(ACTIVITY_TABLE_NAME)
        return rows or []
    except Exception as e:
        print(f"Error listing activities: {e}")
        return []


def _get_activity_by_id(activity_id):
    """根据ID获取活动详情"""
    activities = _list_activities()
    for activity in activities:
        if activity.get('_id') == activity_id or str(activity.get('_id')) == str(activity_id):
            return activity
    return None


def _get_activity_details(activity):
    """提取活动的关键信息"""
    if not activity:
        return None
    return {
        'id': activity.get('_id'),
        'date': activity.get(ACTIVITY_COL_DATE, ''),
        'time': activity.get(ACTIVITY_COL_TIME, ''),
        'speakers': activity.get(ACTIVITY_COL_SPEAKERS, ''),
        'topic': activity.get(ACTIVITY_COL_TOPIC, ''),
        'classroom': activity.get(ACTIVITY_COL_CLASSROOM, ''),
        'videourl': activity.get(ACTIVITY_COL_VIDEOURL, ''),
        'creator_student_id': activity.get(ACTIVITY_COL_CREATOR_STUDENT_ID, ''),
    }


# ===== 报名相关函数 =====
def _list_signups():
    """获取所有报名记录"""
    try:
        rows = base.list_rows(SIGNUP_TABLE_NAME)
        return rows or []
    except Exception as e:
        print(f"Error listing signups: {e}")
        return []


def _count_signups_by_activity(activity_id, role=None):
    """统计某个活动的报名人数"""
    signups = _list_signups()
    count = 0
    for signup in signups:
        if str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')) == str(activity_id):
            if role is None or str(signup.get(SIGNUP_COL_ROLE, '')) == role:
                count += 1
    return count


def _calculate_expected_attendance(activity_id):
    """计算拟参加人数 = 分享者数 + 旁听者数 + 3名评议员"""
    activity = _get_activity_by_id(activity_id)
    if not activity:
        return 0
    
    # 分享者数（按逗号分割）
    speakers_str = str(activity.get(ACTIVITY_COL_SPEAKERS, '')).strip()
    speakers_count = len([s.strip() for s in speakers_str.split(',') if s.strip()]) if speakers_str else 0
    
    # 旁听者数
    listener_count = _count_signups_by_activity(activity_id, '旁听')
    
    # 评议员固定3人
    reviewer_count = REVIEWER_LIMIT
    
    return speakers_count + listener_count + reviewer_count


def _get_signup_stats(activity_id):
    """获取某个活动的报名统计"""
    reviewer_count = _count_signups_by_activity(activity_id, '评议员')
    listener_count = _count_signups_by_activity(activity_id, '旁听')
    expected_attendance = _calculate_expected_attendance(activity_id)
    
    return {
        'reviewers': reviewer_count,
        'listeners': listener_count,
        'expected_attendance': expected_attendance,
        'reviewer_full': reviewer_count >= REVIEWER_LIMIT,
    }


# ===== 统计和预警函数 =====
def _detect_inactive_members():
    """检测消亡的兴趣组（无活动记录）"""
    activities = _list_activities()
    speakers_set = set()
    for activity in activities:
        speakers_str = str(activity.get(ACTIVITY_COL_SPEAKERS, '')).strip()
        speakers = [s.strip() for s in speakers_str.split(',') if s.strip()]
        speakers_set.update(speakers)
    return {
        'total_active_speakers': len(speakers_set),
        'message': f'当前有 {len(speakers_set)} 个活跃的分享者/兴趣组'
    }


def _detect_boundary_violations():
    """检测接近超出边界的社员（过度参与导致可能违规）"""
    signups = _list_signups()
    member_participation = Counter()
    
    for signup in signups:
        name = str(signup.get(SIGNUP_COL_NAME, '')).strip()
        if name:
            member_participation[name] += 1
    
    # 设定阈值：超过10次报名的为预警对象
    warning_threshold = 10
    violations = {name: count for name, count in member_participation.items() if count > warning_threshold}
    
    return {
        'warning_threshold': warning_threshold,
        'potential_violations': violations,
        'count': len(violations),
    }


# ===== Flask 路由 =====
@app.get("/")
def index():
    """主页"""
    return render_template("index.html", time_slots=TIME_SLOTS)


@app.get("/organizer")
def organizer():
    """分享者管理页面"""
    return render_template("organizer.html")


@app.get("/healthz")
def healthz():
    return jsonify({"ok": True}), 200


@app.get("/api/activities")
def api_activities():
    """获取所有活动列表和统计信息"""
    activities = _list_activities()
    result = []
    
    for activity in activities:
        activity_id = activity.get('_id')
        details = _get_activity_details(activity)
        stats = _get_signup_stats(activity_id)
        result.append({
            **details,
            **stats,
        })
    
    return jsonify({
        "ok": True,
        "activities": result,
    })


@app.get("/api/activity/<activity_id>")
def api_activity_detail(activity_id):
    """获取单个活动的详细信息"""
    activity = _get_activity_by_id(activity_id)
    if not activity:
        return jsonify({"ok": False, "message": "活动不存在"}), 404
    
    details = _get_activity_details(activity)
    stats = _get_signup_stats(activity_id)
    
    return jsonify({
        "ok": True,
        "activity": {**details, **stats},
    })


@app.post("/api/signup")
def api_signup():
    """提交评议员或旁听报名"""
    data = request.get_json(silent=True) or {}
    
    name = str(data.get("name", "")).strip()
    student_id = str(data.get("student_id", "")).strip()
    activity_id = str(data.get("activity_id", "")).strip()
    role = str(data.get("role", "")).strip()  # '评议员' 或 '旁听'
    phone = str(data.get("phone", "")).strip()
    
    # 校验基本字段
    if not name or not student_id or not activity_id or not role:
        return jsonify({"ok": False, "message": "请完整填写姓名、学号、活动和角色"}), 400
    
    if role not in ['评议员', '旁听']:
        return jsonify({"ok": False, "message": "角色必须为'评议员'或'旁听'"}), 400
    
    # 校验活动是否存在
    activity = _get_activity_by_id(activity_id)
    if not activity:
        return jsonify({"ok": False, "message": "活动不存在"}), 404
    
    with submit_lock:
        signups = _list_signups()
        
        # 检检查评议员是否已满
        if role == '评议员':
            reviewer_count = _count_signups_by_activity(activity_id, '评议员')
            if reviewer_count >= REVIEWER_LIMIT:
                return jsonify({"ok": False, "message": f"评议员已满 {REVIEWER_LIMIT} 人，无法报名"}), 409
        
        # 检查学号是否已报名过该活动
        for signup in signups:
            if str(signup.get(SIGNUP_COL_STUDENT_ID, "")).strip() == student_id:
                if str(signup.get(SIGNUP_COL_ACTIVITY_ID, "")) == activity_id:
                    return jsonify({"ok": False, "message": "您已经报名过该活动，不能重复提交"}), 409
        
        # 添加新报名记录
        row_data = {
            SIGNUP_COL_NAME: name,
            SIGNUP_COL_STUDENT_ID: student_id,
            SIGNUP_COL_ACTIVITY_ID: activity_id,
            SIGNUP_COL_ROLE: role,
            SIGNUP_COL_PHONE: phone,
        }
        
        try:
            base.append_row(SIGNUP_TABLE_NAME, row_data)
        except Exception as e:
            return jsonify({"ok": False, "message": f"报名失败: {str(e)}"}), 500
    
    return jsonify({"ok": True, "message": f"{role}报名成功"})


@app.get("/api/stats")
def api_stats():
    """获取全局统计信息和预警"""
    inactive = _detect_inactive_members()
    violations = _detect_boundary_violations()
    
    return jsonify({
        "ok": True,
        "inactive_groups": inactive,
        "boundary_violations": violations,
    })


# ===== 分享者管理 API =====
@app.get("/api/my-activities/<student_id>")
def api_my_activities(student_id):
    """获取某个分享者的活动列表"""
    student_id = str(student_id).strip()
    if not student_id:
        return jsonify({"ok": False, "message": "学号不能为空"}), 400
    
    activities = _list_activities()
    my_activities = []
    
    for activity in activities:
        creator_id = str(activity.get(ACTIVITY_COL_CREATOR_STUDENT_ID, "")).strip()
        if creator_id == student_id:
            activity_id = activity.get('_id')
            details = _get_activity_details(activity)
            stats = _get_signup_stats(activity_id)
            my_activities.append({
                **details,
                **stats,
            })
    
    return jsonify({
        "ok": True,
        "activities": my_activities,
    })


@app.post("/api/activity")
def api_create_activity():
    """创建新活动（分享者）"""
    data = request.get_json(silent=True) or {}
    
    # 验证必填字段
    date = str(data.get("date", "")).strip()
    time = str(data.get("time", "")).strip()
    speakers = str(data.get("speakers", "")).strip()
    topic = str(data.get("topic", "")).strip()
    creator_student_id = str(data.get("creator_student_id", "")).strip()
    classroom = str(data.get("classroom", "")).strip()
    videourl = str(data.get("videourl", "")).strip()
    
    if not date or not time or not speakers or not topic or not creator_student_id:
        return jsonify({
            "ok": False, 
            "message": "请完整填写日期、时间、分享者、主题和学号"
        }), 400
    
    # 创建活动记录
    row_data = {
        ACTIVITY_COL_DATE: date,
        ACTIVITY_COL_TIME: time,
        ACTIVITY_COL_SPEAKERS: speakers,
        ACTIVITY_COL_TOPIC: topic,
        ACTIVITY_COL_CREATOR_STUDENT_ID: creator_student_id,
        ACTIVITY_COL_CLASSROOM: classroom if classroom else None,
        ACTIVITY_COL_VIDEOURL: videourl if videourl else None,
    }
    
    try:
        base.append_row(ACTIVITY_TABLE_NAME, row_data)
        return jsonify({"ok": True, "message": "活动创建成功"}), 201
    except Exception as e:
        return jsonify({"ok": False, "message": f"创建失败: {str(e)}"}), 500


@app.put("/api/activity/<activity_id>")
def api_update_activity(activity_id):
    """编辑活动（仅限创建者）"""
    activity_id = str(activity_id).strip()
    activity = _get_activity_by_id(activity_id)
    
    if not activity:
        return jsonify({"ok": False, "message": "活动不存在"}), 404
    
    data = request.get_json(silent=True) or {}
    creator_student_id = str(data.get("creator_student_id", "")).strip()
    
    # 验证身份
    actual_creator = str(activity.get(ACTIVITY_COL_CREATOR_STUDENT_ID, "")).strip()
    if actual_creator != creator_student_id:
        return jsonify({
            "ok": False, 
            "message": "只有活动创建者才能编辑此活动"
        }), 403
    
    # 准备更新数据
    update_data = {}
    if "date" in data:
        update_data[ACTIVITY_COL_DATE] = str(data["date"]).strip()
    if "time" in data:
        update_data[ACTIVITY_COL_TIME] = str(data["time"]).strip()
    if "speakers" in data:
        update_data[ACTIVITY_COL_SPEAKERS] = str(data["speakers"]).strip()
    if "topic" in data:
        update_data[ACTIVITY_COL_TOPIC] = str(data["topic"]).strip()
    if "classroom" in data:
        update_data[ACTIVITY_COL_CLASSROOM] = str(data["classroom"]).strip() or None
    if "videourl" in data:
        update_data[ACTIVITY_COL_VIDEOURL] = str(data["videourl"]).strip() or None
    
    if not update_data:
        return jsonify({
            "ok": False, 
            "message": "没有可更新的数据"
        }), 400
    
    try:
        base.update_row(ACTIVITY_TABLE_NAME, activity.get('_id'), update_data)
        return jsonify({"ok": True, "message": "活动更新成功"})
    except Exception as e:
        return jsonify({"ok": False, "message": f"更新失败: {str(e)}"}), 500


@app.delete("/api/activity/<activity_id>")
def api_delete_activity(activity_id):
    """删除活动（仅限创建者，且无报名时）"""
    activity_id = str(activity_id).strip()
    activity = _get_activity_by_id(activity_id)
    
    if not activity:
        return jsonify({"ok": False, "message": "活动不存在"}), 404
    
    data = request.get_json(silent=True) or {}
    creator_student_id = str(data.get("creator_student_id", "")).strip()
    
    # 验证身份
    actual_creator = str(activity.get(ACTIVITY_COL_CREATOR_STUDENT_ID, "")).strip()
    if actual_creator != creator_student_id:
        return jsonify({
            "ok": False, 
            "message": "只有活动创建者才能删除此活动"
        }), 403
    
    # 检查是否有报名记录
    signup_count = _count_signups_by_activity(activity_id)
    if signup_count > 0:
        return jsonify({
            "ok": False, 
            "message": f"无法删除：已有 {signup_count} 人报名，请先清除报名记录"
        }), 409
    
    try:
        base.delete_row(ACTIVITY_TABLE_NAME, activity.get('_id'))
        return jsonify({"ok": True, "message": "活动删除成功"})
    except Exception as e:
        return jsonify({"ok": False, "message": f"删除失败: {str(e)}"}), 500


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "8080"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)

