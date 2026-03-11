#!/usr/bin/env python3
"""
fetch_yuque.py — 抓取语雀公开文档的正文内容

用法：
  python scripts/fetch_yuque.py                      # 自检模式：抓取默认链接并输出前 1000 字符
  python scripts/fetch_yuque.py --url <URL>          # 抓取指定链接
  python scripts/fetch_yuque.py --url <URL> --render # 使用 Playwright 渲染抓取
  python scripts/fetch_yuque.py --url <URL> --output result.html

Python 3.8+ 兼容
"""

import argparse
import logging
import sys
import textwrap

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

DEFAULT_URL = (
    "https://nova.yuque.com/wg5tth/nuumlq/ky1ofwicugp9f5hq?singleDoc"
)

CONTENT_SELECTORS = [
    "article",
    ".yuque-markdown",
    ".doc-content",
    ".lake-content",
    ".ne-viewer-body",
    "[data-testid='doc-body']",
    ".content",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://nova.yuque.com/",
}

# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 抓取函数
# ---------------------------------------------------------------------------


def fetch_with_requests(url: str, timeout: int):
    """使用 requests + BeautifulSoup 直接抓取并解析页面。

    返回 (content_html, content_text) 或 (None, None)（未匹配到选择器时）。
    """
    try:
        import requests  # noqa: PLC0415
        from bs4 import BeautifulSoup  # noqa: PLC0415
    except ImportError as exc:
        logger.error("缺少依赖：%s。请运行：pip install -r scripts/requirements.txt", exc)
        sys.exit(2)

    logger.info("使用 requests 直接抓取：%s", url)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        logger.error("请求超时（timeout=%ds）。可尝试 --timeout 增大超时时间。", timeout)
        sys.exit(1)
    except requests.exceptions.ConnectionError as exc:
        logger.error("网络连接失败：%s", exc)
        sys.exit(1)
    except requests.exceptions.HTTPError as exc:
        logger.error("HTTP 错误：%s", exc)
        sys.exit(1)

    soup = BeautifulSoup(resp.text, "html.parser")

    for selector in CONTENT_SELECTORS:
        element = soup.select_one(selector)
        if element:
            logger.info("使用选择器 '%s' 找到正文", selector)
            return element.decode_contents(), element.get_text(separator="\n").strip()

    logger.warning(
        "未能通过常见选择器（%s）找到正文，"
        "页面可能需要 JavaScript 渲染。可以尝试加 --render 参数。",
        ", ".join(CONTENT_SELECTORS),
    )
    return None, None


def fetch_with_playwright(url: str, timeout: int):
    """使用 Playwright 渲染页面后抓取正文。

    返回 (content_html, content_text)。
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError  # noqa: PLC0415
    except ImportError:
        logger.error(
            "未安装 Playwright。请先运行：\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        )
        sys.exit(2)

    logger.info("使用 Playwright 渲染抓取：%s", url)
    timeout_ms = timeout * 1000

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(extra_http_headers=HEADERS)
            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")

            matched_selector = None
            for sel in CONTENT_SELECTORS:
                try:
                    page.wait_for_selector(sel, timeout=5000)
                    matched_selector = sel
                    break
                except PlaywrightTimeoutError:
                    continue

            if matched_selector:
                logger.info("Playwright 使用选择器 '%s' 找到正文", matched_selector)
                content_html = page.inner_html(matched_selector)
                content_text = page.inner_text(matched_selector)
            else:
                logger.warning(
                    "Playwright 未匹配到任何选择器，返回完整页面 HTML。"
                )
                content_html = page.content()
                content_text = page.locator("body").inner_text()
        finally:
            browser.close()

    return content_html, content_text


# ---------------------------------------------------------------------------
# 主逻辑
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="抓取语雀公开文档正文内容",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            示例：
              # 自检（抓取默认链接，输出前 1000 字符）
              python scripts/fetch_yuque.py

              # 抓取指定链接
              python scripts/fetch_yuque.py --url https://nova.yuque.com/xxx/yyy/zzz?singleDoc

              # 强制使用 Playwright 渲染
              python scripts/fetch_yuque.py --url <URL> --render

              # 保存抓取结果到文件
              python scripts/fetch_yuque.py --url <URL> --output output.html
            """
        ),
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="要抓取的语雀公开文档 URL（默认：%(default)s）",
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="使用 Playwright 无头浏览器渲染后抓取（需要已安装 playwright）",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="将抓取到的 HTML 保存到指定文件（可选）",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        metavar="SECONDS",
        help="请求超时秒数（默认：%(default)s）",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="自检模式：抓取默认链接并输出前 1000 字符（无参数运行时自动触发）",
    )

    args = parser.parse_args()

    # 无参数运行时触发自检模式
    self_check = args.self_check or (len(sys.argv) == 1)

    # 抓取
    if args.render:
        content_html, content_text = fetch_with_playwright(args.url, args.timeout)
    else:
        content_html, content_text = fetch_with_requests(args.url, args.timeout)
        if content_html is None and not args.render:
            # 自动 fallback 到 Playwright（仅提示，不自动运行以避免隐式安装需求）
            logger.info("提示：若要用无头浏览器重试，请加 --render 参数。")
            sys.exit(1)

    # 输出
    if self_check:
        print("=== [自检] 正文前 1000 字符 ===")
        print((content_text or "")[:1000])
        print("=== [自检] HTML 前 500 字符 ===")
        print((content_html or "")[:500])
    else:
        print("=== 正文文本 ===")
        print(content_text or "")
        print("\n=== 正文 HTML ===")
        print(content_html or "")

    # 保存到文件
    if args.output and content_html:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(content_html)
            logger.info("HTML 已保存到：%s", args.output)
        except OSError as exc:
            logger.error("保存文件失败：%s", exc)
            sys.exit(1)

    if content_html is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
