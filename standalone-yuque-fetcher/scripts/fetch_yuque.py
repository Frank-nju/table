#!/usr/bin/env python3
"""
fetch_yuque.py — Fetch and extract content from a public Yuque document.

Usage:
    python fetch_yuque.py                        # fetch default URL, print first 1000 chars
    python fetch_yuque.py --url <URL>            # fetch a custom URL
    python fetch_yuque.py --render               # use Playwright for JS-rendered pages
    python fetch_yuque.py --output out.txt       # write content to a file
    python fetch_yuque.py --timeout 30           # custom timeout in seconds (default: 20)

Exit codes:
    0  — success
    1  — fetch / parse error
    2  — import error (e.g. Playwright not installed)
"""

import argparse
import logging
import sys

DEFAULT_URL = (
    "https://nova.yuque.com/wg5tth/nuumlq/ky1ofwicugp9f5hq?singleDoc"
)
CONTENT_SELECTORS = ["article", ".yuque-markdown", ".doc-content"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Static fetch (requests + BeautifulSoup)
# ---------------------------------------------------------------------------

def fetch_static(url: str, timeout: int) -> str:
    """Fetch *url* with requests and extract plain text via BeautifulSoup."""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as exc:
        logger.error(
            "Missing dependency: %s. Run: pip install requests beautifulsoup4",
            exc,
        )
        sys.exit(2)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; yuque-fetcher/1.0; "
            "+https://github.com/Frank-nju/table)"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://nova.yuque.com/",
    }

    logger.info("Fetching (static) %s", url)
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("HTTP request failed: %s", exc)
        sys.exit(1)

    soup = BeautifulSoup(resp.text, "html.parser")

    for selector in CONTENT_SELECTORS:
        element = soup.select_one(selector)
        if element:
            logger.info("Content matched with selector: %s", selector)
            return element.get_text(separator="\n").strip()

    logger.warning(
        "No content matched selectors %s. "
        "The page may require JS rendering — try --render.",
        CONTENT_SELECTORS,
    )
    # Fallback: return all visible text from <body>
    body = soup.find("body")
    if body:
        return body.get_text(separator="\n").strip()
    return soup.get_text(separator="\n").strip()


# ---------------------------------------------------------------------------
# Rendered fetch (Playwright)
# ---------------------------------------------------------------------------

def fetch_rendered(url: str, timeout: int) -> str:
    """Fetch *url* using a headless Chromium browser via Playwright."""
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        logger.error(
            "Playwright is not installed. "
            "Run: pip install playwright && playwright install chromium"
        )
        sys.exit(2)

    timeout_ms = timeout * 1000
    logger.info("Fetching (rendered) %s", url)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (compatible; yuque-fetcher/1.0; "
                    "+https://github.com/Frank-nju/table)"
                )
            )
            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")

            # Try known selectors first
            for selector in CONTENT_SELECTORS:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    text = page.inner_text(selector)
                    logger.info("Content matched with selector: %s", selector)
                    return text.strip()
                except PWTimeout:
                    continue

            logger.warning(
                "No content matched selectors %s via Playwright. "
                "Falling back to full page text.",
                CONTENT_SELECTORS,
            )
            return page.inner_text("body").strip()
        finally:
            browser.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch content from a public Yuque document.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="Yuque document URL to fetch (default: built-in example URL)",
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="Use Playwright headless browser for JS-rendered pages",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="FILE",
        help="Write extracted content to FILE instead of stdout",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        metavar="SECONDS",
        help="Request / navigation timeout in seconds (default: 20)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.render:
        content = fetch_rendered(args.url, args.timeout)
    else:
        content = fetch_static(args.url, args.timeout)

    if not content:
        logger.error("No content extracted from %s", args.url)
        sys.exit(1)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(content)
            logger.info("Content written to %s", args.output)
        except OSError as exc:
            logger.error("Failed to write output file: %s", exc)
            sys.exit(1)
    else:
        # Default: print first 1000 characters to stdout
        print(content[:1000])
        if len(content) > 1000:
            print(f"\n... [truncated — total {len(content)} chars]")


if __name__ == "__main__":
    main()
