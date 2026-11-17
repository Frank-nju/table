"""Management commands.

python -m app.cli migrate                     # create/upgrade the database schema
python -m app.cli create-admin --email a@b.c  # create or promote an administrator
python -m app.cli seed-demo                   # fill an empty database with realistic demo data
python -m app.cli import-legacy --source URL  # import data from the previous version
python -m app.cli run-jobs                    # run the background jobs once
python -m app.cli send-test-email --to a@b.c  # check SMTP settings
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from sqlalchemy import func, select

from app.config import get_settings
from app.db import SessionLocal
from app.models import User, UserRole
from app.security import hash_password


def migrate(_: argparse.Namespace) -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parent.parent / "migrations"))
    command.upgrade(cfg, "head")
    print("Database is up to date.")


def create_admin(args: argparse.Namespace) -> None:
    email = args.email.strip().lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            password = args.password or getpass.getpass("Password (8+ characters): ")
            if len(password) < 8:
                sys.exit("Password must be at least 8 characters.")
            user = User(name=args.name or email.split("@")[0], email=email, password_hash=hash_password(password))
            db.add(user)
            action = "Created"
        else:
            action = "Promoted"
        user.role = UserRole.ADMIN
        user.is_active = True
        db.commit()
        print(f"{action} administrator {user.name} <{email}>.")


def seed_demo(args: argparse.Namespace) -> None:
    from app.seed import seed

    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(User)) and not args.force:
            sys.exit("The database already has users; pass --force to seed anyway.")
        seed(db)
    print("Demo data created. Sign in as admin@example.edu / password123 (or any member, same password).")


def import_legacy(args: argparse.Namespace) -> None:
    from app.legacy import load_from_database, load_from_json, run_import

    tables = load_from_database(args.source) if args.source else load_from_json(args.json)
    with SessionLocal() as db:
        report = run_import(db, tables)
    print(report.summary())
    print(
        "\nNext steps: members with an email on file can activate their account via “Forgot password”. "
        "Use Admin → People to add emails or create set-password links for everyone else."
    )


def run_jobs(_: argparse.Namespace) -> None:
    from app.services.jobs import run_all

    with SessionLocal() as db:
        print(run_all(db))


def send_test_email(args: argparse.Namespace) -> None:
    from app.services import mail

    settings = get_settings()
    if not settings.mail_enabled:
        sys.exit("SMTP is not configured (set SMTP_HOST and MAIL_FROM).")
    with SessionLocal() as db:
        mail.queue(db, args.to, f"[{settings.app_name}] Test email", "If you can read this, email works.")
        db.commit()
        sent = mail.deliver_pending(db)
    print("Sent." if sent else "Sending failed; check the logs.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(required=True)

    sub.add_parser("migrate", help="create or upgrade the database schema").set_defaults(fn=migrate)

    p = sub.add_parser("create-admin", help="create or promote an administrator")
    p.add_argument("--email", required=True)
    p.add_argument("--name")
    p.add_argument("--password", help="omit to be prompted")
    p.set_defaults(fn=create_admin)

    p = sub.add_parser("seed-demo", help="fill the database with demo data")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=seed_demo)

    p = sub.add_parser("import-legacy", help="import data from the previous version")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--source", help="SQLAlchemy URL of the old database, e.g. mysql+pymysql://u:p@host/db")
    src.add_argument("--json", help="path to a JSON export of the old app_rows table")
    p.set_defaults(fn=import_legacy)

    sub.add_parser("run-jobs", help="run the background jobs once").set_defaults(fn=run_jobs)

    p = sub.add_parser("send-test-email", help="check SMTP settings")
    p.add_argument("--to", required=True)
    p.set_defaults(fn=send_test_email)

    args = parser.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
