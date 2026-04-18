"""
统计服务模块

封装各种统计和排行榜相关的业务逻辑
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta

from config import (
    ACTIVITY_COL_SPEAKERS, ACTIVITY_COL_DATE, ACTIVITY_COL_CREATOR_NAME, ACTIVITY_COL_TIME,
    ACTIVITY_COL_ON_TIME, ACTIVITY_COL_STATUS, ACTIVITY_COL_CLOSED_AT,
    SIGNUP_COL_ACTIVITY_ID,
    OUTPUT_RECORD_TABLE_NAME, OUTPUT_RECORD_COL_DATE, OUTPUT_RECORD_COL_TYPE, OUTPUT_RECORD_COL_NAME,
    BOUNDARY_LOOKBACK_DAYS, ACTIVITY_CLOSE_GRACE_MINUTES
)
from models import db
from services.activity import (
    list_activities, get_activity_by_id, activity_is_closed
)
from services.signup import (
    list_signups, get_signup_name, get_signup_role
)
from services.cac_admin import is_cac_user
from services.profile import list_user_profiles
from utils.cache import cached_build


# ===== 评议质量统计 =====

def build_review_quality_stats():
    """构建评议质量统计数据"""
    def build_stats():
        from services.rating import list_review_ratings, serialize_rating

        per_signup = defaultdict(lambda: {'weighted_score': 0.0, 'total_weight': 0.0, 'rating_count': 0, 'ratings': []})
        per_reviewer = defaultdict(lambda: {'weighted_score': 0.0, 'total_weight': 0.0, 'rating_count': 0, 'review_count': 0})

        for rating in list_review_ratings():
            item = serialize_rating(rating)
            signup_id = item['signup_id']
            if not signup_id:
                continue
            per_signup[signup_id]['weighted_score'] += item['score'] * item['weight']
            per_signup[signup_id]['total_weight'] += item['weight']
            per_signup[signup_id]['rating_count'] += 1
            per_signup[signup_id]['ratings'].append(item)

        for signup in list_signups():
            if get_signup_role(signup) != '评议员':
                continue
            signup_id = str(signup.get('_id'))
            signup_name = get_signup_name(signup)
            stats = per_signup[signup_id]
            if stats['total_weight'] <= 0:
                continue
            per_reviewer[signup_name]['weighted_score'] += stats['weighted_score']
            per_reviewer[signup_name]['total_weight'] += stats['total_weight']
            per_reviewer[signup_name]['rating_count'] += stats['rating_count']
            per_reviewer[signup_name]['review_count'] += 1

        ranking = []
        for reviewer_name, stats in per_reviewer.items():
            ranking.append({
                'name': reviewer_name,
                'score': round(stats['weighted_score'] / stats['total_weight'], 2) if stats['total_weight'] > 0 else 0,
                'rating_count': stats['rating_count'],
                'review_count': stats['review_count'],
            })

        ranking.sort(key=lambda item: (-item['score'], -item['rating_count'], item['name']))
        return dict(per_signup), ranking

    return cached_build('review_quality_stats', 300, build_stats)


# ===== 排行榜 =====

def build_share_leaderboard():
    """构建分享排行榜"""
    counter = Counter()
    for activity in list_activities():
        for speaker in _split_names(activity.get(ACTIVITY_COL_SPEAKERS, '')):
            if is_cac_user(speaker):
                continue
            counter[speaker] += 1
    return [{'name': name, 'count': count} for name, count in counter.most_common()]


def build_participation_leaderboard():
    """构建参与排行榜"""
    counter = Counter()
    for signup in list_signups():
        if get_signup_role(signup) in {'评议员', '旁听'}:
            signup_name = get_signup_name(signup)
            if is_cac_user(signup_name):
                continue
            counter[signup_name] += 1
    return [{'name': name, 'count': count} for name, count in counter.most_common()]


def build_punctuality_leaderboard():
    """构建准时率排行榜"""
    stats = defaultdict(lambda: {'on_time': 0, 'closed': 0})
    for activity in list_activities():
        if not activity_is_closed(activity):
            continue
        creator_name = str(activity.get(ACTIVITY_COL_CREATOR_NAME, '')).strip()
        if not creator_name:
            continue
        if is_cac_user(creator_name):
            continue
        stats[creator_name]['closed'] += 1
        if _compute_activity_on_time(activity):
            stats[creator_name]['on_time'] += 1

    ranking = []
    for name, item in stats.items():
        closed = item['closed']
        ranking.append({
            'name': name,
            'closed_count': closed,
            'on_time_count': item['on_time'],
            'on_time_rate': round(item['on_time'] / closed, 4) if closed else 0,
        })
    ranking.sort(key=lambda item: (-item['on_time_rate'], -item['closed_count'], item['name']))
    return ranking


# ===== 边界预警 =====

def build_boundary_stats():
    """构建边界预警统计"""
    known_members = set(_collect_known_member_names())
    known_members = {name for name in known_members if not is_cac_user(name)}
    output_counter = _build_output_counts(lookback_days=BOUNDARY_LOOKBACK_DAYS)

    non_compliant = sorted(name for name in known_members if output_counter.get(name, 0) < 1)
    return {
        'lookback_days': BOUNDARY_LOOKBACK_DAYS,
        'tracked_member_count': len(known_members),
        'non_compliant_count': len(non_compliant),
        'non_compliant_names': non_compliant,
        'output_counts': dict(output_counter),
    }


def _build_output_counts(lookback_days=BOUNDARY_LOOKBACK_DAYS):
    """构建产出统计"""
    output_counter = Counter()

    for activity in list_activities():
        if _within_lookback(activity.get(ACTIVITY_COL_DATE, ''), lookback_days=lookback_days):
            for speaker in _split_names(activity.get(ACTIVITY_COL_SPEAKERS, '')):
                output_counter[speaker] += 1

    for signup in list_signups():
        if get_signup_role(signup) != '评议员':
            continue
        activity = get_activity_by_id(str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip())
        if activity and _within_lookback(activity.get(ACTIVITY_COL_DATE, ''), lookback_days=lookback_days):
            output_counter[get_signup_name(signup)] += 1

    for record in db.list_rows(OUTPUT_RECORD_TABLE_NAME):
        if not _within_lookback(record.get(OUTPUT_RECORD_COL_DATE, ''), lookback_days=lookback_days):
            continue
        record_type = str(record.get(OUTPUT_RECORD_COL_TYPE, '')).strip()
        if record_type in {'分享', '评议', 'CAC有约'}:
            name = str(record.get(OUTPUT_RECORD_COL_NAME, '')).strip()
            if name:
                output_counter[name] += 1

    return output_counter


# ===== 辅助函数 =====

def _split_names(names_str):
    """分割名字列表"""
    if not names_str:
        return []
    result = []
    for part in str(names_str).replace('，', ',').split(','):
        name = part.strip()
        if name:
            result.append(name)
    return result


def _within_lookback(date_value, lookback_days=BOUNDARY_LOOKBACK_DAYS):
    """检查日期是否在回溯范围内"""
    target = _parse_date(date_value)
    if not target:
        return False
    return target.date() >= (datetime.now().date() - timedelta(days=lookback_days))


def _parse_date(date_value):
    """解析日期"""
    if not date_value:
        return None
    try:
        return datetime.strptime(str(date_value).strip(), '%Y-%m-%d')
    except (ValueError, TypeError):
        try:
            return datetime.strptime(str(date_value).strip(), '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return None


def _compute_activity_on_time(activity):
    """计算活动是否准时结项（含宽限期）"""
    if not activity:
        return False

    # 检查是否已结项
    on_time_flag = str(activity.get(ACTIVITY_COL_ON_TIME, '')).strip().lower()
    if on_time_flag in ('true', '1', 'yes'):
        return True
    status = str(activity.get(ACTIVITY_COL_STATUS, '')).strip()
    if status == '已结项':
        # 已结项但没有 on_time 标记，尝试用时间计算
        pass
    elif status != '已结项':
        return False  # 未结项的活动谈不上准时

    # 用结项时间和活动结束时间对比
    closed_at = _parse_datetime(activity.get(ACTIVITY_COL_CLOSED_AT, ''))
    end_at = _get_activity_end_datetime(activity)
    if not closed_at or not end_at:
        return False
    return closed_at <= end_at + timedelta(minutes=ACTIVITY_CLOSE_GRACE_MINUTES)


def _parse_datetime(dt_str):
    """解析日期时间"""
    if not dt_str:
        return None
    text = str(dt_str).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M'):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _get_activity_end_datetime(activity):
    """获取活动结束时间"""
    if not activity:
        return None
    date_str = str(activity.get(ACTIVITY_COL_DATE, '')).strip()
    time_str = str(activity.get(ACTIVITY_COL_TIME, '')).strip()
    if not date_str or not time_str:
        return None
    try:
        time_parts = time_str.split('-')
        if len(time_parts) >= 2:
            end_time = time_parts[-1].strip()
            return datetime.strptime(f"{date_str} {end_time}", "%Y-%m-%d %H:%M")
    except (ValueError, IndexError):
        pass
    return None


def _collect_known_member_names():
    """收集已知成员名字"""
    names = set()
    for profile in list_user_profiles():
        name = str(profile.get('姓名', '')).strip()
        if name:
            names.add(name)
    return names
