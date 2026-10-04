from ttlcache import TTLCache


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def make(maxsize=2, ttl=10):
    clock = FakeClock()
    return TTLCache(maxsize=maxsize, ttl=ttl, timer=clock), clock


def test_expires_exactly_at_ttl_get():
    cache, clock = make()
    cache["a"] = 1
    clock.now = 9.999
    assert cache.get("a") == 1
    clock.now = 10
    assert cache.get("a") is None


def test_expires_exactly_at_ttl_getitem_and_contains():
    cache, clock = make()
    cache["a"] = 1
    clock.now = 10
    assert "a" not in cache
    try:
        cache["a"]
    except KeyError:
        pass
    else:
        raise AssertionError("expected KeyError for expired key")


def test_keys_excludes_entry_at_expiry_instant():
    cache, clock = make()
    cache["a"] = 1
    clock.now = 5
    cache["b"] = 2
    clock.now = 10
    assert cache.keys() == ["b"]


def test_len_counts_only_live_entries():
    cache, clock = make(maxsize=3)
    cache["a"] = 1
    cache["b"] = 2
    clock.now = 5
    cache["c"] = 3
    assert len(cache) == 3
    clock.now = 12
    assert len(cache) == 1
    clock.now = 100
    assert len(cache) == 0


def test_expired_entries_do_not_force_eviction():
    cache, clock = make()
    cache["a"] = 1
    clock.now = 1
    cache["b"] = 2
    clock.now = 2
    assert cache.get("a") == 1
    clock.now = 10.5
    cache["c"] = 3
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert len(cache) == 2


def test_full_cache_of_expired_entries_accepts_new_keys():
    cache, clock = make(maxsize=3)
    for i, key in enumerate("abc"):
        clock.now = i
        cache[key] = i
    clock.now = 50
    cache["x"] = 1
    cache["y"] = 2
    assert sorted(cache.keys()) == ["x", "y"]
