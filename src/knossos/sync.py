# knossos/sync.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import httpx


@dataclass
class SyncedProgress:
    chapter_index: int
    scroll_y: float
    updated_at: str


def _now_iso() -> str:
    """Current UTC time as an ISO 8601 string, matching the format the
    sync server compares lexicographically for recency."""
    return datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None).isoformat()


async def push_progress(
    server_url: str,
    identifier: str,
    title: str,
    chapter_index: int,
    scroll_y: float,
    timeout: float = 5.0,
) -> SyncedProgress | None:
    """
    Push this book's current progress to the sync server. Returns the
    server's authoritative resulting state (which may differ from what
    was pushed, if the server already had something newer). Returns None
    on any failure — network issues should never block normal reading,
    so callers should treat a failed sync as "just continue locally."
    """
    payload = {
        "identifier": identifier,
        "title": title,
        "chapter_index": chapter_index,
        "scroll_y": scroll_y,
        "updated_at": _now_iso(),
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{server_url}/sync/progress", json=payload, timeout=timeout)
    except httpx.RequestError:
        return None

    if response.status_code != 200:
        return None

    try:
        data = response.json()
    except ValueError:
        return None

    return SyncedProgress(
        chapter_index=data["chapter_index"],
        scroll_y=data["scroll_y"],
        updated_at=data["updated_at"],
    )


async def pull_progress(server_url: str, identifier: str, timeout: float = 5.0) -> SyncedProgress | None:
    """
    Fetch this book's synced progress from the server, if any exists.
    Returns None on any failure (network issue, or the server genuinely
    has no record for this book yet) — same "fail silently, keep reading"
    principle as push_progress.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{server_url}/sync/progress/{identifier}", timeout=timeout)
    except httpx.RequestError:
        return None

    if response.status_code != 200:
        return None

    try:
        data = response.json()
    except ValueError:
        return None

    return SyncedProgress(
        chapter_index=data["chapter_index"],
        scroll_y=data["scroll_y"],
        updated_at=data["updated_at"],
    )
