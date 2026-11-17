"""Leaderboards, participation tracking, reports and personal dashboards."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.models import (
    Activity,
    ActivityKind,
    ActivitySpeaker,
    Contribution,
    Group,
    GroupStatus,
    Invite,
    InviteStatus,
    ReviewRating,
    Signup,
    SignupRole,
    User,
)
from app.scheduling import ActivityState, local_today
from app.schemas import (
    ActivityOut,
    AdminDashboard,
    ConflictGroup,
    ContributionOut,
    CountEntry,
    GroupHealth,
    HistoryEntry,
    Leaderboards,
    MeDashboard,
    MonthlyReport,
    MyGroup,
    MySignup,
    Overview,
    ParticipationWatch,
    PersonalMetrics,
    PublicProfile,
    PunctualityEntry,
    Recommendation,
    ReviewerWatchEntry,
    ReviewQualityEntry,
    Task,
    UserBrief,
)
from app.services import activities as activity_service
from app.services import groups as group_service
from app.services import invites as invite_service
from app.services import signups as signup_service

LEADERBOARD_SIZE = 20


def _brief(u: User) -> UserBrief:
    return UserBrief(id=u.id, name=u.name)


def tracked_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).where(User.is_active, User.participation_tracked).order_by(User.name)))


# ----- Raw aggregates -----


@dataclass
class Aggregates:
    """Everything the leaderboards and personal metrics need, computed in a handful of queries."""

    shares: Counter[int] = field(default_factory=Counter)
    participation: Counter[int] = field(default_factory=Counter)
    review_weighted: dict[int, float] = field(default_factory=dict)
    review_weight: dict[int, float] = field(default_factory=dict)
    review_ratings: Counter[int] = field(default_factory=Counter)
    reviews_rated: Counter[int] = field(default_factory=Counter)
    closed: Counter[int] = field(default_factory=Counter)
    on_time: Counter[int] = field(default_factory=Counter)

    def review_score(self, user_id: int) -> float | None:
        w = self.review_weight.get(user_id, 0)
        return round(self.review_weighted[user_id] / w, 2) if w else None

    def on_time_rate(self, user_id: int) -> float | None:
        closed = self.closed.get(user_id, 0)
        return round(self.on_time[user_id] / closed, 4) if closed else None


def aggregates(db: Session, since: date | None = None) -> Aggregates:
    today = local_today()
    agg = Aggregates()
    window = [Activity.date <= today] + ([Activity.date >= since] if since else [])

    for user_id, n in db.execute(
        select(ActivitySpeaker.user_id, func.count()).join(Activity).where(*window).group_by(ActivitySpeaker.user_id)
    ):
        agg.shares[user_id] = n
    for user_id, n in db.execute(
        select(Signup.user_id, func.count()).join(Activity).where(*window).group_by(Signup.user_id)
    ):
        agg.participation[user_id] = n

    per_review: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for signup_id, reviewer_id, score, weight in db.execute(
        select(ReviewRating.signup_id, Signup.user_id, ReviewRating.score, ReviewRating.weight)
        .join(Signup, Signup.id == ReviewRating.signup_id)
        .join(Activity, Activity.id == Signup.activity_id)
        .where(*window)
    ):
        per_review[signup_id].append((score, weight))
        agg.review_weighted[reviewer_id] = agg.review_weighted.get(reviewer_id, 0) + score * weight
        agg.review_weight[reviewer_id] = agg.review_weight.get(reviewer_id, 0) + weight
        agg.review_ratings[reviewer_id] += 1
    for (reviewer_id,) in db.execute(select(Signup.user_id).where(Signup.id.in_(list(per_review.keys())))):
        agg.reviews_rated[reviewer_id] += 1

    for organizer_id, on_time in db.execute(
        select(Activity.organizer_id, Activity.closed_on_time).where(Activity.closed_at.is_not(None), *window)
    ):
        agg.closed[organizer_id] += 1
        if on_time:
            agg.on_time[organizer_id] += 1
    return agg


def outputs_by_user(db: Session, lookback_days: int | None = None) -> Counter[int]:
    """Number of 'outputs' (talks, reviews, meetups, recorded contributions) per user in the window."""
    days = lookback_days if lookback_days is not None else get_settings().participation_lookback_days
    today = local_today()
    start = today - timedelta(days=days)
    counter: Counter[int] = Counter()
    for (user_id,) in db.execute(
        select(ActivitySpeaker.user_id).join(Activity).where(Activity.date.between(start, today))
    ):
        counter[user_id] += 1
    for (user_id,) in db.execute(
        select(Signup.user_id)
        .join(Activity)
        .where(
            Activity.date.between(start, today),
            (Signup.role == SignupRole.REVIEWER) | (Activity.kind == ActivityKind.MEETUP),
        )
    ):
        counter[user_id] += 1
    for (user_id,) in db.execute(select(Contribution.user_id).where(Contribution.date.between(start, today))):
        counter[user_id] += 1
    return counter


def participation_watch(db: Session) -> ParticipationWatch:
    settings = get_settings()
    days = settings.participation_lookback_days
    outputs = outputs_by_user(db, days)
    tracked = tracked_users(db)
    grace_cutoff = local_today() - timedelta(days=days)
    # New members get one full window before they can be flagged.
    inactive = [
        u for u in tracked if outputs.get(u.id, 0) == 0 and u.created_at.astimezone(settings.tz).date() <= grace_cutoff
    ]
    return ParticipationWatch(lookback_days=days, tracked_count=len(tracked), inactive=[_brief(u) for u in inactive])


# ----- Leaderboards -----


def leaderboards(db: Session, since: date | None = None) -> Leaderboards:
    agg = aggregates(db, since)
    users = {u.id: u for u in tracked_users(db)}

    def counted(counter: Counter[int]) -> list[CountEntry]:
        rows = [(users[uid], n) for uid, n in counter.items() if uid in users and n > 0]
        rows.sort(key=lambda r: (-r[1], r[0].name.lower()))
        return [CountEntry(user=_brief(u), count=n) for u, n in rows[:LEADERBOARD_SIZE]]

    quality = [
        ReviewQualityEntry(
            user=_brief(users[uid]),
            score=agg.review_score(uid) or 0,
            rating_count=agg.review_ratings[uid],
            review_count=agg.reviews_rated[uid],
        )
        for uid in agg.review_weight
        if uid in users
    ]
    quality.sort(key=lambda e: (-e.score, -e.rating_count, e.user.name.lower()))

    punctuality = [
        PunctualityEntry(
            user=_brief(users[uid]),
            closed_count=agg.closed[uid],
            on_time_count=agg.on_time[uid],
            on_time_rate=agg.on_time_rate(uid) or 0,
        )
        for uid in agg.closed
        if uid in users
    ]
    punctuality.sort(key=lambda e: (-e.on_time_rate, -e.closed_count, e.user.name.lower()))

    return Leaderboards(
        sharing=counted(agg.shares),
        participation=counted(agg.participation),
        review_quality=quality[:LEADERBOARD_SIZE],
        punctuality=punctuality[:LEADERBOARD_SIZE],
        since=since,
    )


def overview(db: Session) -> Overview:
    today = local_today()
    upcoming = db.scalar(
        select(func.count()).select_from(Activity).where(activity_service.state_filter([ActivityState.UPCOMING]))
    )
    this_month = db.scalar(
        select(func.count())
        .select_from(Activity)
        .where(extract("year", Activity.date) == today.year, extract("month", Activity.date) == today.month)
    )
    members = db.scalar(select(func.count()).select_from(User).where(User.is_active))
    groups = db.scalar(select(func.count()).select_from(Group).where(Group.status == GroupStatus.ACTIVE))
    return Overview(
        upcoming_count=upcoming or 0, activities_this_month=this_month or 0, members=members or 0, groups=groups or 0
    )


# ----- Admin reports -----


def monthly_report(db: Session, year: int, month: int) -> MonthlyReport:
    start = date(year, month, 1)
    end = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    acts = list(
        db.scalars(select(Activity).where(Activity.date.between(start, end)).options(selectinload(Activity.signups)))
    )
    signups = [s for a in acts for s in a.signups]
    contributions = db.scalar(select(func.count()).where(Contribution.date.between(start, end))) or 0
    closed = [a for a in acts if a.is_closed]
    awaiting = [a for a in acts if activity_service.state_of(a) == ActivityState.AWAITING_CLOSE]
    on_time = [a for a in closed if a.closed_on_time]
    return MonthlyReport(
        month=f"{year:04d}-{month:02d}",
        activity_count=len(acts),
        regular_count=sum(1 for a in acts if a.kind == ActivityKind.REGULAR),
        meetup_count=sum(1 for a in acts if a.kind == ActivityKind.MEETUP),
        signup_count=len(signups),
        contribution_count=contributions,
        active_organizers=len({a.organizer_id for a in acts}),
        active_participants=len({s.user_id for s in signups}),
        closed_count=len(closed),
        awaiting_close_count=len(awaiting),
        on_time_close_rate=round(len(on_time) / len(closed), 4) if closed else None,
    )


def group_health(db: Session, lookback_days: int = 30) -> list[GroupHealth]:
    since = local_today() - timedelta(days=lookback_days)
    outputs = outputs_by_user(db, lookback_days)
    report = []
    for group in db.scalars(
        select(Group).where(Group.status == GroupStatus.ACTIVE).options(selectinload(Group.memberships))
    ):
        recent = list(db.scalars(select(Activity).where(Activity.group_id == group.id, Activity.date >= since)))
        awaiting = sum(1 for a in recent if activity_service.state_of(a) == ActivityState.AWAITING_CLOSE)
        active_members = sum(1 for m in group.memberships if outputs.get(m.user_id, 0) > 0)
        score = 35 + min(30, len(recent) * 15) + min(25, active_members * 5) - awaiting * 12
        score = max(0, min(100, score))
        status = "healthy" if score >= 75 else "at_risk" if score >= 45 else "inactive"
        leader = group_service.leader_of(group)
        report.append(
            GroupHealth(
                group=UserBrief(id=group.id, name=group.name),
                leader=_brief(leader) if leader else None,
                member_count=len(group.memberships),
                active_member_count=active_members,
                recent_activity_count=len(recent),
                awaiting_close_count=awaiting,
                score=score,
                status=status,  # type: ignore[arg-type]
            )
        )
    report.sort(key=lambda g: (g.score, g.group.name.lower()))
    return report


def reviewer_watch(db: Session) -> list[ReviewerWatchEntry]:
    agg = aggregates(db)
    missing: Counter[int] = Counter()
    reviews: Counter[int] = Counter()
    for user_id, doc_url, closed_at, kind in db.execute(
        select(Signup.user_id, Signup.review_doc_url, Activity.closed_at, Activity.kind)
        .join(Activity)
        .where(Signup.role == SignupRole.REVIEWER)
    ):
        reviews[user_id] += 1
        if closed_at is not None and not doc_url and kind == ActivityKind.REGULAR:
            missing[user_id] += 1
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_(list(reviews.keys())), User.is_active))}
    entries = []
    for uid, user in users.items():
        score = agg.review_score(uid)
        ratings = agg.review_ratings[uid]
        if missing[uid]:
            status = "missing_docs"
        elif score is not None and ratings >= 2 and score < 7:
            status = "low_score"
        elif ratings == 0:
            status = "needs_feedback"
        else:
            status = "ok"
        entries.append(
            ReviewerWatchEntry(
                user=_brief(user),
                score=score,
                rating_count=ratings,
                review_count=reviews[uid],
                missing_docs=missing[uid],
                status=status,  # type: ignore[arg-type]
            )
        )
    order = {"missing_docs": 0, "low_score": 1, "needs_feedback": 2, "ok": 3}
    entries.sort(key=lambda e: (order[e.status], -e.missing_docs, e.score or 0, e.user.name.lower()))
    return entries


def conflicts(db: Session) -> list[ConflictGroup]:
    """Upcoming activities that overlap in time on the same day, grouped into clusters."""
    acts = list(
        db.scalars(
            select(Activity)
            .where(Activity.date >= local_today(), Activity.closed_at.is_(None))
            .options(*activity_service.LOAD)
            .order_by(Activity.date, Activity.start_time)
        )
    )
    by_day: dict[date, list[Activity]] = defaultdict(list)
    for a in acts:
        by_day[a.date].append(a)
    result = []
    for d, day_acts in sorted(by_day.items()):
        cluster: list[Activity] = []
        cluster_end = None
        for a in day_acts:  # sorted by start time: sweep-line clustering
            if cluster and cluster_end is not None and a.start_time < cluster_end:
                cluster.append(a)
                cluster_end = max(cluster_end, a.end_time)
            else:
                if len(cluster) > 1:
                    result.append(ConflictGroup(date=d, activities=[activity_service.to_out(x) for x in cluster]))
                cluster, cluster_end = [a], a.end_time
        if len(cluster) > 1:
            result.append(ConflictGroup(date=d, activities=[activity_service.to_out(x) for x in cluster]))
    return result


def admin_dashboard(db: Session, year: int, month: int) -> AdminDashboard:
    return AdminDashboard(
        monthly=monthly_report(db, year, month),
        participation=participation_watch(db),
        groups=group_health(db),
        reviewers=reviewer_watch(db),
        conflicts=conflicts(db),
    )


# ----- Personal views -----


def _rank(entries: list, user_id: int) -> int | None:  # type: ignore[type-arg]
    return next((i for i, e in enumerate(entries, start=1) if e.user.id == user_id), None)


def personal_metrics(db: Session, user: User, boards: Leaderboards | None = None) -> PersonalMetrics:
    settings = get_settings()
    agg = aggregates(db)
    boards = boards or leaderboards(db)
    outputs = outputs_by_user(db).get(user.id, 0)
    return PersonalMetrics(
        share_count=agg.shares.get(user.id, 0),
        participation_count=agg.participation.get(user.id, 0),
        review_score=agg.review_score(user.id),
        review_rating_count=agg.review_ratings.get(user.id, 0),
        on_time_rate=agg.on_time_rate(user.id),
        closed_count=agg.closed.get(user.id, 0),
        recent_outputs=outputs,
        lookback_days=settings.participation_lookback_days,
        is_inactive=user.participation_tracked and outputs == 0,
        ranks={
            "sharing": _rank(boards.sharing, user.id),
            "participation": _rank(boards.participation, user.id),
            "review_quality": _rank(boards.review_quality, user.id),
            "punctuality": _rank(boards.punctuality, user.id),
        },
    )


def my_signup_out(signup: Signup, viewer: User) -> MySignup:
    return MySignup(
        id=signup.id,
        role=signup.role,
        review_topic=signup.review_topic,
        review_doc_url=signup.review_doc_url,
        review_submitted_at=signup.review_submitted_at,
        average_score=activity_service.weighted_average(signup),
        rating_count=len(signup.ratings),
        activity=activity_service.to_out(signup.activity, viewer),
    )


def tasks_for(db: Session, user: User, metrics: PersonalMetrics, group_count: int) -> list[Task]:
    tasks: list[Task] = []
    if metrics.is_inactive:
        tasks.append(Task(kind="inactive", priority=100))
    if not user.email:
        tasks.append(Task(kind="missing_email", priority=95))
    for invite in invite_service.for_user(db, user, pending_only=True):
        if not invite.activity.is_closed:
            tasks.append(
                Task(
                    kind="pending_invite",
                    priority=90,
                    invite_id=invite.id,
                    activity=UserBrief(id=invite.activity.id, name=invite.activity.title),
                )
            )
    for signup in signup_service.my_signups(db, user, include_closed=True):
        a = signup.activity
        if signup.role == SignupRole.REVIEWER and not signup.review_doc_url and a.is_closed:
            tasks.append(
                Task(
                    kind="submit_review",
                    priority=88,
                    signup_id=signup.id,
                    activity=UserBrief(id=a.id, name=a.title),
                )
            )
    for a in db.scalars(select(Activity).where(Activity.organizer_id == user.id, Activity.closed_at.is_(None))):
        if activity_service.state_of(a) == ActivityState.AWAITING_CLOSE:
            tasks.append(Task(kind="close_activity", priority=85, activity=UserBrief(id=a.id, name=a.title)))
    to_rate = len(signup_service.reviews_to_rate(db, user, limit=50))
    if to_rate:
        tasks.append(Task(kind="rate_reviews", priority=60, count=to_rate))
    if group_count == 0:
        tasks.append(Task(kind="join_group", priority=50))
    tasks.sort(key=lambda t: -t.priority)
    return tasks


def recommendations(db: Session, user: User, limit: int = 6) -> list[Recommendation]:
    my_group_ids = {g.id for g, _ in group_service.groups_of(db, user.id)}
    candidates = db.scalars(
        select(Activity)
        .where(activity_service.state_filter([ActivityState.UPCOMING]))
        .options(*activity_service.LOAD)
        .order_by(Activity.date, Activity.start_time)
        .limit(100)
    ).all()
    recs = []
    for a in candidates:
        if a.organizer_id == user.id or any(s.user_id == user.id for s in a.speakers):
            continue
        if any(s.user_id == user.id for s in a.signups):
            continue
        out = activity_service.to_out(a, user)
        score, reasons = 0, []
        if a.group_id in my_group_ids:
            score += 5
            reasons.append("your_group")
        if a.kind == ActivityKind.MEETUP:
            score += 2
            reasons.append("meetup")
            role = SignupRole.PARTICIPANT
        elif out.counts.reviewer_spots_left:
            score += 3
            reasons.append("reviewer_spots")
            role = SignupRole.REVIEWER
        else:
            score += 1
            reasons.append("observe")
            role = SignupRole.OBSERVER
        if out.viewer.pending_invite_id:
            score += 10
            reasons.insert(0, "invited")
        recs.append((score, a.date, a.start_time, Recommendation(activity=out, suggested_role=role, reasons=reasons)))
    recs.sort(key=lambda r: (-r[0], r[1], r[2]))
    return [r[3] for r in recs[:limit]]


def me_dashboard(db: Session, user: User) -> MeDashboard:
    metrics = personal_metrics(db, user)
    my_groups = group_service.groups_of(db, user.id)
    organizing = db.scalars(
        select(Activity)
        .where(Activity.organizer_id == user.id, Activity.closed_at.is_(None))
        .options(*activity_service.LOAD)
        .order_by(Activity.date, Activity.start_time)
    ).all()
    return MeDashboard(
        metrics=metrics,
        tasks=tasks_for(db, user, metrics, len(my_groups)),
        upcoming=[my_signup_out(s, user) for s in signup_service.my_signups(db, user, include_closed=False)],
        organizing=[activity_service.to_out(a, user) for a in organizing],
        groups=[MyGroup(id=g.id, name=g.name, role=role) for g, role in my_groups],
        invites=[invite_service.to_out(i) for i in invite_service.for_user(db, user)[:20]],
        recommendations=recommendations(db, user),
    )


def public_profile(db: Session, user: User, viewer: User | None) -> PublicProfile:
    history: list[HistoryEntry] = []
    involved = db.scalars(
        select(Activity)
        .where(
            (Activity.organizer_id == user.id)
            | Activity.id.in_(select(ActivitySpeaker.activity_id).where(ActivitySpeaker.user_id == user.id))
            | Activity.id.in_(select(Signup.activity_id).where(Signup.user_id == user.id))
        )
        .options(*activity_service.LOAD)
        .order_by(Activity.date.desc())
        .limit(40)
    ).all()
    for a in involved:
        out: ActivityOut = activity_service.to_out(a, viewer)
        if any(s.user_id == user.id for s in a.speakers):
            history.append(HistoryEntry(kind="spoke", date=a.date, activity=out))
        elif a.organizer_id == user.id:
            history.append(HistoryEntry(kind="organized", date=a.date, activity=out))
        signup = next((s for s in a.signups if s.user_id == user.id), None)
        if signup is not None:
            history.append(HistoryEntry(kind="signed_up", date=a.date, activity=out, role=signup.role))
    for c in db.scalars(
        select(Contribution).where(Contribution.user_id == user.id).order_by(Contribution.date.desc()).limit(20)
    ):
        history.append(
            HistoryEntry(
                kind="contribution",
                date=c.date,
                contribution=ContributionOut(
                    id=c.id, user=_brief(c.user), kind=c.kind, date=c.date, note=c.note, created_at=c.created_at
                ),
            )
        )
    history.sort(key=lambda h: h.date, reverse=True)
    return PublicProfile(
        user=_brief(user),
        bio=user.bio,
        joined_at=user.created_at,
        groups=[MyGroup(id=g.id, name=g.name, role=role) for g, role in group_service.groups_of(db, user.id)],
        metrics=personal_metrics(db, user),
        history=history[:40],
    )


def pending_invite_count(db: Session, user: User) -> int:
    return (
        db.scalar(select(func.count()).where(Invite.invitee_id == user.id, Invite.status == InviteStatus.PENDING)) or 0
    )
