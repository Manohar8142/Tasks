import pytest

from ttlcache import TTLCache


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def make(maxsize=2, ttl=10):
    clock = FakeClock()
    return TTLCache(maxsize=maxsize, ttl=ttl, timer=clock), clock


def test_basic_get_set():
    cache, _ = make()
    cache["a"] = 1
    assert cache["a"] == 1
    assert cache.get("a") == 1
    assert cache.get("zz", "dflt") == "dflt"
    assert "a" in cache


def test_missing_key_raises():
    cache, _ = make()
    with pytest.raises(KeyError):
        cache["nope"]


def test_lru_eviction_among_live_entries():
    cache, clock = make()
    cache["a"] = 1
    cache["b"] = 2
    cache.get("a")
    cache["c"] = 3
    assert "b" not in cache
    assert cache.get("a") == 1
    assert cache.get("c") == 3


def test_overwrite_refreshes_ttl_without_eviction():
    cache, clock = make()
    cache["a"] = 1
    cache["b"] = 2
    clock.now = 8
    cache["a"] = 10
    assert len(cache) == 2
    clock.now = 15
    assert cache.get("a") == 10
    assert cache.get("b") is None


def test_delete_and_clear():
    cache, _ = make()
    cache["a"] = 1
    cache["b"] = 2
    del cache["a"]
    assert "a" not in cache
    cache.clear()
    assert len(cache) == 0


def test_expired_after_ttl():
    cache, clock = make()
    cache["a"] = 1
    clock.now = 11
    assert cache.get("a") is None
    assert "a" not in cache


@pytest.mark.parametrize("maxsize,ttl", [(0, 1), (-1, 1), (1, 0), (1, -5)])
def test_invalid_arguments(maxsize, ttl):
    with pytest.raises(ValueError):
        TTLCache(maxsize=maxsize, ttl=ttl)


def test_keys_in_lru_order():
    cache, _ = make(maxsize=3)
    cache["a"] = 1
    cache["b"] = 2
    cache["c"] = 3
    cache.get("a")
    assert cache.keys() == ["b", "c", "a"]
