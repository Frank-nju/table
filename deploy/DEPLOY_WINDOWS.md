# CAC分享会系统 - Windows服务器部署指南

## 服务器信息
- IP地址: 47.102.100.9
- 系统: Windows Server

---

## 一、环境准备

### 1. 安装 Python 3.10+

1. 访问 https://www.python.org/downloads/
2. 下载 Windows 安装包
3. 安装时勾选 "Add Python to PATH"

### 2. 安装 Node.js 18+

1. 访问 https://nodejs.org/
2. 下载 LTS 版本并安装

### 3. 安装 MySQL

#### 方法1: 下载MySQL安装包
1. 访问 https://dev.mysql.com/downloads/mysql/
2. 选择 Windows 版本下载
3. 运行安装程序，设置 root 密码

#### 方法2: 使用Chocolatey
```powershell
# 以管理员身份运行PowerShell
Set-ExecutionPolicy Bypass -Scope Process -Force
iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
choco install mysql -y
```

### 4. 创建数据库

```sql
CREATE DATABASE table_signup CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'table_user'@'localhost' IDENTIFIED BY '你的密码';
GRANT ALL PRIVILEGES ON table_signup.* TO 'table_user'@'localhost';
FLUSH PRIVILEGES;
```

---

## 二、部署应用

### 1. 上传项目文件

将整个项目文件夹上传到服务器，例如 `C:\table-signup`

### 2. 安装依赖

```cmd
cd C:\table-signup

# 后端依赖
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
```

### 3. 构建前端

```cmd
cd C:\table-signup\frontend
npm run build
```

构建完成后，`frontend\dist\` 目录包含静态文件。

### 4. 修改配置文件

编辑 `C:\table-signup\.env`：

```env
DB_BACKEND=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=table_user
MYSQL_PASSWORD=你的密码
MYSQL_DATABASE=table_signup
```

### 5. 启动服务

```cmd
cd C:\table-signup
.venv\Scripts\activate
python app.py
```

---

## 三、配置防火墙

### 方法1: 通过Windows防火墙界面
1. 打开 "高级安全Windows Defender防火墙"
2. 点击 "入站规则" → "新建规则"
3. 选择 "端口" → "TCP" → "特定本地端口: 8080"
4. 选择 "允许连接"
5. 命名为 "CAC分享会系统"

### 方法2: 使用命令行
```powershell
New-NetFirewallRule -DisplayName "CAC分享会-8080" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow
```

---

## 四、设置开机自启动

### 方法1: 使用任务计划程序
1. 打开 "任务计划程序"
2. 创建基本任务
   - 名称: CAC分享会系统
   - 触发器: 计算机启动时
   - 操作: 启动程序
   - 程序: `C:\table-signup\.venv\Scripts\pythonw.exe`
   - 参数: `app.py`
   - 起始位置: `C:\table-signup`

### 方法2: 使用NSSM（推荐）
```powershell
# 下载NSSM: https://nssm.cc/download
nssm install CACSignup "C:\table-signup\.venv\Scripts\pythonw.exe" "app.py"
nssm set CACSignup AppDirectory "C:\table-signup"
nssm set CACSignup DisplayName "CAC分享会系统"
nssm start CACSignup
```

---

## 五、验证部署

### 检查服务状态
```cmd
curl http://localhost:8080/healthz
```

### 访问应用
浏览器打开: http://47.102.100.9:8080

---

## 六、更新部署

```cmd
cd C:\table-signup

# 拉取代码
git pull

# 更新后端依赖
.venv\Scripts\activate
pip install -r requirements.txt

# 更新前端并构建
cd frontend
npm install
npm run build

# 重启服务
# 如果用NSSM:
nssm restart CACSignup
# 否则手动重启 python app.py
```

---

## 七、常用命令

| 操作 | 命令 |
|------|------|
| 启动服务 | `python app.py` |
| 后台启动 | `pythonw app.py` |
| 构建前端 | `cd frontend && npm run build` |
| 开发模式前端 | `cd frontend && npm run dev` |

---

## 阿里云安全组

别忘了在阿里云控制台开放端口：
1. 进入ECS实例详情
2. 点击 "安全组"
3. 添加入方向规则：端口 8080，协议 TCP