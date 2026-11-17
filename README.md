# CAC Share Session Signup System

A lightweight platform for organizing community activities. It supports activity creation, registration, peer review, and organizational reporting.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3, Vite, Element Plus, Pinia |
| Backend | Flask |
| Database | MySQL or SeaTable |
| Deployment | Gunicorn and Nginx |

## Repository layout

```text
table/
├── app.py                 # Flask application entry point
├── config.py              # Application configuration
├── models/                # Data access layer
├── services/              # Business logic
├── routes/                # API routes
├── utils/                 # Shared utilities
├── frontend/              # Vue 3 application
├── templates/             # Deprecated Jinja2 frontend
├── deploy/                # Deployment scripts and configuration
└── tests/                 # Unit tests
```

## Features

### Activity management
- Create, edit, and delete activities
- Support regular activities and CAC-hosted sessions
- Select time in 30-minute increments and combine adjacent slots
- Find available rooms for the selected date and time
- Detect scheduling conflicts; same-type room conflicts are blocked

### Registration
- Register as a reviewer or an observer
- Limit each activity to three reviewers
- Ask reviewers to provide a review topic or question
- Allow participants to cancel their registration

### CAC administration
- Manage CAC administrators
- Define room availability slots
- Track whether each slot is available or reserved

### Governance dashboard
- View sharing and participation leaderboards
- Review participation-threshold alerts
- Inspect scheduling-conflict reports

### Personal workspace
- View profile details, registrations, and invitations

## Quick start

### Backend

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # On Windows, copy .env.example .env
```

Configure the database settings in `.env`, then start the server:

```bash
python app.py
```

The backend listens at `http://localhost:8080`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The development server listens at `http://localhost:5173` and proxies API requests to the backend.

### Production build

```bash
cd frontend
npm run build
```

The generated files are placed in `frontend/dist/` and served by the backend.

## Configuration

At minimum, configure a MySQL connection:

```env
DB_BACKEND=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=table_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=table_signup
```

Optional email settings:

```env
SMTP_HOST=smtp.example.com
SMTP_USER=noreply@example.com
SMTP_PASSWORD=your_password
```

CAC-hosted session settings can be configured with `CAC_FIXED_WEEKDAY` and `CAC_FIXED_TIME`.

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/activities` | List activities |
| GET | `/api/activity/<id>` | Get activity details |
| POST | `/api/activity` | Create an activity |
| PUT | `/api/activity/<id>` | Update an activity |
| DELETE | `/api/activity/<id>` | Delete an activity |
| POST | `/api/activity/<id>/close` | Close an activity |
| POST | `/api/signup` | Register for an activity |
| DELETE | `/api/signup/<id>` | Cancel a registration |
| GET | `/api/my-signups/<name>` | List a user's registrations |
| GET | `/api/cac-admins` | List CAC administrators |
| GET | `/api/cac-room-slots` | List room slots |
| GET | `/api/stats` | Get dashboard statistics |
| GET | `/api/leaderboards` | Get leaderboards |

## Frontend routes

| Route | Page |
|---|---|
| `/` | Home, activity list, and leaderboards |
| `/activity/:id` | Activity details and registration form |
| `/admin` | Administration |
| `/profile` | Personal workspace |

## Scheduling conflict rules

| Situation | Result |
|---|---|
| Same activity type, same room, overlapping times | Blocked |
| Different activity types, same room, overlapping times | Warning |
| Overlapping times without a room conflict | Warning |

## Database compatibility

The application currently uses Chinese table and column names in its existing database schema. These identifiers are part of the persisted data contract and remain unchanged so existing installations continue to work.

## Documentation

- [Setup and deployment guide](SETUP_GUIDE.md)
- [Changelog](CHANGELOG.md)
- [Vue development guide](frontend/VUE_DEV_GUIDE.md)
- [Windows deployment guide](deploy/DEPLOY_WINDOWS.md)

## Development commands

```bash
# Backend
python app.py

# Frontend
cd frontend
npm run dev
npm run build

# Unit tests
python tests/test_modules.py
```

## Updating a deployment

Pull the latest source, install updated dependencies, rebuild the frontend, and restart the backend service. Database tables and columns remain compatible with existing installations.

## License

No open-source license is included with this project.

