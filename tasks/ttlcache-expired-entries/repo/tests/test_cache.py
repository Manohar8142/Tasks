import pytest

from ttlcache import TTLCache


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_set_and_get():
    cache = TTLCache(maxsize=2, ttl=10, timer=FakeClock())
    cache["a"] = 1
    assert cache["a"] == 1
    assert cache.get("missing") is None


def test_entry_expires_after_ttl():
    clock = FakeClock()
    cache = TTLCache(maxsize=2, ttl=10, timer=clock)
    cache["a"] = 1
    clock.now = 11
    assert cache.get("a") is None


def test_invalid_arguments():
    with pytest.raises(ValueError):
        TTLCache(maxsize=0, ttl=1)
