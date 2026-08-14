"""
Browser Automation (Playwright-based).

Turns natural-language browser intents into real browser actions — the
"Jarvis posts on Instagram" capability from the target demos. Playwright
is imported lazily and installed via ``pip install playwright &&
playwright install chromium`` (handled by setup_jarvis.ps1 when you opt in).

All functions are side-effecting by design (they move a real browser) so
they are called from the intent router only on explicit keyword matches.

Design notes:
- A single re-used Chromium instance (persistent context) keeps login
  sessions — so "post to Instagram" works because you stay logged in.
- Actions return a plain-English result string for speaking/logging.
- Failures never raise — they return a spoken-safe error message.
"""
from dataclasses import dataclass
from typing import Optional

BROWSER_RUNNING: Optional[object] = None  # persistent browser handle
CONTEXT = None


@dataclass
class ActionResult:
    ok: bool
    message: str


def _get_browser(headless: bool = False):
    """Lazily create a persistent-context Chromium so logins survive restarts."""
    global BROWSER_RUNNING, CONTEXT
    from playwright.sync_api import sync_playwright

    if BROWSER_RUNNING is None:
        pw = sync_playwright().start()
        profile = (
            __import__("pathlib").Path(__file__).resolve().parent.parent.parent
            / "02_build_cache" / "browser_profile"
        )
        profile.mkdir(parents=True, exist_ok=True)
        CONTEXT = pw.chromium.launch_persistent_context(
            str(profile),
            headless=headless,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"],
        )
        BROWSER_RUNNING = pw

    page = CONTEXT.pages[0] if CONTEXT.pages else CONTEXT.new_page()
    return page


def _browser_result(message: str, ok: bool = True) -> ActionResult:
    return ActionResult(ok=ok, message=message)


def open_url(url: str, wait: str = "domcontentloaded") -> ActionResult:
    try:
        page = _get_browser()
        page.goto(url, wait_until=wait, timeout=30000)
        return _browser_result(f"Opened {url}. Page title: {page.title()[:80]}.")
    except Exception as e:
        return _browser_result(f"Couldn't open {url}: {e}", ok=False)


def navigate_to_site(site: str) -> ActionResult:
    """Resolve common site nicknames ('instagram', 'youtube', 'gmail')."""
    site = site.lower().strip()
    known = {
        "instagram": "https://www.instagram.com/",
        "youtube": "https://www.youtube.com/",
        "gmail": "https://mail.google.com/",
        "google": "https://www.google.com/",
        "twitter": "https://x.com/",
        "x": "https://x.com/",
        "reddit": "https://www.reddit.com/",
        "github": "https://github.com/",
    }
    url = known.get(site)
    if not url:
        if site.startswith("http"):
            url = site
        else:
            url = f"https://www.google.com/search?q={__import__('urllib.parse').quote(site)}"
    return open_url(url)


def click(selector: str) -> ActionResult:
    try:
        page = _get_browser()
        page.click(selector, timeout=15000)
        return _browser_result(f"Clicked {selector}.")
    except Exception as e:
        return _browser_result(f"Couldn't click {selector}: {e}", ok=False)


def fill(selector: str, text: str) -> ActionResult:
    try:
        page = _get_browser()
        page.fill(selector, text, timeout=15000)
        return _browser_result(f"Typed '{text[:40]}...' into {selector}.")
    except Exception as e:
        return _browser_result(f"Couldn't fill {selector}: {e}", ok=False)


def page_screenshot(path: str) -> ActionResult:
    try:
        page = _get_browser()
        page.screenshot(path=path)
        return _browser_result(f"Screenshot saved to {path}.")
    except Exception as e:
        return _browser_result(f"Screenshot failed: {e}", ok=False)


def close_browser() -> ActionResult:
    global BROWSER_RUNNING, CONTEXT
    try:
        if CONTEXT is not None:
            CONTEXT.close()
            CONTEXT = None
        if BROWSER_RUNNING is not None:
            BROWSER_RUNNING.stop()
            BROWSER_RUNNING = None
        return _browser_result("Browser session closed.")
    except Exception as e:
        return _browser_result(f"Browser close failed: {e}", ok=False)
