"""One browser helper for the download scripts: Playwright (Apache-2.0), sync API.

WHY THIS MODULE EXISTS
----------------------
Until 21 Oct 2026 seventeen scripts drove Chrome through ``undetected-chromedriver``
(GPL-3.0) and Selenium. The repository's code is Apache-2.0, so that library was
removed and the scripts now drive Chromium through Playwright via this module.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
undetected-chromedriver existed to hide automation from bot detection
(Cloudflare and similar). This module does not replace that: it launches a
normal Playwright browser with Playwright's own, truthful user agent, adds no
stealth patches, and drops evasion flags such as
``--disable-blink-features=AutomationControlled``. A site that blocks automated
browsers will block these scripts; such papers must be fetched by hand or
through an approved route (library proxy, publisher API, interlibrary loan).

SHAPE
-----
``launch_driver()`` returns a ``Driver`` whose methods mirror the small part of
Selenium's WebDriver the scripts used (``get``, ``current_url``, ``title``,
``page_source``, ``find_element(s)``, ``execute_script``, ``get_cookies``,
``quit`` ...), so each port keeps its own logic, waits, and outputs. Waits that
were ``WebDriverWait(...).until(EC.presence_of_element_located(...))`` become
``driver.wait_for(By.X, value, timeout)``.

Downloads: Selenium scripts set Chrome's ``download.default_directory`` and
polled it. Playwright delivers downloads as events, which are only processed
while Playwright is running, so a plain ``time.sleep`` loop never sees the file.
Use ``driver.sleep(s)`` in place of ``time.sleep`` while a download may be
arriving, or ``driver.wait_for_download(timeout)``. Every download (and every
PDF that opens in the browser's viewer, mirroring Chrome's
``plugins.always_open_pdf_externally``) is saved into the download directory
under its suggested filename, so directory-polling code keeps working.

Playwright is NOT installed on this machine as of 21 Oct 2026. Before any of
these scripts can run:  ``pip install playwright`` (in an approved environment)
then ``python -m playwright install chromium``.
"""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Iterable, Optional

INSTALL_HINT = ("Playwright is not installed. Install it (with approval) with "
                "`pip install playwright` and then `python -m playwright install chromium`.")


class BrowserError(RuntimeError):
    """A browser operation failed (Selenium: WebDriverException)."""


class BrowserTimeout(BrowserError):
    """A navigation or wait timed out (Selenium: TimeoutException)."""


class NoSuchElement(BrowserError):
    """find_element found nothing (Selenium: NoSuchElementException)."""


# Names the ported scripts can keep in their except clauses.
TimeoutException = BrowserTimeout
WebDriverException = BrowserError
NoSuchElementException = NoSuchElement


def playwright_available() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
        return True
    except ImportError:
        return False


class By:
    """Selenium locator strategies, translated to Playwright selectors."""
    XPATH = "xpath"
    CSS_SELECTOR = "css selector"
    TAG_NAME = "tag name"
    NAME = "name"
    ID = "id"
    CLASS_NAME = "class name"
    LINK_TEXT = "link text"
    PARTIAL_LINK_TEXT = "partial link text"


def _xpath_literal(s: str) -> str:
    if "'" not in s:
        return f"'{s}'"
    if '"' not in s:
        return f'"{s}"'
    return "concat(" + ", \"'\", ".join(f"'{p}'" for p in s.split("'")) + ")"


