# standalone-yuque-fetcher

A lightweight Python tool that fetches and extracts the body text of public
[Yuque](https://www.yuque.com/) documents.  It tries a simple HTTP GET first,
and falls back to a headless-browser render (via Playwright) when the
`--render` flag is supplied.

---

## Requirements

| Dependency     | Purpose                            | Required? |
|----------------|------------------------------------|-----------|
| Python 3.8+    | Runtime                            | ✅        |
| requests       | HTTP GET                           | ✅        |
| beautifulsoup4 | HTML parsing                       | ✅        |
| playwright     | Headless-browser render (`--render`) | Optional |

---

## Installation

```bash
# Clone (or copy) this sub-directory, then:
cd standalone-yuque-fetcher

# Create and activate a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install core dependencies
pip install -r scripts/requirements.txt
```

### Installing Playwright (optional)

Only needed when you add the `--render` flag:

```bash
pip install playwright && playwright install
```

---

## Usage

```
python3 scripts/fetch_yuque.py [--url URL] [--render] [--output FILE] [--timeout SECS]
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--url URL` | `https://nova.yuque.com/wg5tth/nuumlq/ky1ofwicugp9f5hq?singleDoc` | Target document URL |
| `--render` | off | Enable Playwright headless render before extraction |
| `--output FILE` | stdout | Write full extracted text to FILE |
| `--timeout SECS` | `15` | Network / page-load timeout |

### Example commands

```bash
# 1. Fetch default document, print first 1 000 chars (no arguments needed)
python3 scripts/fetch_yuque.py

# 2. Fetch a custom URL
python3 scripts/fetch_yuque.py --url "https://www.yuque.com/your/doc"

# 3. Save full text to a file
python3 scripts/fetch_yuque.py --output outputs/doc.txt

# 4. Use Playwright rendering (JS-heavy pages)
python3 scripts/fetch_yuque.py --render --output outputs/doc_rendered.txt

# 5. Increase timeout for slow connections
python3 scripts/fetch_yuque.py --timeout 30
```

### Expected output (no arguments)

```
2026-03-11T09:49:00 [INFO] Fetching URL with requests: https://nova.yuque.com/...
2026-03-11T09:49:01 [INFO] Received HTTP 200, content-length=123456
2026-03-11T09:49:01 [INFO] Done.
置顶-活动信息登记报名表
...（前 1000 字符）
```

See [`sample_output.txt`](./sample_output.txt) for a real example run.

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0`  | Success |
| `1`  | Network / HTTP error |
| `2`  | Could not extract content from page |
| `3`  | `--render` used but Playwright is not installed |

---

## Migrating to a standalone repository

To turn this sub-directory into its own independent repository:

### Option A — git subtree (preserves commit history)

```bash
# From the root of the Frank-nju/table repository:
git subtree split --prefix=standalone-yuque-fetcher -b yuque-fetcher-branch

# In a new empty GitHub repository (e.g. Frank-nju/yuque-fetcher):
git init yuque-fetcher
cd yuque-fetcher
git pull /path/to/table/repo yuque-fetcher-branch
git remote add origin https://github.com/Frank-nju/yuque-fetcher.git
git push -u origin main
```

### Option B — copy and push (simpler, no history)

```bash
cp -r standalone-yuque-fetcher /tmp/yuque-fetcher
cd /tmp/yuque-fetcher
git init
git add .
git commit -m "Initial commit: standalone yuque-fetcher"
git remote add origin https://github.com/Frank-nju/yuque-fetcher.git
git branch -M main
git push -u origin main
```

---

## Notes

- **Never commit tokens or cookies.**  If the document ever becomes private,
  pass credentials via environment variables and read them in code — do not
  hard-code them.
- The tool respects the site's public-facing HTML.  Avoid excessive polling
  that could burden the server.
- Tested with Python 3.8 – 3.11.

---

## License

MIT — see [LICENSE](../LICENSE) (add one when creating the standalone repo).
