"""Simple caching utilities — TTL memory cache and LRU decorator."""

from __future__ import annotations

import time
from functools import lru_cache as _lru_cache, wraps
from threading import Lock
from typing import Any, Callable, Optional


class MemoryCache:
    """In-memory cache with optional TTL per entry."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, Optional[float]]] = {}
        self._lock = Lock()

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Store a value with an optional TTL (seconds)."""
        expires_at = time.monotonic() + ttl if ttl is not None else None
        with self._lock:
            self._store[key] = (value, expires_at)

    def get(self, key: str) -> Any:
        """Retrieve a value, or None if missing/expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at is not None and time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._store.clear()

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)


def cached(maxsize: int = 128) -> Callable:
    """Decorator that wraps a function with functools.lru_cache.

    Args:
        maxsize: Maximum number of cached entries.

    Returns:
        Decorator that applies lru_cache to the decorated function.
    """
    def decorator(func: Callable) -> Callable:
        lru = _lru_cache(maxsize=maxsize)(func)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return lru(*args, **kwargs)

        wrapper.cache_info = lru.cache_info  # type: ignore[attr-defined]
        wrapper.cache_clear = lru.cache_clear  # type: ignore[attr-defined]
        return wrapper

    return decorator
