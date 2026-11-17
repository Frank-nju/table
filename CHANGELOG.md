# Changelog

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

