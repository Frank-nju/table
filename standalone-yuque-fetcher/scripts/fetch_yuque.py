#!/usr/bin/env python3
"""
fetch_yuque.py

抓取公开语雀文档正文。优先使用 requests + BeautifulSoup。
当页面通过 JS 动态渲染且未找到常见选择器时，可通过 --render 启用 Playwright 渲染（可选）。

兼容 Python 3.8+

Usage:
    python3 fetch_yuque.py                          # 抓取默认 URL，打印前 1000 字符
    python3 fetch_yuque.py --url <URL>              # 抓取指定 URL
    python3 fetch_yuque.py --render                 # 使用 Playwright 渲染（需要额外安装）
    python3 fetch_yuque.py --output result.txt      # 输出到文件
    python3 fetch_yuque.py --timeout 30 --verbose   # 设置超时 + 详细日志
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup

DEFAULT_URL = "https://nova.yuque.com/wg5tth/nuumlq/ky1ofwicugp9f5hq?singleDoc"
COMMON_SELECTORS = ["article", ".yuque-markdown", ".doc-content"]

logger = logging.getLogger("fetch_yuque")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fetch public Yuque document content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--url", "-u",
        default=DEFAULT_URL,
        help="Document URL to fetch (default: built-in example link)",
    )
    p.add_argument(
        "--render", "-r",
        action="store_true",
        help="Use headless browser rendering via Playwright (optional dependency)",
    )
    p.add_argument(
        "--output", "-o",
        default=None,
        help="Output file path (default: stdout)",
    )
    p.add_argument(
        "--timeout", "-t",
        type=int,
        default=15,
        help="Request/rendering timeout in seconds (default: 15)",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose/debug logging",
    )
    return p.parse_args()


def try_requests_extract(
    url: str, timeout: int
) -> Tuple[Optional[str], Optional[str]]:
    """Use requests + BeautifulSoup to fetch and parse the page.

    Returns (html_fragment, plain_text) or (None, None) if no selector matched.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; yuque-fetcher/1.0)",
        "Referer": "https://nova.yuque.com/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    logger.debug("GET %s (timeout=%ds)", url, timeout)
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    logger.debug("Response status %s, content-length %d", resp.status_code, len(resp.content))

    soup = BeautifulSoup(resp.text, "html.parser")
    for sel in COMMON_SELECTORS:
        el = soup.select_one(sel)
        if el:
            logger.debug("Matched selector: %s", sel)
            return el.decode_contents(), el.get_text(separator="\n").strip()

    logger.debug("No selector matched: %s", COMMON_SELECTORS)
    return None, None


def try_playwright_extract(
    url: str, timeout: int
) -> Tuple[str, str]:
    """Use Playwright (headless Chromium) to render the page and extract text.

    Returns (html_fragment, plain_text).
    Raises ImportError with a friendly message if Playwright is not installed.
    """
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        msg = (
            "Playwright is not installed. "
            "Install it with:\n"
            "  pip install playwright\n"
            "  playwright install\n"
            "Then retry with --render."
        )
        logger.error(msg)
        raise ImportError(msg)

    logger.debug("Launching headless Chromium via Playwright (timeout=%ds)", timeout)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=timeout * 1000)

        for sel in COMMON_SELECTORS:
            try:
                el = page.query_selector(sel)
                if el:
                    html = el.inner_html()
                    text = el.inner_text()
                    logger.debug("Matched selector: %s", sel)
                    browser.close()
                    return html, text
            except Exception:
                continue

        logger.debug("No selector matched; falling back to full page content")
        content = page.content()
        browser.close()
        return content, ""


def write_output(text: str, output_path: Optional[str]) -> int:
    """Write *text* to *output_path* or stdout.  Returns exit code."""
    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
            logger.info("Saved output to %s", output_path)
        except OSError as exc:
            logger.error("写文件失败: %s", exc)
            return 4
    else:
        print(text)
    return 0


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    logger.info("Fetching %s", args.url)

    # --- Step 1: try requests + BS4 ---
    html: Optional[str] = None
    text: Optional[str] = None
    try:
        html, text = try_requests_extract(args.url, args.timeout)
    except Exception as exc:
        logger.warning("requests fetch 失败: %s", exc)

    # --- Step 2: fall back to Playwright if requested and needed ---
    if not html and args.render:
        logger.info("未通过 requests 找到正文，尝试 Playwright 渲染（--render 已指定）")
        try:
            html, text = try_playwright_extract(args.url, args.timeout)
        except ImportError:
            return 2
        except Exception as exc:
            logger.error("Playwright 渲染失败: %s", exc)
            return 2

    if not html:
        logger.error(
            "未能提取正文（未匹配常见选择器）。"
            "如果页面需要 JS 渲染，请使用 --render 参数。"
        )
        return 3

    # Use plain text when available; fall back to html fragment
    output_str = text if text else html

    # When run with no arguments (quick self-check mode), truncate to 1000 chars
    is_default_run = (args.url == DEFAULT_URL and not args.render and args.output is None)
    if is_default_run and len(sys.argv) == 1:
        output_str = output_str[:1000]

    return write_output(output_str, args.output)


if __name__ == "__main__":
    try:
        rc = main()
    except KeyboardInterrupt:
        rc = 130
    sys.exit(rc)
