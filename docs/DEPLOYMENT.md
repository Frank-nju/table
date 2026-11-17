# Deployment

A deployment is two processes sharing one database:

| Process | Command | Notes |
|---|---|---|
| **web** | `gunicorn -c gunicorn.conf.py app.asgi:app` | Serves the API and the built frontend on port 8000 |
| **worker** | `python -m app.worker` | Sends queued email, daily review reminders, weekly participation report. Run exactly one |

Put nginx (or any TLS-terminating proxy) in front of the web process.

## Required settings

Copy [`backend/.env.example`](../backend/.env.example). In production you must set:

- `ENVIRONMENT=production`
- `SECRET_KEY`: a long random value (`python -c "import secrets; print(secrets.token_urlsafe(48))"`). Changing it signs everyone out.
- `DATABASE_URL`, for example `mysql+pymysql://cac:PASSWORD@127.0.0.1/cac?charset=utf8mb4` or `postgresql+psycopg://cac:PASSWORD@127.0.0.1/cac`
- `PUBLIC_BASE_URL`: the address people open, e.g. `https://cac.example.edu` (used in email links)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_SECURITY`, and `MAIL_FROM`, so that reminders and password resets are actually delivered

Useful extras: `ALLOWED_EMAIL_DOMAINS=smail.nju.edu.cn,nju.edu.cn` restricts sign-ups, `BOOTSTRAP_ADMIN_EMAILS` promotes listed addresses automatically, and `PARTICIPATION_REPORT_EMAIL` receives the weekly report.

Check email with `python -m app.cli send-test-email --to you@example.edu`.

## Option A: Docker Compose

```bash
cp backend/.env.example .env      # set SECRET_KEY, PUBLIC_BASE_URL, MYSQL_PASSWORD, MYSQL_ROOT_PASSWORD, SMTP_*
docker compose up -d --build
docker compose exec web python -m app.cli create-admin --email you@example.edu
```

This starts MySQL, applies migrations, and runs `web` (bound to `127.0.0.1:8000`) and `worker`. Point nginx at port 8000 using [`deploy/nginx/cac.conf`](../deploy/nginx/cac.conf). The database lives in the `db-data` volume; back it up with `docker compose exec db mysqldump …`.

## Option B: Ubuntu with systemd

Prerequisites: Python 3.11+, Node.js 20+, a MySQL or PostgreSQL database, and nginx.

```sql
CREATE DATABASE cac CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'cac'@'localhost' IDENTIFIED BY 'a-strong-password';
GRANT ALL PRIVILEGES ON cac.* TO 'cac'@'localhost';
```

```bash
sudo bash deploy/install.sh       # first run creates /etc/cac/cac.env and stops
sudo nano /etc/cac/cac.env        # set DATABASE_URL, PUBLIC_BASE_URL, SMTP_*
sudo bash deploy/install.sh       # builds, installs and starts cac-web + cac-worker
```

The script copies the app to `/opt/cac`, builds the frontend, creates a virtualenv, and installs [`cac-web.service`](../deploy/systemd/cac-web.service) (which runs migrations on start) and [`cac-worker.service`](../deploy/systemd/cac-worker.service). Then:

```bash
sudo cp deploy/nginx/cac.conf /etc/nginx/sites-available/cac && sudo ln -s ../sites-available/cac /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d cac.example.edu
```

To **upgrade**, pull the new code and run `sudo bash deploy/install.sh` again.
To read the **logs**, use `journalctl -u cac-web -f` and `journalctl -u cac-worker -f`.

## Windows

Gunicorn doesn't run on Windows, so use uvicorn directly for the web process, and run the worker separately (for example with NSSM or Task Scheduler):

```powershell
cd backend
.venv\Scripts\python -m app.cli migrate
.venv\Scripts\uvicorn app.asgi:app --host 0.0.0.0 --port 8000 --workers 2
.venv\Scripts\python -m app.worker
```

For a small single-machine setup you can instead set `RUN_SCHEDULER=true` and skip the separate worker.

## Health checks

- `GET /healthz` returns 200 while the process is up.
- `GET /readyz` returns 200 when the database is reachable, and 503 otherwise.
