# knossos/opds/cache.py

from __future__ import annotations

import hashlib
import time
from pathlib import Path

from knossos.config import Paths

DEFAULT_TTL_SECONDS = 15 * 60  # 15 minutes — long enough to avoid re-fetching
                                 # during normal back-and-forth browsing, short
                                 # enough that a library update shows up reasonably soon


def _cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _cache_path(paths: Paths, url: str) -> Path:
    cache_dir = paths.cache_dir / "opds_feeds"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{_cache_key(url)}.xml"


def get_cached_feed(paths: Paths, url: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str | None:
    """Return cached feed XML for this URL if it exists and hasn't expired,
    else None."""
    path = _cache_path(paths, url)
    if not path.exists():
        return None

    age = time.time() - path.stat().st_mtime
    if age > ttl_seconds:
        return None

    return path.read_text(encoding="utf-8")


def set_cached_feed(paths: Paths, url: str, xml_text: str) -> None:
    path = _cache_path(paths, url)
    path.write_text(xml_text, encoding="utf-8")
