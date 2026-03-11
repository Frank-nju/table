#!/usr/bin/env python3
"""
fetch_yuque.py — Fetch and extract the body text of a public Yuque document.

Default behaviour (no arguments):
    Fetches https://nova.yuque.com/wg5tth/nuumlq/ky1ofwicugp9f5hq?singleDoc
    and prints the first 1 000 characters to stdout.

Exit codes:
    0  success
    1  network / HTTP error
    2  content not found
    3  Playwright not installed (only raised when --render is used)
"""

import argparse
import logging
import sys

DEFAULT_URL = "https://nova.yuque.com/wg5tth/nuumlq/ky1ofwicugp9f5hq?singleDoc"
CONTENT_SELECTORS = ["article", ".yuque-markdown", ".doc-content"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Fetch the body text of a public Yuque document.",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="Target Yuque document URL (default: %(default)s)",
    )
    parser.add_argument(
        "--render",
        action="store_true",
        default=False,
        help=(
            "Use Playwright headless browser to render the page before "
            "extracting text.  Requires: pip install playwright && "
            "playwright install"
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="FILE",
        help="Write output to FILE instead of stdout.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        metavar="SECONDS",
        help="Request / page-load timeout in seconds (default: %(default)s).",
    )
    return parser.parse_args(argv)


def _build_headers():
    return {
        "User-Agent": (
            "Mozilla/5.0 (compatible; yuque-fetcher/1.0; "
            "+https://github.com/Frank-nju/table)"
        ),
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://nova.yuque.com/",
    }


def _extract_text_from_html(html: str) -> str:
    """Parse *html* and return the inner text of the first matching selector."""
    from bs4 import BeautifulSoup  # noqa: PLC0415  (local import for clarity)

    soup = BeautifulSoup(html, "html.parser")
    for selector in CONTENT_SELECTORS:
        element = soup.select_one(selector)
        if element:
            logger.debug("Matched selector: %s", selector)
            return element.get_text(separator="\n").strip()
    return ""


# ---------------------------------------------------------------------------
# Fetch strategies
# ---------------------------------------------------------------------------

def fetch_with_requests(url: str, timeout: int) -> str:
    """
    Attempt a plain HTTP GET and extract the document body.

    Returns the extracted text, or an empty string when no content selector
    matched.
    """
    import requests  # noqa: PLC0415

    logger.info("Fetching URL with requests: %s", url)
    try:
        resp = requests.get(url, headers=_build_headers(), timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        logger.error("Request timed out after %d s.", timeout)
        sys.exit(1)
    except requests.exceptions.HTTPError as exc:
        logger.error("HTTP error: %s", exc)
        sys.exit(1)
    except requests.exceptions.RequestException as exc:
        logger.error("Network error: %s", exc)
        sys.exit(1)

    logger.info(
        "Received HTTP %d, content-length=%d",
        resp.status_code,
        len(resp.content),
    )
    return _extract_text_from_html(resp.text)


def fetch_with_playwright(url: str, timeout: int) -> str:
    """
    Render the page with Playwright and extract the document body.

    Raises SystemExit(3) with a friendly message if Playwright is not
    installed.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout  # noqa: PLC0415
    except ImportError:
        logger.error(
            "Playwright is not installed.  Install it with:\n"
            "    pip install playwright && playwright install"
        )
        sys.exit(3)

    logger.info("Rendering page with Playwright: %s", url)
    selector_css = ", ".join(CONTENT_SELECTORS)
    timeout_ms = timeout * 1000

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_extra_http_headers(_build_headers())
            try:
                page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            except PWTimeout:
                logger.error("Page load timed out after %d s.", timeout)
                sys.exit(1)

            try:
                page.wait_for_selector(selector_css, timeout=5000)
                text = page.inner_text(selector_css)
                logger.debug("Playwright matched selector(s): %s", selector_css)
            except PWTimeout:
                logger.warning(
                    "Content selector not found after JS render; "
                    "falling back to full page text."
                )
                text = page.inner_text("body")
        finally:
            browser.close()

    return text.strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    args = _parse_args(argv)

    # --- Step 1: try plain HTTP GET ---
    text = fetch_with_requests(args.url, args.timeout)

    # --- Step 2: fall back to Playwright when requested ---
    if not text:
        if args.render:
            logger.info(
                "Plain HTTP fetch yielded no content; "
                "switching to Playwright render."
            )
            text = fetch_with_playwright(args.url, args.timeout)
        else:
            logger.warning(
                "No content matched expected selectors. "
                "Try --render to enable headless-browser rendering."
            )

    if not text:
        logger.error("Could not extract any content from the page.")
        sys.exit(2)

    # --- Step 3: emit output ---
    if args.output:
        logger.info("Writing output to: %s", args.output)
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        # When no output file is given, print the first 1 000 characters.
        print(text[:1000])

    logger.info("Done.")


if __name__ == "__main__":
    main()
