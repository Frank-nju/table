"""Realistic demo data for local development and screenshots. Never run this against production."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Activity,
    ActivityKind,
    ActivitySpeaker,
    Contribution,
    ContributionKind,
    Group,
    GroupMembership,
    GroupRole,
    Invite,
    InviteStatus,
    ReviewRating,
    Room,
    RoomSlot,
    Signup,
    SignupRole,
    User,
    UserRole,
)
from app.scheduling import local_today
from app.security import hash_password

PASSWORD = "password123"

MEMBERS = [
    ("Lin Yue", "lin.yue", "zh"),
    ("Chen Hao", "chen.hao", "zh"),
    ("Zhou Xin", "zhou.xin", "zh"),
    ("Wang Fang", "wang.fang", "zh"),
    ("Liu Yang", "liu.yang", "en"),
    ("Sun Qi", "sun.qi", "zh"),
    ("Maya Patel", "maya.patel", "en"),
    ("Zhao Lei", "zhao.lei", "zh"),
    ("He Jing", "he.jing", "zh"),
    ("Tom Becker", "tom.becker", "en"),
    ("Xu Ran", "xu.ran", "zh"),
    ("Guo Ming", "guo.ming", "zh"),
]


def t(s: str) -> time:
    return time.fromisoformat(s)


def seed(db: Session) -> None:
    tz = get_settings().tz
    today = local_today()
    pw = hash_password(PASSWORD)
    long_ago = datetime.now(UTC) - timedelta(days=120)

    admin = User(
        name="CAC Admin",
        email="admin@example.edu",
        password_hash=pw,
        role=UserRole.ADMIN,
        created_at=long_ago,
        participation_tracked=False,
    )
    users = [
        User(name=n, email=f"{e}@example.edu", password_hash=pw, locale=loc, created_at=long_ago)
        for n, e, loc in MEMBERS
    ]
    db.add_all([admin, *users])
    u = {x.name.split()[0]: x for x in users}  # by first name

    rooms = [
        Room(name="CAC-101", capacity=40, notes="Projector, whiteboard"),
        Room(name="CAC-102", capacity=24, notes="Round tables"),
        Room(name="Xianlin B-204", capacity=60, notes="Lecture hall"),
    ]
    db.add_all(rooms)
    for offset in range(-30, 29):
        d = today + timedelta(days=offset)
        if d.weekday() == get_settings().meetup_weekday:
            db.add(RoomSlot(room=rooms[1], date=d, start_time=t("14:00"), end_time=t("18:00")))
        elif d.weekday() < 5:
            db.add(RoomSlot(room=rooms[0], date=d, start_time=t("13:00"), end_time=t("22:00")))
            db.add(RoomSlot(room=rooms[2], date=d, start_time=t("18:30"), end_time=t("21:30")))

    groups = {
        "systems": Group(
            name="Systems Reading Group",
            goal="Read and discuss one classic systems paper each week.",
            time_boundary="Autumn term 2026",
            plan="Thursday evenings: one presenter, three reviewers.",
            description="From Unix to Raft — the papers every engineer should know.",
        ),
        "ml": Group(
            name="ML Paper Club",
            goal="Reproduce one recent ML result per month.",
            time_boundary="Sept 2026 – Jan 2027",
            plan="Two talks a month, code on GitHub.",
            description="Hands-on with diffusion, transformers and friends.",
        ),
        "design": Group(
            name="Product & Design",
            goal="Ship one small product idea per term.",
            time_boundary="Autumn term 2026",
            plan="Critique sessions every other week.",
            description="User research, prototyping and design critique.",
        ),
    }
    db.add_all(groups.values())
    for key, leader, members in (
        ("systems", "Chen", ["Zhou", "Liu", "Zhao", "Tom"]),
        ("ml", "Lin", ["Maya", "Sun", "He", "Xu"]),
        ("design", "Wang", ["Guo", "Maya", "He"]),
    ):
        groups[key].memberships = [GroupMembership(user=u[leader], role=GroupRole.LEADER)] + [
            GroupMembership(user=u[m], role=GroupRole.MEMBER) for m in members
        ]

    def activity(
        title: str,
        days: int,
        start: str,
        end: str,
        organizer: str,
        speakers: list[str],
        *,
        room: Room | None = None,
        group: str | None = None,
        kind: ActivityKind = ActivityKind.REGULAR,
        description: str = "",
        location: str = "",
        closed: bool | None = None,
    ) -> Activity:
        d = today + timedelta(days=days)
        a = Activity(
            title=title,
            description=description,
            kind=kind,
            date=d,
            start_time=t(start),
            end_time=t(end),
            room=room,
            location=location,
            organizer=u[organizer],
            group=groups[group] if group else None,
            created_at=datetime.combine(d - timedelta(days=10), t("12:00"), tzinfo=tz),
        )
        a.speakers = [ActivitySpeaker(user=u[s], position=i) for i, s in enumerate(speakers)]
        if closed is not None:
            closed_at = datetime.combine(d, t(end), tzinfo=tz) + timedelta(hours=2 if closed else 50)
            a.closed_at, a.closed_on_time, a.closed_by_id = closed_at, closed, None
        db.add(a)
        return a

    def signup(a: Activity, who: str, role: SignupRole, topic: str = "", doc: bool = False) -> Signup:
        s = Signup(
            activity=a,
            user=u[who],
            role=role,
            review_topic=topic,
            created_at=datetime.combine(a.date - timedelta(days=3), t("10:00"), tzinfo=tz),
        )
        if doc:
            s.review_doc_url = f"https://www.yuque.com/cac/reviews/{a.title.split()[0].lower()}-{who.lower()}"
            s.review_submitted_at = datetime.combine(a.date + timedelta(days=1), t("21:00"), tzinfo=tz)
        db.add(s)
        return s

    def rate(s: Signup, who: str, score: int, comment: str = "") -> None:
        observer = any(x.user is u[who] and x.role == SignupRole.OBSERVER for x in s.activity.signups)
        db.add(ReviewRating(signup=s, rater=u[who], score=score, weight=10 if observer else 1, comment=comment))

    # ----- Past sessions -----
    raft = activity(
        "Raft: Understandable Consensus",
        -24,
        "19:00",
        "20:30",
        "Chen",
        ["Chen"],
        room=rooms[0],
        group="systems",
        closed=True,
        description="Leader election, log replication and why Raft is easier to teach than Paxos.",
    )
    r1 = signup(raft, "Zhou", SignupRole.REVIEWER, "How does Raft handle split votes?", doc=True)
    r2 = signup(raft, "Liu", SignupRole.REVIEWER, "Membership changes and joint consensus", doc=True)
    for who in ("Tom", "Zhao", "Maya"):
        signup(raft, who, SignupRole.OBSERVER)
    db.flush()
    rate(r1, "Tom", 9, "Clear diagrams of the election timeline.")
    rate(r1, "Zhao", 8)
    rate(r2, "Maya", 7, "Good questions; the write-up could be more concise.")
    rate(r2, "Chen", 8)

    diffusion = activity(
        "Diffusion Models from Scratch",
        -17,
        "19:00",
        "21:00",
        "Lin",
        ["Lin", "Maya"],
        room=rooms[2],
        group="ml",
        closed=True,
        description="We implement DDPM in 200 lines of PyTorch and train it live on MNIST.",
    )
    r3 = signup(diffusion, "Sun", SignupRole.REVIEWER, "Noise schedules and sample quality", doc=True)
    signup(diffusion, "He", SignupRole.REVIEWER, "Classifier-free guidance")
    for who in ("Xu", "Zhou", "Guo"):
        signup(diffusion, who, SignupRole.OBSERVER)
    db.flush()
    rate(r3, "Xu", 9)
    rate(r3, "Guo", 10, "Best review this term.")

    critique = activity(
        "Design Critique: Campus Map App",
        -10,
        "14:00",
        "15:30",
        "Wang",
        ["Wang", "Guo"],
        room=rooms[0],
        group="design",
        closed=False,
        description="Bring your laptop — we'll run a quick usability test together.",
    )
    signup(critique, "Maya", SignupRole.REVIEWER, "Accessibility of the colour palette", doc=True)
    signup(critique, "He", SignupRole.OBSERVER)

    activity(
        "CAC Meetup: Finding Your First Research Project",
        -9,
        "14:00",
        "16:00",
        "Zhao",
        ["Zhao"],
        room=rooms[1],
        kind=ActivityKind.MEETUP,
        closed=True,
        description="An informal chat with senior students about getting started in a lab.",
    )

    awaiting = activity(
        "eBPF for Observability",
        -2,
        "19:00",
        "20:00",
        "Liu",
        ["Liu"],
        room=rooms[0],
        group="systems",
        description="Tracing syscalls in production without restarting anything.",
    )
    signup(awaiting, "Chen", SignupRole.REVIEWER, "Overhead measurements")
    signup(awaiting, "Tom", SignupRole.OBSERVER)

    # ----- Upcoming sessions -----
    rust = activity(
        "Ownership in Rust, Visually",
        2,
        "19:00",
        "20:30",
        "Zhou",
        ["Zhou"],
        room=rooms[0],
        group="systems",
        description="Borrowing, lifetimes and the borrow checker explained with animations.",
    )
    signup(rust, "Chen", SignupRole.REVIEWER, "Comparing with C++ RAII")
    signup(rust, "Tom", SignupRole.OBSERVER)
    signup(rust, "Liu", SignupRole.OBSERVER)

    transformers = activity(
        "Attention Is All You Need — Line by Line",
        4,
        "19:00",
        "20:30",
        "Maya",
        ["Maya"],
        room=rooms[2],
        group="ml",
        description="Reading the transformer paper together, then building a tiny GPT.",
    )
    for who, topic in (("Lin", "Positional encodings"), ("Sun", "Training stability"), ("Xu", "Scaling laws")):
        signup(transformers, who, SignupRole.REVIEWER, topic)
    signup(transformers, "He", SignupRole.OBSERVER)

    sunday = today + timedelta(days=(get_settings().meetup_weekday - today.weekday()) % 7 or 7)
    meetup = activity(
        "CAC Meetup: Internship Season Q&A",
        (sunday - today).days,
        "14:00",
        "15:30",
        "Sun",
        ["Sun"],
        room=rooms[1],
        kind=ActivityKind.MEETUP,
        description="Résumés, interviews and offers — bring your questions.",
    )
    signup(meetup, "Guo", SignupRole.PARTICIPANT)
    signup(meetup, "Xu", SignupRole.PARTICIPANT)

    figma = activity(
        "Prototyping in Figma in 60 Minutes",
        7,
        "15:00",
        "16:00",
        "Guo",
        ["Guo"],
        room=rooms[0],
        group="design",
        description="From sketch to clickable prototype.",
    )
    activity(
        "Writing a Tiny Database in Go",
        9,
        "19:30",
        "21:00",
        "Tom",
        ["Tom", "Zhao"],
        room=rooms[0],
        group="systems",
        description="B-trees, write-ahead logs and crash recovery.",
    )
    activity(
        "Reading Group: The Mythical Man-Month",
        12,
        "18:30",
        "19:30",
        "He",
        ["He"],
        location="Library 3F reading room",
        description="Chapters 1–3. Copies available at the front desk.",
    )

    db.flush()
    db.add(
        Invite(
            activity=figma,
            inviter=u["Guo"],
            invitee=u["Wang"],
            status=InviteStatus.PENDING,
            message="Would love your eye on the interaction details!",
        )
    )
    db.add(Invite(activity=rust, inviter=u["Zhou"], invitee=u["Lin"], status=InviteStatus.PENDING))
    db.add(
        Contribution(
            user=u["He"],
            kind=ContributionKind.SHARING,
            date=today - timedelta(days=5),
            note="Talk at the university open day",
        )
    )
    db.add(Contribution(user=admin, kind=ContributionKind.MEETUP, date=today - timedelta(days=9)))
    db.commit()
