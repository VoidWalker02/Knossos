# knossos/opds/client.py

from __future__ import annotations

import httpx


def fetch_feed(url: str, timeout: float = 10.0) -> str:
    """
    Fetch a raw OPDS feed (Atom+XML) from the given URL.

    Kept deliberately minimal for now: no auth, no retries, no caching.
    Those can layer on top once we know the basic fetch/parse path works.
    """
    response = httpx.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text

# knossos/opds/client.py (addition)

from pathlib import Path


def download_book(url: str, destination: Path, timeout: float = 30.0) -> Path:
    """
    Download a book from an OPDS acquisition link and save it to disk.
    Returns the path it was saved to.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)

    with httpx.stream("GET", url, timeout=timeout) as response:
        response.raise_for_status()
        with open(destination, "wb") as f:
            for chunk in response.iter_bytes():
                f.write(chunk)

    return destination
