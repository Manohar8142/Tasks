"""A size-bounded mapping whose entries expire a fixed time after insertion."""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Callable, Hashable

_MISSING = object()


class TTLCache:
    """Least-recently-used cache with per-entry time-to-live.

    An entry written at time ``t`` is live while ``timer() < t + ttl``.
    When the cache is full, writing a new key evicts the least recently
    used entry.
    """

    def __init__(self, maxsize: int, ttl: float, timer: Callable[[], float] = time.monotonic):
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self.maxsize = maxsize
        self.ttl = ttl
        self._timer = timer
        self._data: OrderedDict[Hashable, tuple[object, float]] = OrderedDict()

    def __setitem__(self, key, value) -> None:
        now = self._timer()
        if key in self._data:
            del self._data[key]
        elif len(self._data) >= self.maxsize:
            self._data.popitem(last=False)
        self._data[key] = (value, now + self.ttl)

    def get(self, key, default=None):
        item = self._data.get(key)
        if item is None:
            return default
        value, expires_at = item
        if self._timer() > expires_at:
            del self._data[key]
            return default
        self._data.move_to_end(key)
        return value

    def __getitem__(self, key):
        value = self.get(key, _MISSING)
        if value is _MISSING:
            raise KeyError(key)
        return value

    def __contains__(self, key) -> bool:
        item = self._data.get(key)
        return item is not None and self._timer() <= item[1]

    def __delitem__(self, key) -> None:
        del self._data[key]

    def __len__(self) -> int:
        return len(self._data)

    def keys(self) -> list:
        """Live keys, least recently used first."""
        now = self._timer()
        return [k for k, (_, expires_at) in self._data.items() if now <= expires_at]

    def clear(self) -> None:
        self._data.clear()
