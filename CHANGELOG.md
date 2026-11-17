# Changelog

## [3.1.0] — 2026-11 — Platform-native UI

Applied [Modern Web Guidance](https://github.com/GoogleChrome/modern-web-guidance) across the frontend.

- **Dialogs** are native `<dialog>` modals. The hand-written focus trap, Esc handling and body scroll lock are gone, and dialogs show their errors inline instead of behind the backdrop.
- **Menus and notifications** use the Popover API with anchor positioning. The account panel no longer claims `role="menu"` without the keyboard behaviour that role promises.
- **Notifications** live in a labelled region announced with `ariaNotify()`. Errors stay until dismissed, and nothing is shown behind an open modal.
- **Filters and view switches** are native radio groups instead of ARIA tabs that had no tab panels.
- **Theme:** colours are defined once with `light-dark()`. The light/dark choice moved to Settings (System / Light / Dark) and is applied before first paint by an inline script that the Content-Security-Policy allows by hash.
- **Chinese input:** the people picker no longer selects someone when Enter confirms a pinyin candidate.
- **Accessibility:** focus moves to the new page heading after navigation. Fields link their errors only while they're shown, and focus goes to the first invalid field after a failed submit. Session cards use a single, stretched title link.
- **Forms:** native validation with `:user-invalid`, a "Show password" toggle, `spellcheck="false"` on emails, and auto-growing text areas.
- **Text scaling:** sizes are in `rem`, breakpoints are in `em`, and nothing with text has a fixed height. The `text-scale` meta opt-in is set, and copy-link feedback appears on the button itself.

## [3.0.0] — 2026-11 — Complete rebuild

A ground-up rewrite. See [docs/UPGRADING.md](docs/UPGRADING.md) to move existing data across.

### Security
- Real accounts with email and password (Argon2), httpOnly session cookies, password reset by email, and rate-limited sign-in. v2 trusted whatever name was typed, so anyone could edit or delete anyone's sessions or make themselves an administrator.
- Role-based permissions are enforced on the server for every action.
- Contact details are visible only to organisers and administrators.
- CSRF protection, a Content-Security-Policy, and other security headers.

### Correctness
- A relational schema with foreign keys and unique constraints replaces the JSON-blob `app_rows` store.
- Reviewer limits and room bookings take row locks, so they hold across multiple server processes. v2 used an in-process lock.
- Background jobs run in a dedicated worker and are idempotent. v2 started a copy in every web worker.
- All times are handled in the configured time zone, not the server's local time.
- Fixed v2 frontend bugs: observers signed up with the wrong role value, status badges never matched, cancelling a signup always failed, and "Log in" on the profile page signed you in as `test`.

### Features
- A session form with live schedule checking, room availability per time slot, and confirmation of warnings before saving.
- Rooms with bookable open times, including weekly repeats.
- A review workflow: submit a write-up link, rate with observer weighting, and a "Rate reviews" queue.
- Invitations that are accepted automatically on signup.
- Interest groups: leadership transfer, member removal, and archiving.
- A personal dashboard with a to-do list, metrics, ranks and recommendations, plus public profiles.
- Leaderboards with 30/90-day windows.
- An admin dashboard: monthly report, participation watch, group health, reviewer watch, and clashes. Also people management, recorded contributions, and CSV export.
- Calendar (.ics) export, English and 简体中文, light and dark themes, and a mobile-first layout.
- Bilingual email templates delivered through a retrying outbox.

### Engineering
- FastAPI, SQLAlchemy 2 and Alembic on the backend; Vue 3, TypeScript and Vite on the frontend.
- 91 backend tests that pass on SQLite, PostgreSQL and MySQL; frontend unit tests; and a Playwright end-to-end suite.
- GitHub Actions CI, a Dockerfile, Docker Compose, systemd units and an install script.
- An importer for v2 data, and a demo-data seeder.

---

## [2026-03] Architecture refactor

### Architecture

- Split the former monolithic `app.py` into `routes/`, `services/`, and `models/`
- Migrated the frontend from vanilla JavaScript and Jinja2 templates to Vue 3, Vite, and Element Plus
- Decoupled the frontend from the API and added an independent frontend build

### Features

- Replaced free-form activity times with separate start and end time selectors
- Added room availability lookup for the selected date and time
- Added activity-type selection for regular activities and CAC-hosted sessions
- Blocked room conflicts between activities of the same type
- Added confirmation dialogs for destructive actions
- Added frontend conflict warnings

### Improvements

- Clarified the code structure for easier maintenance
- Standardized component-based frontend development and state management
- Centralized API handling and error reporting
- Added automatic database-column registration

### Documentation

- Rewrote the README to reflect the new architecture
- Added the Vue development guide
- Removed outdated architecture and code-review documents
- Updated the setup guide

---

## [2026-02] MySQL migration

### Added

- MySQL backend support
- SeaTable-to-MySQL migration script
- Scheduling-conflict detection in the governance dashboard
- Review-document scoring panel

### Improved

- Migrated the data layer from SeaTable to MySQL
- Added aggregate caching for activity and signup statistics

---

## [2026-01] Initial release

### Feature coverage

- End-to-end activity workflow: creation, signup, peer review, and closure
- Three entry points: home page, speaker workspace, and personal profile
- Organizational reporting: monthly reports, group health, review reminders, and participation-threshold alerts
- Personal workspace with aggregated tasks and activity recommendations

