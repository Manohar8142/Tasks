"""Parsing and comparison of Semantic Versioning 2.0.0 version strings."""

from __future__ import annotations

import re
from functools import total_ordering

_IDENT = r"[0-9A-Za-z-]+"
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    rf"(?:-({_IDENT}(?:\.{_IDENT})*))?"
    rf"(?:\+({_IDENT}(?:\.{_IDENT})*))?$"
)


@total_ordering
class Version:
    """An immutable semantic version.

    Build metadata is kept for display but ignored for equality and ordering.
    """

    __slots__ = ("major", "minor", "patch", "prerelease", "build")

    def __init__(self, major: int, minor: int, patch: int,
                 prerelease: str | None = None, build: str | None = None):
        if min(major, minor, patch) < 0:
            raise ValueError("version numbers must be non-negative")
        self.major = major
        self.minor = minor
        self.patch = patch
        self.prerelease = prerelease
        self.build = build

    @classmethod
    def parse(cls, text: str) -> Version:
        match = _SEMVER_RE.match(text.strip())
        if not match:
            raise ValueError(f"invalid semantic version: {text!r}")
        major, minor, patch, prerelease, build = match.groups()
        if prerelease:
            for ident in prerelease.split("."):
                if ident.isdigit() and len(ident) > 1 and ident[0] == "0":
                    raise ValueError(f"numeric identifier has a leading zero: {text!r}")
        return cls(int(major), int(minor), int(patch), prerelease, build)

    def bump_major(self) -> Version:
        return Version(self.major + 1, 0, 0)

    def bump_minor(self) -> Version:
        return Version(self.major, self.minor + 1, 0)

    def bump_patch(self) -> Version:
        if self.prerelease:
            return Version(self.major, self.minor, self.patch)
        return Version(self.major, self.minor, self.patch + 1)

    def _key(self):
        return (self.major, self.minor, self.patch, self.prerelease or "")

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._key() == other._key()

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._key() < other._key()

    def __hash__(self):
        return hash(self._key())

    def __str__(self):
        text = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            text += f"-{self.prerelease}"
        if self.build:
            text += f"+{self.build}"
        return text

    def __repr__(self):
        return f"Version.parse({str(self)!r})"
