# fetch_yuque — 语雀公开文档抓取脚本

## 简介

`scripts/fetch_yuque.py` 是一个 Python 脚本，用于抓取指定语雀公开文档的正文内容（HTML 与纯文本），无需登录。

**目标文档链接（公开，互联网所有人可访问）：**
```
https://nova.yuque.com/wg5tth/nuumlq/ky1ofwicugp9f5hq?singleDoc
```

---

## 功能特性

- 优先使用 `requests + BeautifulSoup` 直接抓取并解析静态 HTML（速度快、无需浏览器）
- 若静态抓取未能匹配正文（页面需要 JS 渲染），可通过 `--render` 参数切换为 Playwright 无头浏览器抓取
- 支持命令行参数：`--url`、`--render`、`--output`、`--timeout`
- **自检模式**：不带参数直接运行时，自动抓取默认链接并在控制台输出前 1000 字符，方便快速验证
- 友好的日志与错误处理（请求失败、选择器未匹配、Playwright 未安装等均有提示）
- 返回非 0 状态码以便 CI 或调用方检测失败

---

## 安装依赖

```bash
pip install -r scripts/requirements.txt
```

若需要使用 Playwright 渲染模式（`--render`），额外运行：

```bash
pip install playwright
playwright install chromium
```

---

## 快速上手

### 自检模式（无参数运行）

```bash
python scripts/fetch_yuque.py
```

脚本会自动抓取默认链接，在控制台输出正文前 1000 字符，用于验证功能是否正常。

**预期输出示例：**
```
[INFO] 使用 requests 直接抓取：https://nova.yuque.com/wg5tth/nuumlq/ky1ofwicugp9f5hq?singleDoc
[INFO] 使用选择器 'article' 找到正文
=== [自检] 正文前 1000 字符 ===
置顶-活动信息登记报名表-0311更新

...（正文内容）...
=== [自检] HTML 前 500 字符 ===
<h1>置顶-活动信息登记报名表-0311更新</h1>...
```

> 若页面需要 JS 渲染，requests 模式会提示未找到选择器，此时请加 `--render` 参数。

---

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--url` | 要抓取的语雀公开文档 URL | 内置默认链接 |
| `--render` | 使用 Playwright 无头浏览器渲染后抓取 | 未开启 |
| `--output FILE` | 将抓取到的 HTML 保存到指定文件 | 不保存 |
| `--timeout N` | 请求超时秒数 | 20 |
| `--self-check` | 自检模式（同无参数运行） | — |

---

## 示例命令

```bash
# 1. 自检（抓取默认链接，输出前 1000 字符）
python scripts/fetch_yuque.py

# 2. 抓取指定链接
python scripts/fetch_yuque.py --url "https://nova.yuque.com/wg5tth/nuumlq/ky1ofwicugp9f5hq?singleDoc"

# 3. 使用 Playwright 渲染模式（页面需要 JS 时）
python scripts/fetch_yuque.py --url "https://nova.yuque.com/wg5tth/nuumlq/ky1ofwicugp9f5hq?singleDoc" --render

# 4. 保存 HTML 到文件
python scripts/fetch_yuque.py --url "https://nova.yuque.com/..." --output output.html

# 5. 设置更长的超时时间
python scripts/fetch_yuque.py --timeout 60
```

---

## 工作原理

### 方式一：requests + BeautifulSoup（默认）

脚本用 `requests` 直接 GET 目标 URL，拿到完整 HTML 后用 BeautifulSoup 按以下选择器依次匹配正文：

```
article → .yuque-markdown → .doc-content → .lake-content → .ne-viewer-body → [data-testid='doc-body'] → .content
```

找到第一个匹配的元素即作为正文，同时返回 HTML 和纯文本。

### 方式二：Playwright（`--render` 时启用）

当目标页面需要 JavaScript 才能渲染内容时，脚本启动 Chromium 无头浏览器，等待页面加载并尝试同样的选择器列表。若均未匹配则返回完整页面 HTML。

---

## 无需登录的前提

本脚本假定目标语雀文档已通过"**公开分享**"方式发布，互联网所有人均可访问，无需登录账号。

如需抓取**私有文档**，需在请求头中携带语雀 Personal Access Token：

1. 登录语雀 → 账户设置 → Token
2. 生成新 Token，赋予只读权限
3. 在请求头中添加 `X-Auth-Token: <your-token>`（**切勿将 Token 提交至代码仓库**）

---

## 注意事项

- 请遵守语雀的服务条款与版权规定，勿频繁抓取或抓取私有内容。
- **切勿**将个人访问 Token、Cookie 等敏感信息提交到代码仓库。
- 语雀页面的 HTML 结构可能随版本更新而变化，若选择器失效请根据实际页面结构调整 `CONTENT_SELECTORS`。
