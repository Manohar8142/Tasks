"""Conversion between human-readable duration strings and ``timedelta``."""

from __future__ import annotations

import re
from datetime import timedelta

# Unit suffix -> length in seconds, largest first.
UNITS = {"d": 86400, "h": 3600, "m": 60, "s": 1}

_SINGLE = re.compile(r"^\s*(\d+)\s*([dhms])\s*$")


def parse_duration(text: str) -> timedelta:
    """Parse a duration such as ``"90s"`` or ``"2h"``.

    Raises ``TypeError`` for non-string input and ``ValueError`` for
    anything that is not a valid duration.
    """
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")
    match = _SINGLE.match(text)
    if not match:
        raise ValueError(f"invalid duration: {text!r}")
    amount, unit = match.groups()
    return timedelta(seconds=int(amount) * UNITS[unit])


def format_duration(delta: timedelta) -> str:
    """Format a non-negative ``timedelta`` compactly, e.g. ``"1d2h5s"``.

    Sub-second precision is dropped. A zero duration formats as ``"0s"``.
    """
    if delta < timedelta(0):
        raise ValueError("negative durations are not supported")
    remaining = int(delta.total_seconds())
    parts = []
    for unit, size in UNITS.items():
        amount, remaining = divmod(remaining, size)
        if amount:
            parts.append(f"{amount}{unit}")
    return "".join(parts) or "0s"
