import asyncio
import re
import time
from html.parser import HTMLParser
from urllib.parse import unquote

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import settings
from app.services.cache import file_cache, page_cache, search_cache

API_URL = "https://en.wikipedia.org/w/api.php"  
MAX_EXTRACT_CHARS = 200_000  
PAGE_VERSION = 2            
_TAGS = re.compile(r"<[^>]+>")
_FILE_HREF = re.compile(r"(?:/wiki/|\./)(File:[^?#]+)")
_CITE = re.compile(r"\[\s*\d+\s*\]")
_CAPTION_CLASSES = ("infobox-caption", "gallerytext", "thumbcaption")


class WikipediaError(Exception): ...


def _retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return False


def _clean(html: str | None) -> str:
    return re.sub(r"\s+", " ", _TAGS.sub("", html or "")).strip()


class _FigureParser(HTMLParser):
    """Collects every article image with its caption, in the order it appears on the page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.items: list[dict] = []
        self._file: str | None = None
        self._last: dict | None = None
        self._cap_kind: str | None = None  
        self._cap_depth = 0
        self._cap_parts: list[str] = []
        self._cap_target: dict | None = None

    @staticmethod
    def _url(value: str) -> str:
        value = value.strip()
        return "https:" + value if value.startswith("//") else value

    def _start_caption(self, kind: str) -> None:
        self._cap_kind, self._cap_depth, self._cap_parts = kind, 1, []
        self._cap_target = self._last if self._last and not self._last["caption"] else None

    def _end_caption(self) -> None:
        text = re.sub(r"\s+", " ", _CITE.sub("", " ".join(self._cap_parts))).strip()
        if self._cap_target is not None and text:
            self._cap_target["caption"] = text[:300]
        self._cap_kind = None
        self._cap_target = None

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        cls = a.get("class", "")
        if self._cap_kind is not None:
            if tag == "div" and self._cap_kind == "div":
                self._cap_depth += 1
            return
        if tag == "a":
            m = _FILE_HREF.search(a.get("href", ""))
            if m:
                self._file = unquote(m.group(1)).replace("_", " ")
        elif tag == "img" and "mw-file-element" in cls:
            src = a.get("src", "")
            if a.get("srcset"):  
                src = re.split(r",\s+", a["srcset"].strip())[-1].split()[0]
            if self._file and src:
                try:
                    w, h = int(a.get("width") or 0), int(a.get("height") or 0)
                except ValueError:
                    w = h = 0
                item = {"file_title": self._file, "thumb_url": self._url(src),
                        "width": w, "height": h, "alt": a.get("alt", "")[:200], "caption": ""}
                self.items.append(item)
                self._last = item
            self._file = None
        elif tag == "figcaption":
            self._start_caption("figcaption")
        elif tag == "div" and any(c in cls for c in _CAPTION_CLASSES):
            self._start_caption("div")

    def handle_endtag(self, tag):
        if self._cap_kind == "figcaption" and tag == "figcaption":
            self._end_caption()
        elif self._cap_kind == "div" and tag == "div":
            self._cap_depth -= 1
            if self._cap_depth == 0:
                self._end_caption()

    def handle_data(self, data):
        if self._cap_kind is not None:
            self._cap_parts.append(data)


def parse_figures(html_text: str) -> list[dict]:
    parser = _FigureParser()
    parser.feed(html_text)
    parser.close()
    seen: set[str] = set()
    out: list[dict] = []
    for it in parser.items:
        if it["file_title"] in seen:
            continue
        seen.add(it["file_title"])
        it["position"] = len(out) 
        out.append(it)
    return out


class WikipediaClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=5.0),
            headers={"User-Agent": settings.wiki_user_agent},
        )
        self._sem = asyncio.Semaphore(4)  

    async def aclose(self) -> None:
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=4),
        retry=retry_if_exception(_retryable),
        reraise=True,
    )
    async def _get(self, params: dict) -> dict:
        async with self._sem:
            r = await self._client.get(
                API_URL, params={**params, "format": "json", "formatversion": "2"}
            )
        r.raise_for_status()
        return r.json()

    async def search_titles(self, query: str, limit: int = 6) -> list[str]:
        key = f"{limit}:{query.strip().lower()}"
        cached = search_cache.get(key)
        if cached is not None:
            return cached
        try:
            data = await self._get({
                "action": "query", "list": "search", "srsearch": query,
                "srlimit": limit, "srnamespace": 0,
            })
        except (httpx.HTTPError, ValueError) as e:
            raise WikipediaError(f"search failed: {e}") from e
        titles = [r["title"] for r in data.get("query", {}).get("search", [])]
        search_cache.set(key, titles)
        return titles

    async def _fetch_page(self, title: str) -> dict | None:
        data = await self._get({
            "action": "query", "prop": "extracts|pageprops|revisions",
            "titles": title, "redirects": 1, "explaintext": 1,
            "ppprop": "disambiguation", "rvprop": "ids",
        })
        pages = data.get("query", {}).get("pages", [])
        if not pages or pages[0].get("missing"):
            return None
        p = pages[0]
        canonical = p["title"]
        return {
            "title": canonical,
            "url": "https://en.wikipedia.org/wiki/" + canonical.replace(" ", "_"),
            "revision_id": str((p.get("revisions") or [{}])[0].get("revid", "0")),
            "is_disambiguation": "disambiguation" in (p.get("pageprops") or {}),
            "extract": (p.get("extract") or "")[:MAX_EXTRACT_CHARS],
        }

    async def _fetch_figures(self, title: str) -> list[dict]:
        """Images of the article in reading order, each with its real caption."""
        data = await self._get({
            "action": "parse", "page": title, "prop": "text", "redirects": 1,
            "disableeditsection": 1, "disabletoc": 1, "disablelimitreport": 1,
        })
        html_text = (data.get("parse") or {}).get("text") or ""
        if not isinstance(html_text, str) or not html_text:
            return []
        return await asyncio.to_thread(parse_figures, html_text)

    async def file_details(self, file_titles: list[str]) -> dict[str, dict]:
        """Attribution (artist, license, source page) for the few images we actually show."""
        out: dict[str, dict] = {}
        missing: list[str] = []
        for t in file_titles:
            hit = file_cache.get(t)
            if hit is not None:
                out[t] = hit
            else:
                missing.append(t)
        if missing:
            try:
                data = await self._get({
                    "action": "query", "titles": "|".join(missing[:10]), "prop": "imageinfo",
                    "iiprop": "url|extmetadata",
                    "iiextmetadatafilter": "Artist|LicenseShortName", "redirects": 1,
                })
            except Exception:
                return out 
            for p in data.get("query", {}).get("pages", []):
                info = (p.get("imageinfo") or [None])[0]
                if not info:
                    continue
                meta = info.get("extmetadata") or {}
                d = {
                    "source_url": info.get("descriptionurl"),
                    "artist": _clean(meta.get("Artist", {}).get("value"))[:100],
                    "license": _clean(meta.get("LicenseShortName", {}).get("value"))[:50],
                }
                out[p["title"]] = d
                file_cache.set(p["title"], d)
        return out

    async def get_page(self, title: str) -> dict | None:
        """Cached page + images. Returns None if the page doesn't exist.
        Raises WikipediaError if Wikipedia is unreachable."""
        cached = page_cache.get(title)
        if cached and cached.get("v") == PAGE_VERSION:
            cached["from_cache"] = True
            return cached
        page, images = await asyncio.gather(
            self._fetch_page(title), self._fetch_figures(title), return_exceptions=True
        )
        if isinstance(page, BaseException):
            raise WikipediaError(f"fetch failed for '{title}': {page}") from page
        if page is None:
            return None
        if isinstance(images, BaseException): 
            images = []
        for im in images:
            im["page_title"] = page["title"]
        page["images"] = images
        page["v"] = PAGE_VERSION
        page["fetched_at"] = time.time()
        page_cache.set(title, page)
        page["from_cache"] = False
        return page


wiki = WikipediaClient()