import json

import pytest

from app.legacy import load_from_json, run_import
from app.models import Activity, Contribution, Group, Invite, ReviewRating, Room, RoomSlot, Signup, User, UserRole
from app.seed import seed

LEGACY = {
    "用户档案": [
        {"_id": "p1", "姓名": "张三", "邮箱": "ZS@example.edu", "首次使用时间": "2026-02-01 10:00:00"},
        {"_id": "p2", "姓名": "李四", "邮箱": "ls@example.edu"},
    ],
    "CAC管理员": [{"_id": "a1", "姓名": "张三"}],
    "兴趣组": [
        {
            "_id": "g1",
            "组名": "系统组",
            "组长": "张三",
            "主题目标": "读论文",
            "时间边界": "本学期",
            "执行方案": "每周一次",
            "状态": "活跃",
        }
    ],
    "兴趣组成员": [
        {"_id": "m1", "兴趣组ID": "g1", "成员姓名": "张三", "成员身份": "组长"},
        {"_id": "m2", "兴趣组ID": "g1", "成员姓名": "李四", "成员身份": "组员"},
    ],
    "分享会活动": [
        {
            "_id": "act1",
            "活动日期": "2026-03-05",
            "活动时间": "14:00-15:30",
            "分享者": "张三、王五",
            "活动主题": "Raft 共识算法",
            "活动教室": "CAC-101",
            "组织者姓名": "张三",
            "组织者邮箱": "zs@example.edu",
            "活动状态": "已结项",
            "结项时间": "2026-03-05 17:00:00",
            "准时结项": "true",
            "结项人": "张三",
            "活动类型": "normal",
            "所属兴趣组ID": "g1",
        },
        {
            "_id": "act2",
            "活动日期": "2026-03-08",
            "活动时间": "14:00-15:00",
            "分享者": "李四",
            "活动主题": "CAC有约",
            "组织者姓名": "李四",
            "活动类型": "cac有约",
        },
        {"_id": "bad", "活动日期": "", "活动时间": "whenever", "活动主题": "Broken", "组织者姓名": "x"},
    ],
    "分享会报名": [
        {
            "_id": "s1",
            "姓名": "李四",
            "关联活动": "act1",
            "角色": "评议员",
            "联系电话": "138",
            "邮箱": "ls@example.edu",
            "评议内容": "选主过程",
            "评议语雀链接": "https://yuque.com/x",
            "评议提交时间": "2026-03-06 20:00:00",
        },
        {"_id": "s2", "姓名": "赵六", "关联活动": "act1", "角色": "旁听"},
        {"_id": "s3", "姓名": "赵六", "关联活动": "act1", "角色": "旁听"},
        {"_id": "s4", "姓名": "赵六", "关联活动": "missing", "角色": "旁听"},
    ],
    "评议评分": [
        {"_id": "r1", "评议报名ID": "s1", "评分人姓名": "赵六", "评分": "9", "权重": "10"},
        {"_id": "r2", "评议报名ID": "s1", "评分人姓名": "李四", "评分": "10", "权重": "1"},
    ],
    "评议邀请": [
        {
            "_id": "i1",
            "活动ID": "act1",
            "邀请人": "张三",
            "被邀请人": "李四",
            "状态": "已接受",
            "邀请来源": "分享者指定",
        }
    ],
    "输出活动记录": [{"_id": "o1", "姓名": "王五", "输出类型": "CAC有约", "输出日期": "2026-03-10"}],
    "CAC教室时间槽": [
        {"_id": "t1", "教室": "CAC-101", "日期": "2026-03-12", "时间段": "14:00-14:30"},
        {"_id": "t2", "教室": "CAC-101", "日期": "2026-03-12", "时间段": "14:30-15:00"},
        {"_id": "t3", "教室": "CAC-102", "日期": "2026-03-12", "时间段": "16:00-16:30"},
    ],
}


def test_legacy_import_maps_everything(db, tmp_path):
    path = tmp_path / "dump.json"
    path.write_text(json.dumps(LEGACY, ensure_ascii=False), encoding="utf-8")
    report = run_import(db, load_from_json(str(path)))

    users = {u.name: u for u in db.query(User).all()}
    assert set(users) == {"张三", "李四", "王五", "赵六", "x"}
    assert users["张三"].role == UserRole.ADMIN and users["张三"].email == "zs@example.edu"
    assert users["张三"].password_hash is None  # must claim the account
    assert users["李四"].phone == "138"

    raft = db.query(Activity).filter_by(title="Raft 共识算法").one()
    assert raft.room.name == "CAC-101" and raft.group.name == "系统组"
    assert [s.user.name for s in raft.speakers] == ["张三", "王五"]
    assert raft.closed_on_time is True and raft.closed_by_id == users["张三"].id
    assert str(raft.start_time) == "14:00:00" and str(raft.end_time) == "15:30:00"
    assert db.query(Activity).filter_by(title="CAC有约").one().kind == "meetup"

    assert db.query(Signup).count() == 2  # duplicate and orphan skipped
    rating = db.query(ReviewRating).one()  # self-rating skipped
    assert rating.rater.name == "赵六" and rating.weight == 10
    assert db.query(Invite).one().status == "accepted"
    assert db.query(Contribution).one().kind == "meetup"
    assert {g.name for g in db.query(Group).all()} == {"系统组"}
    slots = db.query(RoomSlot).order_by(RoomSlot.start_time).all()
    assert [(s.room.name, str(s.start_time), str(s.end_time)) for s in slots] == [
        ("CAC-101", "14:00:00", "15:00:00"),  # adjacent half-hours merged
        ("CAC-102", "16:00:00", "16:30:00"),
    ]
    assert db.query(Room).count() == 2
    assert report.skipped["activities (missing date, time or organiser)"] == 1
    assert "Imported:" in report.summary()


def test_legacy_import_refuses_non_empty_database(db, make_user):
    make_user()
    with pytest.raises(RuntimeError):
        run_import(db, LEGACY)


def test_flat_json_export_format(tmp_path):
    rows = [{"table_name": "用户档案", "row_id": "p1", "row_data": json.dumps({"姓名": "张三"}, ensure_ascii=False)}]
    path = tmp_path / "rows.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    assert load_from_json(str(path)) == {"用户档案": [{"姓名": "张三", "_id": "p1"}]}


def test_demo_seed_produces_a_working_dataset(db, anon):
    seed(db)
    client = anon
    assert (
        client.post("/api/auth/login", json={"email": "admin@example.edu", "password": "password123"}).status_code
        == 200
    )
    page = client.get("/api/activities", params={"state": ["upcoming"]}).json()
    assert page["total"] >= 4
    dash = client.get("/api/admin/dashboard").json()
    assert dash["participation"]["tracked_count"] == 12
    boards = client.get("/api/stats/leaderboards").json()
    assert boards["sharing"] and boards["review_quality"]
    client.post("/api/auth/login", json={"email": "lin.yue@example.edu", "password": "password123"})
    me = client.get("/api/me/dashboard").json()
    assert any(t["kind"] == "pending_invite" for t in me["tasks"])
