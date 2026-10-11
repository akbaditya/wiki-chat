import hashlib
import json
import os
import time

from app.config import settings


class PageCache:
    """Wikipedia page cache on disk (JSON per page) with TTL."""

    def __init__(self) -> None:
        self.dir = settings.wiki_cache_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ttl = settings.wiki_cache_ttl_days * 86400
        self.hits = 0
        self.misses = 0

    def _path(self, title: str):
        h = hashlib.sha1(title.strip().lower().encode()).hexdigest()[:20]
        return self.dir / f"{h}.json"

    def get(self, title: str) -> dict | None:
        try:
            data = json.loads(self._path(title).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            self.misses += 1
            return None
        if time.time() - data.get("fetched_at", 0) > self.ttl:
            self.misses += 1
            return None
        self.hits += 1
        return data

    def set(self, title: str, data: dict) -> None:
        path = self._path(title)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, path)  

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {"hits": self.hits, "misses": self.misses,
                "hit_rate": round(self.hits / total, 3) if total else 0.0}
    
    def cleanup(self, max_bytes: int) -> dict:
        """Deletes expired files, stale temp files, then the oldest files above the size cap.
        The file's modified time is the fetch time (reads never touch it)."""
        now = time.time()
        files, removed = [], 0

        def rm(path) -> bool:
            try:
                path.unlink(missing_ok=True)
                return True
            except OSError:  
                return False

        for p in self.dir.iterdir():
            try:
                st = p.stat()
            except OSError:
                continue
            if p.suffix == ".tmp":
                if now - st.st_mtime > 3600 and rm(p):
                    removed += 1
            elif p.suffix == ".json":
                if now - st.st_mtime > self.ttl:  
                    removed += rm(p)
                else:
                    files.append((st.st_mtime, st.st_size, p))

        total = sum(size for _, size, _ in files)
        for _, size, p in sorted(files):  
            if total <= max_bytes:
                break
            if rm(p):
                total -= size
                removed += 1
        return {"removed": removed, "kept_mb": round(total / 1e6, 1)}


class TTLCache:
    """Tiny in-memory cache for Wikipedia search results."""

    def __init__(self, ttl_seconds: int = 3600, max_items: int = 500) -> None:
        self.ttl = ttl_seconds
        self.max = max_items
        self._d: dict[str, tuple[float, object]] = {}

    def get(self, key: str):
        item = self._d.get(key)
        if item and item[0] > time.time():
            return item[1]
        self._d.pop(key, None)
        return None

    def set(self, key: str, value) -> None:
        if len(self._d) >= self.max:
            self._d.clear()
        self._d[key] = (time.time() + self.ttl, value)


page_cache = PageCache()
search_cache = TTLCache()
file_cache = TTLCache(ttl_seconds=86400, max_items=2000)   
