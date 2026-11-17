# CAC Share Session System — Windows Server Deployment

## Server

- IP address: 47.102.100.9
- Operating system: Windows Server

## 1. Prepare the environment

### Install Python 3.10 or later

1. Visit https://www.python.org/downloads/.
2. Download the Windows installer.
3. Select **Add Python to PATH** during installation.

### Install Node.js 18 or later

1. Visit https://nodejs.org/.
2. Download and install the LTS release.

### Install MySQL

You can download the installer from https://dev.mysql.com/downloads/mysql/ and set a root password during setup. Alternatively, run PowerShell as Administrator and install MySQL with Chocolatey:

~~~powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
choco install mysql -y
~~~

Create the database:

~~~sql
CREATE DATABASE table_signup CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'table_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON table_signup.* TO 'table_user'@'localhost';
FLUSH PRIVILEGES;
~~~

## 2. Deploy the application

Upload the project directory to the server, for example, C:/table-signup.

Install dependencies:

~~~cmd
cd C:/table-signup
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt

cd frontend
npm install
~~~

Build the frontend:

~~~cmd
cd C:/table-signup/frontend
npm run build
~~~

The generated static files are placed in frontend/dist.

Create C:/table-signup/.env with the database settings:

~~~env
DB_BACKEND=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=table_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=table_signup
~~~

Start the service:

~~~cmd
cd C:/table-signup
.venv/Scripts/activate
python app.py
~~~

## 3. Configure the firewall

### Windows Firewall interface

1. Open **Windows Defender Firewall with Advanced Security**.
2. Select **Inbound Rules** → **New Rule**.
3. Choose **Port** → **TCP** → **Specific local ports: 8080**.
4. Select **Allow the connection**.
5. Name the rule **CAC Share Session System**.

### Command line

~~~powershell
New-NetFirewallRule -DisplayName "CAC Share Session - 8080" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow
~~~

## 4. Start the service at boot

### Task Scheduler

Create a basic task with the following settings:

- Name: CAC Share Session System
- Trigger: When the computer starts
- Action: Start a program
- Program: C:/table-signup/.venv/Scripts/pythonw.exe
- Arguments: app.py
- Start in: C:/table-signup

### NSSM (recommended)

~~~powershell
nssm install CACSignup "C:/table-signup/.venv/Scripts/pythonw.exe" "app.py"
nssm set CACSignup AppDirectory "C:/table-signup"
nssm set CACSignup DisplayName "CAC Share Session System"
nssm start CACSignup
~~~

Download NSSM from https://nssm.cc/download.

## 5. Verify the deployment

Check the health endpoint:

~~~cmd
curl http://localhost:8080/healthz
~~~

Open the application at http://47.102.100.9:8080.

## 6. Update the deployment

~~~cmd
cd C:/table-signup
git pull

.venv/Scripts/activate
pip install -r requirements.txt

cd frontend
npm install
npm run build
~~~

Restart the service with nssm restart CACSignup, or restart python app.py manually.

## 7. Common commands

| Task | Command |
|---|---|
| Start the service | python app.py |
| Start in the background | pythonw app.py |
| Build the frontend | cd frontend && npm run build |
| Run the frontend dev server | cd frontend && npm run dev |

## Aliyun security group

Allow inbound TCP traffic on port 8080 in the Aliyun console:

1. Open the ECS instance details.
2. Select **Security Groups**.
3. Add an inbound rule for TCP port 8080.

