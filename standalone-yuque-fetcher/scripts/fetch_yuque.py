#!/usr/bin/env python3
"""
fetch_yuque.py

Fetch the text content of a public Yuque document.

Default mode uses requests + BeautifulSoup (no extra browser install required).
Pass --render to fall back to headless Playwright rendering when the page
requires JavaScript execution to expose its main content.

Compatible with Python 3.8+.
No sensitive tokens are included or required for public documents.
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup

DEFAULT_URL = (
    "https://nova.yuque.com/wg5tth/nuumlq/ky1ofwicugp9f5hq?singleDoc"
)

# Selectors tried in order; first match wins.
CONTENT_SELECTORS = [
    "article",
    ".yuque-markdown",
    ".doc-content",
    ".lake-content",
    "main",
]

logger = logging.getLogger("fetch_yuque")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch the text content of a public Yuque document.\n"
            "No-arg run fetches the default URL and prints the first 1000 characters."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--url", "-u",
        default=DEFAULT_URL,
        help="Yuque document URL to fetch (default: %(default)s)",
    )
    parser.add_argument(
        "--render", "-r",
        action="store_true",
        help=(
            "Use headless Playwright to render the page before extracting "
            "content (requires: pip install playwright && playwright install). "
            "Falls back automatically from requests if content is not found."
        ),
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        metavar="FILE",
        help="Write output to FILE instead of stdout.",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=15,
        metavar="SECONDS",
        help="Request / page-load timeout in seconds (default: %(default)s).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose / debug logging.",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Fetching helpers
# ---------------------------------------------------------------------------

def _extract_from_html(html: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (raw_html, plain_text) for the first matching content selector."""
    soup = BeautifulSoup(html, "html.parser")
    for sel in CONTENT_SELECTORS:
        el = soup.select_one(sel)
        if el:
            return el.decode_contents(), el.get_text(separator="\n").strip()
    return None, None


def fetch_with_requests(url: str, timeout: int) -> Tuple[Optional[str], Optional[str]]:
    """Download *url* with requests and try to extract main content."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; yuque-fetcher/1.0)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://nova.yuque.com/",
    }
    logger.debug("GET %s (timeout=%ds)", url, timeout)
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    logger.debug("HTTP %s, content-length=%s", resp.status_code, len(resp.text))
    return _extract_from_html(resp.text)


def fetch_with_playwright(url: str, timeout: int) -> Tuple[Optional[str], Optional[str]]:
    """Render *url* with a headless Chromium browser and extract main content."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error(
            "Playwright is not installed.\n"
            "  Install with:  pip install playwright && playwright install\n"
            "  Then retry:    python fetch_yuque.py --render"
        )
        raise

    logger.debug("Launching headless Chromium via Playwright …")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")

        # Give JS a moment to populate the DOM.
        page.wait_for_timeout(2000)

        html_content, text_content = None, None
        for sel in CONTENT_SELECTORS:
            el = page.query_selector(sel)
            if el:
                html_content = el.inner_html()
                text_content = el.inner_text()
                logger.debug("Content found via selector '%s'", sel)
                break

        if not html_content:
            logger.debug("No selector matched; returning full page source.")
            html_content = page.content()
            text_content = ""

        browser.close()
    return html_content, text_content


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def main(argv: Optional[list] = None) -> int:
    args = parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    no_args = argv is None and len(sys.argv) == 1
    logger.info("Fetching document: %s", args.url)

    raw_html: Optional[str] = None
    text: Optional[str] = None

    # --- Step 1: try requests + BeautifulSoup ---
    try:
        raw_html, text = fetch_with_requests(args.url, args.timeout)
        if raw_html:
            logger.info("Content extracted via requests + BeautifulSoup.")
        else:
            logger.warning(
                "requests: page fetched but no content selector matched. "
                "Consider retrying with --render."
            )
    except requests.RequestException as exc:
        logger.warning("requests fetch failed: %s", exc)

    # --- Step 2: optionally try Playwright ---
    if not raw_html and args.render:
        logger.info("Falling back to Playwright rendering (--render specified).")
        try:
            raw_html, text = fetch_with_playwright(args.url, args.timeout)
        except ImportError:
            return 2
        except Exception as exc:
            logger.error("Playwright rendering failed: %s", exc)
            return 2

    if not raw_html:
        logger.error(
            "Could not extract document content.\n"
            "  - If the page requires JavaScript rendering, retry with: --render\n"
            "  - Make sure the URL is publicly accessible without login."
        )
        return 3

    if text:
        output_text = text
    else:
        # raw_html returned (e.g. full-page Playwright fallback); strip tags.
        logger.info("No plain text extracted; stripping HTML tags for output.")
        soup = BeautifulSoup(raw_html, "html.parser")
        output_text = soup.get_text(separator="\n").strip() or raw_html

    # --- Output ---
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(output_text)
            logger.info("Output saved to: %s", args.output)
        except OSError as exc:
            logger.error("Failed to write output file: %s", exc)
            return 4
    else:
        # No-arg / quick-check mode: show first 1000 characters.
        if no_args:
            print(output_text[:1000])
        else:
            print(output_text)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