def _css_attr(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def to_selector(by: str, value: str) -> str:
    """Selenium (by, value) -> Playwright selector string."""
    if by == By.XPATH:
        return "xpath=" + value
    if by in (By.CSS_SELECTOR, By.TAG_NAME):
        return "css=" + value
    if by == By.NAME:
        return f'css=[name="{_css_attr(value)}"]'
    if by == By.ID:
        return f'css=[id="{_css_attr(value)}"]'
    if by == By.CLASS_NAME:
        return "css=." + value.strip().replace(" ", ".")
    if by == By.LINK_TEXT:
        return f"xpath=//a[normalize-space(.)={_xpath_literal(value.strip())}]"
    if by == By.PARTIAL_LINK_TEXT:
        return f"xpath=//a[contains(normalize-space(.), {_xpath_literal(value.strip())})]"
    raise ValueError(f"unknown locator strategy {by!r}")


def _wrap_error(e: Exception) -> BrowserError:
    name = type(e).__name__
    if name == "TimeoutError":
        return BrowserTimeout(str(e))
    return BrowserError(f"{name}: {e}")


_SAFE = re.compile(r"[^A-Za-z0-9._ ()+-]")


def _unique(path: Path) -> Path:
    if not path.exists():
        return path
    for i in range(1, 10000):
        cand = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not cand.exists():
            return cand
    raise BrowserError(f"no free filename for {path}")


class Element:
    """A Selenium-WebElement-like wrapper over a Playwright ElementHandle."""

    def __init__(self, handle, driver: "Driver"):
        self._h = handle
        self._driver = driver

    def get_attribute(self, name: str) -> Optional[str]:
        """Property first, then attribute, as Selenium does (so ``href`` is absolute)."""
        try:
            v = self._h.evaluate(
                "(el, n) => { const p = el[n];"
                " if (typeof p === 'string' || typeof p === 'number') return String(p);"
                " if (typeof p === 'boolean') return p ? 'true' : null;"
                " return el.getAttribute(n); }", name)
        except Exception as e:  # noqa: BLE001
            raise _wrap_error(e) from e
        return v

    @property
    def text(self) -> str:
        try:
            return self._h.inner_text()
        except Exception:  # noqa: BLE001 - not rendered: Selenium returns ""
            return ""

    @property
    def tag_name(self) -> str:
        return self._h.evaluate("el => el.tagName.toLowerCase()")

    def is_displayed(self) -> bool:
        return self._h.is_visible()

    def click(self) -> None:
        try:
            self._h.click()
        except Exception as e:  # noqa: BLE001
            raise _wrap_error(e) from e
        self._driver._pump(0)

    def find_elements(self, by: str, value: str) -> list["Element"]:
        return [Element(h, self._driver) for h in self._h.query_selector_all(to_selector(by, value))]

    def find_element(self, by: str, value: str) -> "Element":
        h = self._h.query_selector(to_selector(by, value))
        if h is None:
            raise NoSuchElement(f"no element for {by}={value!r}")
        return Element(h, self._driver)


class _SwitchTo:
    def __init__(self, driver: "Driver"):
        self._d = driver

    def window(self, handle: str) -> None:
        for p in self._d.context.pages:
            if self._d._handle_of(p) == handle:
                self._d.page = p
                p.bring_to_front()
                return
        raise BrowserError(f"no window {handle}")


class Driver:
    """A Playwright browser context exposed through a Selenium-like surface.

    ``page`` and ``context`` are the raw Playwright objects, for anything the
    wrapper does not cover."""

    def __init__(self, pw, browser, context, page_load_timeout: float, download_dir: Optional[Path],
                 save_viewer_pdfs: bool):
        self._pw = pw
        self._browser = browser
        self.context = context
        self.page = context.pages[0] if context.pages else context.new_page()
        self._timeout_ms = int(page_load_timeout * 1000)
        self.download_dir = Path(download_dir) if download_dir else None
        self.save_viewer_pdfs = save_viewer_pdfs
        self.downloads: list[Path] = []      # every file saved, in order
        self._pending: list = []
        self._handles: dict[int, str] = {}
        self.switch_to = _SwitchTo(self)
        context.on("page", self._watch)
        for p in context.pages:
            self._watch(p)

    # --- internals ---------------------------------------------------------
    def _watch(self, page) -> None:
        # A plain function, not list.append: Playwright tags its handlers with an attribute, which a
        # built-in method can't carry (AttributeError on the first live run, 22 Oct 2026).
        page.on("download", lambda d: self._pending.append(d))

    def _handle_of(self, page) -> str:
        return self._handles.setdefault(id(page), f"pw-{len(self._handles)}")

    def _save_download(self, d) -> Optional[Path]:
        if self.download_dir is None:
            return None
        self.download_dir.mkdir(parents=True, exist_ok=True)
        name = _SAFE.sub("_", d.suggested_filename or "download") or "download"
        dest = _unique(self.download_dir / name)
        d.save_as(str(dest))  # blocks until the download has finished
        self.downloads.append(dest)
        return dest

    def _pump(self, ms: int) -> None:
        """Let Playwright process events for ``ms`` ms, then save finished downloads."""
        if ms > 0:
            try:
                self.page.wait_for_timeout(ms)
            except Exception:  # noqa: BLE001 - page closed mid-wait
                time.sleep(ms / 1000)
        while self._pending:
            d = self._pending.pop(0)
            try:
                self._save_download(d)
            except Exception:  # noqa: BLE001 - a failed download leaves no file, as in Chrome
                pass

    # --- Selenium-like surface ---------------------------------------------
    def get(self, url: str) -> None:
        """Navigate and wait for the load event. A URL that turns into a download
        (or a PDF shown in the viewer, when save_viewer_pdfs) is saved to download_dir."""
        try:
            resp = self.page.goto(url, timeout=self._timeout_ms, wait_until="load")
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if "Download is starting" in msg or "net::ERR_ABORTED" in msg:
                self._pump(500)
                return
            raise _wrap_error(e) from e
        if (resp is not None and self.save_viewer_pdfs and self.download_dir is not None
                and "application/pdf" in (resp.headers.get("content-type") or "").lower()):
            try:
                body = resp.body()
                self.download_dir.mkdir(parents=True, exist_ok=True)
                name = _SAFE.sub("_", Path(resp.url.split("?")[0]).name or "document.pdf")
                if not name.lower().endswith(".pdf"):
                    name += ".pdf"
                dest = _unique(self.download_dir / name)
                dest.write_bytes(body)
                self.downloads.append(dest)
            except Exception:  # noqa: BLE001 - viewer body unavailable; nothing saved
                pass
        self._pump(0)

    def set_page_load_timeout(self, seconds: float) -> None:
        self._timeout_ms = int(seconds * 1000)

    def set_download_dir(self, path) -> None:
        """Replaces CDP ``Page.setDownloadBehavior``: later downloads go to ``path``."""
        self.download_dir = Path(path)

    @property
    def current_url(self) -> str:
        return self.page.url

    @property
    def title(self) -> str:
        return self.page.title()

    @property
    def page_source(self) -> str:
        return self.page.content()

    @property
    def user_agent(self) -> str:
        return self.page.evaluate("() => navigator.userAgent")

    def find_elements(self, by: str, value: str) -> list[Element]:
        try:
            return [Element(h, self) for h in self.page.query_selector_all(to_selector(by, value))]
        except Exception as e:  # noqa: BLE001
            raise _wrap_error(e) from e

    def find_element(self, by: str, value: str) -> Element:
        h = self.page.query_selector(to_selector(by, value))
        if h is None:
            raise NoSuchElement(f"no element for {by}={value!r}")
        return Element(h, self)

    def wait_for(self, by: str, value: str, timeout: float = 30, clickable: bool = False) -> Element:
        """WebDriverWait + EC.presence_of_element_located (or element_to_be_clickable)."""
        try:
            h = self.page.wait_for_selector(to_selector(by, value),
                                            state="visible" if clickable else "attached",
                                            timeout=int(timeout * 1000))
        except Exception as e:  # noqa: BLE001
            raise _wrap_error(e) from e
        if clickable and not h.is_enabled():
            raise BrowserTimeout(f"{by}={value!r} present but not enabled")
        return Element(h, self)

    def execute_script(self, script: str, *args: Any) -> Any:
        """Selenium-style script body: may ``return`` and read ``arguments[i]``."""
        args = [a._h if isinstance(a, Element) else a for a in args]
        try:
            out = self.page.evaluate(
                "(a) => (function() { " + script + "\n}).apply(null, a)", args)
        except Exception as e:  # noqa: BLE001
            raise _wrap_error(e) from e
        self._pump(0)
        return out

    def get_cookies(self) -> list[dict]:
        """Selenium-format cookies (name, value, domain, path, secure, httpOnly, expiry)."""
        out = []
        for c in self.context.cookies():
            d = {k: c[k] for k in ("name", "value", "domain", "path", "secure", "httpOnly") if k in c}
            if c.get("expires", -1) and c.get("expires", -1) > 0:
                d["expiry"] = int(c["expires"])
            out.append(d)
        return out

    def add_cookie(self, cookie: dict) -> None:
        c = {k: cookie[k] for k in ("name", "value", "domain", "path", "secure", "httpOnly") if k in cookie}
        if "expiry" in cookie:
            c["expires"] = cookie["expiry"]
        if "domain" not in c:
            c["url"] = self.page.url
        self.context.add_cookies([c])

    def requests_session(self, session=None):
        """A requests.Session carrying this browser's cookies and its own user agent."""
        import requests
        s = session or requests.Session()
        for c in self.get_cookies():
            s.cookies.set(c["name"], c["value"], domain=c.get("domain"), path=c.get("path", "/"))
        s.headers["User-Agent"] = self.user_agent
        return s

    def fetch(self, url: str, timeout: float = 60, headers: Optional[dict] = None):
        """GET through the browser context (shares its cookies).
        Returns (status, content_type, body_bytes)."""
        try:
            r = self.context.request.get(url, timeout=int(timeout * 1000), headers=headers)
            return r.status, (r.headers.get("content-type") or ""), r.body()
        except Exception as e:  # noqa: BLE001
            raise _wrap_error(e) from e

    def sleep(self, seconds: float) -> None:
        """time.sleep that keeps Playwright's events, and so downloads, flowing."""
        self._pump(int(seconds * 1000))

    def wait_for_download(self, timeout: float = 60, since: Optional[int] = None) -> Optional[Path]:
        """The first file saved after index ``since`` (default: now), or None on timeout."""
        start = len(self.downloads) if since is None else since
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self._pump(250)
            if len(self.downloads) > start:
                return self.downloads[start]
        return None

    @property
    def window_handles(self) -> list[str]:
        return [self._handle_of(p) for p in self.context.pages]

    def close(self) -> None:
        """Close the current tab (Selenium semantics); the browser stays open."""
        try:
            self.page.close()
        finally:
            pages = self.context.pages
            if pages:
                self.page = pages[0]

    def quit(self) -> None:
        for closer in (self.context.close, getattr(self._browser, "close", None), self._pw.stop):
            if closer is None:
                continue
            try:
                closer()
            except Exception:  # noqa: BLE001
                pass

    def __enter__(self) -> "Driver":
        return self

    def __exit__(self, *exc) -> None:
        self.quit()


def launch_driver(headless: bool = True,
                  window_size: tuple[int, int] = (1920, 1080),
                  download_dir=None,
                  user_data_dir=None,
                  profile_directory: Optional[str] = None,
                  channel: Optional[str] = None,
                  page_load_timeout: float = 60,
                  save_viewer_pdfs: bool = True,
                  extra_args: Iterable[str] = ()) -> Driver:
    """Start Chromium (or ``channel="chrome"`` for installed Google Chrome) and return a Driver.

    ``user_data_dir`` (+ ``profile_directory``) reuses a persistent profile, as the
    Selenium scripts' ``--user-data-dir`` did; the profile must not be open in
    another browser. No stealth options are applied (see module docstring)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise BrowserError(INSTALL_HINT) from e
    pw = sync_playwright().start()
    args = list(extra_args)
    if profile_directory:
        args.append(f"--profile-directory={profile_directory}")
    viewport = {"width": int(window_size[0]), "height": int(window_size[1])}
    try:
        if user_data_dir:
            Path(user_data_dir).mkdir(parents=True, exist_ok=True)
            context = pw.chromium.launch_persistent_context(
                str(user_data_dir), headless=headless, channel=channel, args=args,
                accept_downloads=True, viewport=viewport)
            browser = None
        else:
            browser = pw.chromium.launch(headless=headless, channel=channel, args=args)
            context = browser.new_context(accept_downloads=True, viewport=viewport)
    except Exception as e:  # noqa: BLE001
        pw.stop()
        raise _wrap_error(e) from e
    return Driver(pw, browser, context, page_load_timeout, download_dir, save_viewer_pdfs)
