"""Thread-safe, in-memory TTL cache with automatic eviction.

This module provides a lightweight caching layer suitable for metadata,
search results, and thumbnail data that does **not** require external
infrastructure (Redis, Memcached, etc.).

A module-level singleton :data:`cache` is exported for convenience::

    from app.core.cache import cache

    cache.set("key", value, ttl=300)
    cached = cache.get("key")

Thread Safety
-------------
All public methods acquire an internal :class:`threading.Lock` before
mutating the store, making the cache safe for use from multiple threads
(e.g. FastAPI background tasks, ThreadPoolExecutor workers).

Eviction Policy
---------------
When the cache reaches ``max_size``:

1. All expired entries are purged first.
2. If still at capacity, the oldest 25 % of entries (by expiry time)
   are evicted to make room.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

logger: logging.Logger = logging.getLogger(__name__)


class CacheEntry:
    """A single cached value with an absolute expiry timestamp.

    Attributes
    ----------
    value:
        The cached object (any Python value).
    expires_at:
        Monotonic timestamp after which this entry is considered stale.
    """

    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: float) -> None:
        """Initialise a cache entry.

        Parameters
        ----------
        value:
            The object to cache.
        ttl:
            Time-to-live in seconds from *now*.
        """
        self.value: Any = value
        self.expires_at: float = time.monotonic() + ttl

    @property
    def is_expired(self) -> bool:
        """Return ``True`` if this entry has exceeded its TTL."""
        return time.monotonic() >= self.expires_at


class Cache:
    """Thread-safe in-memory key→value store with per-entry TTL.

    Parameters
    ----------
    max_size:
        Maximum number of entries the cache will hold before triggering
        eviction.  Defaults to ``1000``.
    """

    def __init__(self, max_size: int = 1000) -> None:
        """Initialise the cache.

        Parameters
        ----------
        max_size:
            Upper bound on stored entries.
        """
        self._store: dict[str, CacheEntry] = {}
        self._lock: threading.Lock = threading.Lock()
        self._max_size: int = max_size

    # ── Public API ───────────────────────────────────────────────────────

    def get(self, key: str) -> Any | None:
        """Retrieve a value by key, returning ``None`` on miss or expiry.

        Expired entries are lazily deleted on access.

        Parameters
        ----------
        key:
            The cache key to look up.

        Returns
        -------
        Any | None
            The cached value, or ``None`` if the key is absent or
            expired.
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.is_expired:
                del self._store[key]
                logger.debug("Cache MISS (expired): %s", key)
                return None
            logger.debug("Cache HIT: %s", key)
            return entry.value

    def set(self, key: str, value: Any, ttl: float = 300.0) -> None:
        """Store a value under *key* with the given TTL.

        If the cache has reached ``max_size``, an eviction pass is
        triggered before the new entry is inserted.

        Parameters
        ----------
        key:
            The cache key.
        value:
            The object to store.
        ttl:
            Time-to-live in seconds.  Defaults to ``300`` (5 minutes).
        """
        with self._lock:
            if len(self._store) >= self._max_size and key not in self._store:
                self._evict_expired()
            self._store[key] = CacheEntry(value, ttl)
            logger.debug("Cache SET: %s (ttl=%.1fs)", key, ttl)

    def delete(self, key: str) -> bool:
        """Remove a single key from the cache.

        Parameters
        ----------
        key:
            The cache key to delete.

        Returns
        -------
        bool
            ``True`` if the key existed (regardless of expiry),
            ``False`` otherwise.
        """
        with self._lock:
            removed = self._store.pop(key, None) is not None
            if removed:
                logger.debug("Cache DELETE: %s", key)
            return removed

    def clear(self) -> None:
        """Remove **all** entries from the cache."""
        with self._lock:
            count = len(self._store)
            self._store.clear()
            logger.debug("Cache CLEAR: removed %d entries", count)

    @property
    def size(self) -> int:
        """Return the current number of entries (including expired ones).

        Returns
        -------
        int
        """
        with self._lock:
            return len(self._store)

    # ── Internal helpers ─────────────────────────────────────────────────

    def _evict_expired(self) -> None:
        """Purge expired entries; if still at capacity, evict the oldest 25 %.

        This method **must** be called while ``self._lock`` is held.
        """
        expired_keys = [k for k, v in self._store.items() if v.is_expired]
        for k in expired_keys:
            del self._store[k]

        if expired_keys:
            logger.debug("Evicted %d expired cache entries", len(expired_keys))

        # If still at capacity after removing expired entries, evict the
        # oldest quarter (by expiry timestamp) to make headroom.
        if len(self._store) >= self._max_size:
            sorted_entries = sorted(
                self._store.items(),
                key=lambda item: item[1].expires_at,
            )
            evict_count = max(1, len(sorted_entries) // 4)
            for k, _ in sorted_entries[:evict_count]:
                del self._store[k]
            logger.debug(
                "Evicted %d oldest cache entries (capacity pressure)",
                evict_count,
            )


# ── Module-level singleton ───────────────────────────────────────────────

cache: Cache = Cache()
"""Global application cache instance.

Import and use directly::

    from app.core.cache import cache
    cache.set("search:queen", results, ttl=900)
"""
