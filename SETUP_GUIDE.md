# Setup and Deployment Guide

Use this guide to install the application and verify a basic deployment.

## 1. Prerequisites

- Linux server (Ubuntu 22.04 or later recommended) or Windows Server
- Python 3.10 or later
- Node.js 18 or later for building the frontend
- MySQL 8.0 or later

## 2. Clone the repository and install dependencies

### Linux or macOS

```bash
git clone <your-repo-url> table
cd table

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
```

### Windows

```cmd
git clone <your-repo-url> table
cd table

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

cd frontend
npm install
```

## 3. Configure environment variables

Copy the example file and edit `.env`:

```bash
cp .env.example .env
```

On Windows, use `copy .env.example .env`.

Set the database connection details:

```env
DB_BACKEND=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=table_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=table_signup
```

Email notifications are optional:

```env
SMTP_HOST=smtp.example.com
SMTP_USER=noreply@example.com
SMTP_PASSWORD=your_password
```

## 4. Create the database

Run the following statements in MySQL:

```sql
CREATE DATABASE table_signup CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'table_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON table_signup.* TO 'table_user'@'localhost';
FLUSH PRIVILEGES;
```

On first startup, the application creates its physical storage tables, including `app_rows` and `app_table_columns`.

## 5. Build the frontend

```bash
cd frontend
npm run build
```

The backend serves the generated files from `frontend/dist/`.

## 6. Start the application

### Development

Start the backend in one terminal:

```bash
python app.py
```

Start the frontend development server in another:

```bash
cd frontend
npm run dev
```

- Backend: `http://localhost:8080`
- Frontend: `http://localhost:5173` (API requests are proxied to the backend)

### Production

Build the frontend, then start the backend:

```bash
python app.py
```

Open `http://localhost:8080`.

## 7. Basic acceptance checks

### 7.1 API smoke checks

```bash
curl -s http://localhost:8080/api/activities
curl -s http://localhost:8080/api/stats
curl -s http://localhost:8080/api/cac-admins
```

Each endpoint should return a JSON response with `"ok": true`.

### 7.2 Page checks

| Page | URL | Check |
|---|---|---|
| Home | `/` | Activity list and leaderboards are visible |
| Admin | `/admin` | Tabs work and the create-activity dialog opens |
| Profile | `/profile` | Login prompt or profile details are visible |

### 7.3 Feature checks

- [ ] Create an activity with a time and room
- [ ] Open an activity's details
- [ ] Register for an activity
- [ ] Add a CAC administrator from the admin page
- [ ] Add a room time slot from the admin page

## 8. Production deployment

### Linux with systemd and Nginx

The repository includes deployment templates:

```bash
sudo bash deploy/deploy_prod.sh /opt/table
sudo vim /etc/table-signup.env
sudo systemctl restart table-signup
```

### Windows Server

See the [Windows deployment guide](deploy/DEPLOY_WINDOWS.md).

### Docker (optional)

```bash
docker build -t cac-signup .
docker run -d -p 8080:8080 --env-file .env cac-signup
```

## 9. Updating a deployment

```bash
git pull
source .venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
npm run build

sudo systemctl restart table-signup  # Linux
```

On Windows, restart the service or restart `python app.py` manually. Existing database tables and columns remain compatible with the application.

## 10. Troubleshooting

### View logs

```bash
journalctl -u table-signup -f  # Linux systemd
```

When running the app directly, check the terminal output.

| Symptom | Likely cause | What to check |
|---|---|---|
| Blank frontend page | Frontend has not been built | Run `cd frontend && npm run build` |
| API returns 500 | Database connection failed | Check the `MYSQL_*` settings in `.env` |
| Broken page styling | Static files are missing | Check whether `frontend/dist/` exists |
| Activity creation fails | A required field is missing | Check the request payload |

## 11. Security recommendations

- Do not commit `.env` to the repository
- Rotate database passwords regularly
- Enable HTTPS in production
- Configure email only when notifications are needed

