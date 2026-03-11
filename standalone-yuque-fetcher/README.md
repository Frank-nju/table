# yuque-fetcher (standalone)

A lightweight Python script that fetches the plain-text content of a **public** Yuque document.

- **Default mode** — uses `requests` + `BeautifulSoup` (no browser install required).
- **Render mode** — pass `--render` to use a headless Chromium browser via Playwright (optional; useful when the page renders its content entirely with JavaScript).
- **Compatible with Python 3.8+**
- **No sensitive tokens or secrets are included.** This script only accesses publicly shared documents.

---

## Quick start (local)

```bash
# 1. Clone the repo (or just this sub-directory)
git clone https://github.com/Frank-nju/table.git
cd table/standalone-yuque-fetcher

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install required dependencies
pip install -r scripts/requirements.txt

# 4. Run with no arguments → fetches the default URL, prints first 1000 chars
python scripts/fetch_yuque.py
```

---

## Running inside GitHub Codespaces

GitHub Codespaces gives you a full VS Code environment in the browser with Python pre-installed — no local setup required.

### Step 1 — Open a Codespace

1. Go to <https://github.com/Frank-nju/table>.
2. Click the green **Code** button → **Codespaces** tab → **Create codespace on main** (or select the branch you want).
3. The Codespace will open in your browser with a VS Code interface and an integrated terminal.

> **Tip:** You can also open a Codespace directly on a specific path by clicking **Open in Codespace** from the repository file tree.

### Step 2 — Select the correct Python version

The Codespace image ships with Python 3.x by default. Verify the version:

```bash
python3 --version   # should be 3.8 or newer
```

If you need a specific version, use `pyenv` (pre-installed in many Codespace images):

```bash
pyenv install 3.11
pyenv local 3.11
python3 --version
```

### Step 3 — Navigate to the project directory

In the Codespaces terminal:

```bash
cd standalone-yuque-fetcher
```

### Step 4 — Create a virtual environment and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r scripts/requirements.txt
```

### Step 5 — Run the script

**Quick check (no arguments)** — fetches the default URL and prints the first 1000 characters:

```bash
python scripts/fetch_yuque.py
```

**Fetch a custom URL:**

```bash
python scripts/fetch_yuque.py --url "https://nova.yuque.com/wg5tth/nuumlq/ky1ofwicugp9f5hq?singleDoc"
```

**Save output to a file:**

```bash
python scripts/fetch_yuque.py --output outputs/doc.txt
```

**Verbose logging:**

```bash
python scripts/fetch_yuque.py --verbose
```

### Step 6 — (Optional) Install Playwright for JavaScript-rendered pages

Some Yuque pages load their content dynamically via JavaScript. In that case, use `--render`:

```bash
pip install playwright
playwright install   # downloads Chromium/Firefox/WebKit (~200 MB, one-time)
python scripts/fetch_yuque.py --render
```

> **Note:** `playwright install` downloads browser binaries. In Codespaces, this step requires internet access (enabled by default). The download may take a couple of minutes.

---

## Command-line reference

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--url` | `-u` | see script | Yuque document URL to fetch |
| `--render` | `-r` | off | Use Playwright headless browser |
| `--output` | `-o` | stdout | File path to write output |
| `--timeout` | `-t` | `15` | Request / page-load timeout (seconds) |
| `--verbose` | `-v` | off | Enable debug logging |

### Return codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `2` | Playwright not installed or render error |
| `3` | Content not found (no selector matched) |
| `4` | Failed to write output file |
| `130` | Interrupted by user (Ctrl-C) |

---

## Example commands and expected output

```bash
$ python scripts/fetch_yuque.py
INFO: Fetching document: https://nova.yuque.com/wg5tth/nuumlq/...
INFO: Content extracted via requests + BeautifulSoup.
置顶-活动信息登记报名表-0311更新
...（first 1000 characters of document text）
```

```bash
$ python scripts/fetch_yuque.py --render --verbose
DEBUG: Launching headless Chromium via Playwright …
DEBUG: Content found via selector 'article'
INFO: Content extracted via Playwright rendering.
...
```

---

## Optional: devcontainer configuration

To pin the Python version and pre-install dependencies automatically in every new Codespace, add a `.devcontainer/devcontainer.json` file at the root of the repository:

```json
{
  "name": "yuque-fetcher dev",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "postCreateCommand": "cd standalone-yuque-fetcher && pip install -r scripts/requirements.txt",
  "customizations": {
    "vscode": {
      "extensions": ["ms-python.python"]
    }
  }
}
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `ModuleNotFoundError: No module named 'bs4'` | Dependencies not installed | `pip install -r scripts/requirements.txt` |
| `Playwright is not installed` | `playwright` package missing | `pip install playwright && playwright install` |
| Script exits with code 3 (no content found) | Page renders via JS | Add `--render` flag |
| `requests.exceptions.ConnectionError` | No network or URL changed | Check internet access; verify URL is still public |
| `TimeoutError` | Slow network | Increase timeout: `--timeout 30` |
| Playwright download is very slow in Codespaces | Large binary download | Wait or use `playwright install chromium` to install only Chromium |

---

## Migrating this directory into its own repository

If you want to move `standalone-yuque-fetcher/` into a brand-new repository (e.g., `Frank-nju/yuque-fetcher`):

### Option A — Copy and push (simple)

```bash
# From the root of the table repo
cp -r standalone-yuque-fetcher /tmp/yuque-fetcher
cd /tmp/yuque-fetcher
git init
git add .
git commit -m "Initial commit: standalone yuque-fetcher"
# Create Frank-nju/yuque-fetcher on GitHub, then:
git remote add origin git@github.com:Frank-nju/yuque-fetcher.git
git push -u origin main
```

### Option B — Preserve commit history with `git subtree`

```bash
# From the root of the table repo
git subtree split -P standalone-yuque-fetcher -b split-yuque-fetcher
git remote add yuque-fetcher git@github.com:Frank-nju/yuque-fetcher.git
git push yuque-fetcher split-yuque-fetcher:main
```

---

## Notes

- **No secrets or tokens are used.** This script only fetches publicly shared documents. Do not commit authentication tokens or cookies to version control.
- Please respect the Yuque terms of service and do not hammer their servers with automated requests.
