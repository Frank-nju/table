"""Interest groups and their memberships."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.errors import BadRequest, Conflict, Forbidden, NotFound
from app.models import Activity, Group, GroupMembership, GroupRole, GroupStatus, User
from app.schemas import GroupDetail, GroupIn, GroupMemberOut, GroupOut, GroupUpdate, UserBrief
from app.services import activities as activity_service
from app.services import mail, users

MIN_MEMBERS = 2


def get(db: Session, group_id: int) -> Group:
    group = db.scalar(select(Group).where(Group.id == group_id).options(selectinload(Group.memberships)))
    if group is None:
        raise NotFound("Interest group not found.", code="group_not_found")
    return group


def leader_of(group: Group) -> User | None:
    return next((m.user for m in group.memberships if m.role == GroupRole.LEADER), None)


def membership(group: Group, user_id: int) -> GroupMembership | None:
    return next((m for m in group.memberships if m.user_id == user_id), None)


def to_out(group: Group, viewer: User | None) -> GroupOut:
    leader = leader_of(group)
    return GroupOut(
        id=group.id,
        name=group.name,
        goal=group.goal,
        time_boundary=group.time_boundary,
        plan=group.plan,
        description=group.description,
        status=group.status,
        created_at=group.created_at,
        leader=UserBrief(id=leader.id, name=leader.name) if leader else None,
        member_count=len(group.memberships),
        is_member=viewer is not None and membership(group, viewer.id) is not None,
    )


def to_detail(db: Session, group: Group, viewer: User | None) -> GroupDetail:
    recent = db.scalars(
        select(Activity)
        .where(Activity.group_id == group.id)
        .options(*activity_service.LOAD)
        .order_by(Activity.date.desc(), Activity.start_time.desc())
        .limit(10)
    ).all()
    members = sorted(group.memberships, key=lambda m: (m.role != GroupRole.LEADER, m.user.name.lower()))
    return GroupDetail(
        **to_out(group, viewer).model_dump(),
        members=[
            GroupMemberOut(user=UserBrief(id=m.user.id, name=m.user.name), role=m.role, joined_at=m.joined_at)
            for m in members
        ],
        recent_activities=[activity_service.to_out(a, viewer) for a in recent],
    )


def list_groups(db: Session, viewer: User | None, include_archived: bool = False) -> list[GroupOut]:
    stmt = select(Group).options(selectinload(Group.memberships)).order_by(Group.name)
    if not include_archived:
        stmt = stmt.where(Group.status == GroupStatus.ACTIVE)
    return [to_out(g, viewer) for g in db.scalars(stmt)]


def _require_leader(actor: User, group: Group) -> None:
    m = membership(group, actor.id)
    if not actor.is_admin and (m is None or m.role != GroupRole.LEADER):
        raise Forbidden("Only the group leader or an administrator can do this.", code="not_group_leader")


def _check_name(db: Session, name: str, exclude_id: int | None = None) -> None:
    existing = db.scalar(select(Group).where(func.lower(Group.name) == name.lower()))
    if existing is not None and existing.id != exclude_id:
        raise Conflict("A group with this name already exists.", code="group_name_taken")


def create(db: Session, actor: User, data: GroupIn) -> Group:
    _check_name(db, data.name)
    members = users.get_users(db, [m for m in data.member_ids if m != actor.id])
    if len(members) + 1 < MIN_MEMBERS:
        raise BadRequest(
            f"An interest group needs at least {MIN_MEMBERS} members, including you.", code="group_too_small"
        )
    group = Group(
        name=data.name,
        goal=data.goal,
        time_boundary=data.time_boundary,
        plan=data.plan,
        description=data.description,
    )
    group.memberships = [GroupMembership(user_id=actor.id, role=GroupRole.LEADER)] + [
        GroupMembership(user_id=u.id, role=GroupRole.MEMBER) for u in members
    ]
    db.add(group)
    db.commit()
    return get(db, group.id)


def update(db: Session, actor: User, group_id: int, data: GroupUpdate) -> Group:
    group = get(db, group_id)
    _require_leader(actor, group)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("name"):
        _check_name(db, changes["name"], exclude_id=group.id)
    for field, value in changes.items():
        if value is not None:
            setattr(group, field, value)
    db.commit()
    return get(db, group.id)


def join(db: Session, actor: User, group_id: int) -> Group:
    group = get(db, group_id)
    if group.status != GroupStatus.ACTIVE:
        raise BadRequest("This group is archived.", code="group_archived")
    if membership(group, actor.id):
        raise Conflict("You're already a member of this group.", code="already_member")
    group.memberships.append(GroupMembership(user_id=actor.id, role=GroupRole.MEMBER))
    mail.notify(db, leader_of(group), "group_member_joined", member=actor.name, group=group.name)
    db.commit()
    return get(db, group.id)


def leave(db: Session, actor: User, group_id: int) -> Group:
    group = get(db, group_id)
    m = membership(group, actor.id)
    if m is None:
        raise NotFound("You're not a member of this group.", code="not_member")
    if m.role == GroupRole.LEADER:
        raise BadRequest("Hand leadership to another member before leaving.", code="leader_cannot_leave")
    group.memberships.remove(m)
    db.commit()
    return get(db, group.id)


def remove_member(db: Session, actor: User, group_id: int, user_id: int) -> Group:
    group = get(db, group_id)
    _require_leader(actor, group)
    m = membership(group, user_id)
    if m is None:
        raise NotFound("That person isn't a member of this group.", code="not_member")
    if m.role == GroupRole.LEADER:
        raise BadRequest("Hand leadership to another member first.", code="leader_cannot_leave")
    group.memberships.remove(m)
    db.commit()
    return get(db, group.id)


def transfer(db: Session, actor: User, group_id: int, user_id: int) -> Group:
    group = get(db, group_id)
    _require_leader(actor, group)
    target = membership(group, user_id)
    if target is None:
        raise BadRequest("The new leader must already be a member of the group.", code="not_member")
    for m in group.memberships:
        m.role = GroupRole.LEADER if m.user_id == user_id else GroupRole.MEMBER
    db.commit()
    return get(db, group.id)


def groups_of(db: Session, user_id: int) -> list[tuple[Group, GroupRole]]:
    rows = db.execute(
        select(Group, GroupMembership.role)
        .join(GroupMembership)
        .where(GroupMembership.user_id == user_id)
        .order_by(Group.name)
    ).all()
    return [(g, r) for g, r in rows]
