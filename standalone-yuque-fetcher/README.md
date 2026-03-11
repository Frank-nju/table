# yuque-fetcher (standalone)

一个轻量的 Python 脚本，用于抓取**公开**语雀文档的正文内容。

- 默认使用 `requests` + `BeautifulSoup` 直接解析 HTML，零浏览器依赖。
- 当页面需要 JavaScript 渲染时，可通过 `--render` 启用可选的 [Playwright](https://playwright.dev/python/) 后端。
- 支持输出到文件或标准输出。
- 兼容 Python 3.8 – 3.11。

---

## 目录

- [快速开始](#快速开始)
- [安装](#安装)
- [使用方法](#使用方法)
- [可选：Playwright 渲染](#可选playwright-渲染)
- [示例输出](#示例输出)
- [如何迁移为独立仓库](#如何迁移为独立仓库)
- [注意事项](#注意事项)

---

## 快速开始

```bash
# 克隆仓库后进入项目目录
cd standalone-yuque-fetcher

# 安装依赖
pip install -r scripts/requirements.txt

# 无参数运行：抓取内置示例链接，打印前 1000 字符
python3 scripts/fetch_yuque.py
```

---

## 安装

**Python 3.8+ 是必要条件。**

```bash
# 推荐使用虚拟环境
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -r scripts/requirements.txt
```

---

## 使用方法

```text
usage: fetch_yuque.py [-h] [--url URL] [--render] [--output OUTPUT]
                      [--timeout TIMEOUT] [--verbose]

选项说明:
  --url, -u       抓取的文档 URL（默认：内置示例链接）
  --render, -r    启用 Playwright 无头浏览器渲染（可选依赖）
  --output, -o    输出文件路径（默认输出到 stdout）
  --timeout, -t   请求超时秒数（默认 15）
  --verbose, -v   输出详细日志
```

### 示例命令

```bash
# 1. 抓取默认示例文档（无参数快速自检）
python3 scripts/fetch_yuque.py

# 2. 抓取指定 URL 并保存到文件
python3 scripts/fetch_yuque.py \
  --url "https://nova.yuque.com/wg5tth/nuumlq/ky1ofwicugp9f5hq?singleDoc" \
  --output outputs/doc.txt

# 3. 使用 Playwright 渲染（页面需要 JS 时）
python3 scripts/fetch_yuque.py --render \
  --url "https://nova.yuque.com/..."

# 4. 开启详细日志
python3 scripts/fetch_yuque.py --verbose
```

### 返回码

| 代码 | 含义 |
|------|------|
| 0    | 成功 |
| 2    | Playwright 未安装或渲染失败 |
| 3    | 未找到正文（选择器未匹配） |
| 4    | 写文件失败 |
| 130  | 用户中断（Ctrl-C） |

---

## 可选：Playwright 渲染

当目标页面通过 JavaScript 动态加载正文，`requests` 直接抓取可能无法获取内容。此时可安装 Playwright：

```bash
pip install playwright
playwright install   # 下载 Chromium 等浏览器二进制（约 100–300 MB）
```

然后在运行时加上 `--render` 标志即可：

```bash
python3 scripts/fetch_yuque.py --render --url "https://nova.yuque.com/..."
```

> **注意**：`playwright install` 只需运行一次，用于下载无头浏览器二进制文件。

---

## 示例输出

参见 [sample_output.txt](sample_output.txt)。

实际运行效果（示意）：

```
INFO: Fetching https://nova.yuque.com/wg5tth/nuumlq/ky1ofwicugp9f5hq?singleDoc
置顶-活动信息登记报名表
...（文档正文前 1000 字符）
```

---

## 如何迁移为独立仓库

### 方法 A：复制目录并初始化新仓库

```bash
cp -r standalone-yuque-fetcher /path/to/yuque-fetcher
cd /path/to/yuque-fetcher
git init
git add .
git commit -m "init: standalone yuque-fetcher"
git remote add origin git@github.com:Frank-nju/yuque-fetcher.git
git push -u origin main
```

### 方法 B：使用 git subtree 保留提交历史

```bash
# 在原仓库根目录执行
git subtree split -P standalone-yuque-fetcher -b yuque-fetcher-split
git remote add yuque-fetcher git@github.com:Frank-nju/yuque-fetcher.git
git push yuque-fetcher yuque-fetcher-split:main
```

---

## 注意事项

- **不要提交任何个人访问令牌（token）或浏览器 Cookie。** 若目标文档为私有，请在运行时通过环境变量或安全的 secrets 管理方式提供凭证，切勿硬编码进源代码。
- 请遵守语雀服务条款与版权政策，不要对站点造成过载。
- 本脚本假设目标文档为**公开可访问**（无需登录）。
- 若需抓取需要认证的文档，可在 `headers` 中加入 `Cookie` 或 `X-Auth-Token`，但请妥善保管这些凭证。

---

## CI

本项目通过 GitHub Actions 在 Python 3.8–3.11 上自动运行依赖安装与脚本自检，详见 [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)。

---

## License

[MIT](LICENSE)
