# Upgrading from v2

Version 3 is a rewrite, and the data model changed in two important ways:

1. **People have real accounts.** v2 identified everyone by the name they typed, so anyone could act as anyone. v3 requires signing in with an email and password.
2. **Data is relational.** v2 stored everything as JSON blobs in one `app_rows` table with Chinese column names. v3 has proper tables (users, activities, signups, ratings, …) with constraints.

Nothing is lost: an importer reads the old `app_rows` table and maps every record onto the new schema.

## Steps

1. **Back up** the old database: `mysqldump table_signup > v2-backup.sql`.
2. **Create a new, empty database** for v3, and deploy v3 against it (see [DEPLOYMENT.md](DEPLOYMENT.md)). Run `python -m app.cli migrate`, but don't create any users yet. The importer only runs on an empty database.
3. **Import**, pointing at the old database (read-only access is enough):
   ```bash
   cd backend
   python -m app.cli import-legacy --source "mysql+pymysql://user:pass@127.0.0.1/table_signup?charset=utf8mb4"
   ```
   If you can't reach the old database from the new server, export `app_rows` to JSON and import the file instead:
   ```bash
   mysql -N -r -e "SELECT JSON_ARRAYAGG(JSON_OBJECT('table_name', table_name, 'row_id', row_id, 'row_data', row_data)) FROM app_rows" table_signup > legacy.json
   python -m app.cli import-legacy --json legacy.json
   ```
   The importer prints a summary of what it created, what it skipped, and why.
4. **Create your own admin account** if you weren't in the old `CAC管理员` list: `python -m app.cli create-admin --email you@example.edu`.
5. **Tell members how to activate their accounts.** Everyone from v2 now exists as an *unclaimed* account:
   - Members whose email was recorded in v2 go to **Sign in → Forgot password**, enter that email, and set a password from the link.
   - For members without an email on file, open **Admin → People**, click their email cell to add one, or use **Set-password link** to get a one-time link you can send them privately.

## How old data maps to new

| v2 (`app_rows.table_name`) | v3 |
|---|---|
| `用户档案`, plus every name seen anywhere | `users` (unclaimed; an email is attached when known) |
| `CAC管理员` | `users.role = admin` |
| `分享会活动` | `activities`. `活动时间 "14:00-15:30"` becomes start and end times, `活动教室` becomes a `rooms` row, `分享者 "A、B"` becomes speaker links, and `cac有约` becomes a CAC Meetup |
| `分享会报名` | `signups` (`评议员` → reviewer, `旁听` → observer, `参与者` → participant). The phone number moves to the person's profile |
| `评议评分` | `review_ratings` (self-ratings and duplicates are skipped) |
| `评议邀请` | `invites` (`已取消` maps to withdrawn) |
| `兴趣组`, `兴趣组成员` | `groups`, `group_memberships` |
| `输出活动记录` | `contributions` |
| `CAC教室时间槽` | `room_slots`. Adjacent 30-minute rows are merged into one window |

Names that look like student IDs (for example `MF2533001`, used by some very old rows) are imported but excluded from participation statistics. You can change this per person in **Admin → People**.

If your v2 data still lives in SeaTable, first move it to MySQL with the `scripts/migrate_seatable_to_mysql.py` script from v2 (it remains in this repository's git history), then follow the steps above.

## What changed for members

- Signing in is required to sign up, review or rate. Browsing stays open to everyone.
- Contact details (email, phone) are only visible to the organiser of a session and to administrators.
- Signups can be cancelled until the session starts. After that, only the organiser can remove someone.
- A session can be closed once it has started. Closing within the grace period (24 h by default) counts as on time.
- CAC Meetups follow `MEETUP_WEEKDAY` and `MEETUP_WINDOW_*` (Sunday 14:00–18:00 by default). v2 had two conflicting settings for this.
