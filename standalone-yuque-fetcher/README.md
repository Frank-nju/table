# standalone-yuque-fetcher

A minimal, self-contained Python script that fetches and extracts content from a public [Yuque](https://www.yuque.com/) document.

> **Goal:** This sub-directory is intended to become an independent repository.  
> See [Migrating to a standalone repo](#migrating-to-a-standalone-repository) below.

---

## Features

- Fetches public Yuque documents with `requests` + `BeautifulSoup` (no browser required by default).
- Falls back to [Playwright](https://playwright.dev/python/) headless rendering when the page requires JavaScript (`--render` flag).
- Configurable via command-line arguments.
- Prints the first 1,000 characters to `stdout` when run without arguments.
- Exits with a non-zero status code on any error.

---

## Requirements

- Python 3.8+
- See [`scripts/requirements.txt`](scripts/requirements.txt) for Python package dependencies.

---

## Installation

```bash
# 1. (Recommended) Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 2. Install core dependencies
pip install -r scripts/requirements.txt

# 3. (Optional) Install Playwright + Chromium only if you need --render
pip install playwright
playwright install chromium
```

---

## Usage

### Basic — static fetch (default)

```bash
# Fetch the built-in example URL and print the first 1 000 characters
python scripts/fetch_yuque.py

# Fetch a custom URL
python scripts/fetch_yuque.py --url "https://nova.yuque.com/your-doc-path"

# Save content to a file
python scripts/fetch_yuque.py --output article.txt

# Custom timeout (seconds)
python scripts/fetch_yuque.py --timeout 30
```

### With Playwright rendering (`--render`)

Use this when the page requires JavaScript to display its content:

```bash
# Make sure Playwright is installed first (see Installation above)
python scripts/fetch_yuque.py --render

# Combine flags
python scripts/fetch_yuque.py --url "https://nova.yuque.com/your-doc-path" \
                               --render --output article.txt --timeout 30
```

### All options

| Flag | Default | Description |
|------|---------|-------------|
| `--url` | built-in example URL | Yuque document URL to fetch |
| `--render` | `false` | Enable Playwright headless rendering |
| `--output` | stdout | Write content to this file path |
| `--timeout` | `20` | Timeout in seconds |

---

## Example output

```
$ python scripts/fetch_yuque.py
2024-01-01T12:00:00 [INFO] Fetching (static) https://nova.yuque.com/...
2024-01-01T12:00:01 [INFO] Content matched with selector: article
置顶-活动信息登记报名表-0311更新
...（前 1,000 字符）...
```

---

## Notes

⚠️ **Never commit tokens or cookies.**  
This script is designed for publicly accessible documents only.  
Do not add authentication credentials (API tokens, cookies, passwords) to any committed file.

- The default selectors (`article`, `.yuque-markdown`, `.doc-content`) cover most Yuque page layouts. If they fail on a static fetch, try `--render`.
- Playwright requires a separate browser binary (`playwright install chromium`). The core script works without it.
- Respect the target website's `robots.txt` and terms of service. Do not hammer the server with rapid repeated requests.

---

## Migrating to a standalone repository

This directory is structured as an independent project and can be extracted into its own repository at any time.

### Option A — copy the directory (simplest)

```bash
# From the root of this repository:
cp -r standalone-yuque-fetcher /path/to/new/repo

cd /path/to/new/repo
git init
git add .
git commit -m "Initial commit: standalone-yuque-fetcher"

# Push to a new GitHub repository (create the repo on GitHub first)
git remote add origin https://github.com/<owner>/<new-repo>.git
git push -u origin main
```

### Option B — extract with full git history (`git subtree`)

```bash
# From the root of this repository:
git subtree split --prefix=standalone-yuque-fetcher -b split-yuque-fetcher

# Create the new repo directory
mkdir /path/to/new/repo && cd /path/to/new/repo
git init
git pull /path/to/original/table-repo split-yuque-fetcher
git remote add origin https://github.com/<owner>/<new-repo>.git
git push -u origin main
```

This preserves the commit history of `standalone-yuque-fetcher/` in the new repository.
