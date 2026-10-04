# TTLCache keeps treating expired entries as live

We use `TTLCache` to cache auth tokens with `ttl` set to exactly the token
lifetime, and we keep serving tokens the server has already rejected. Looking
into it, I found that expired entries leak out in several ways.

1. **Off-by-one at the expiry instant.** The docstring says an entry written
   at time `t` is live while `timer() < t + ttl`. But at exactly `t + ttl`,
   `get()`, `[]` and `in` still return the old value.
2. **`len()` counts expired entries.** After every entry has expired,
   `len(cache)` still reports the old size.
3. **Expired entries cause live ones to be evicted.** When the cache is "full"
   only because of expired entries, inserting a new key evicts a *live*
   least-recently-used entry instead of reclaiming the expired slot.

## Reproduction

```python
from ttlcache import TTLCache

now = [0.0]
cache = TTLCache(maxsize=2, ttl=10, timer=lambda: now[0])
cache["a"] = 1          # expires at 10
now[0] = 1
cache["b"] = 2          # expires at 11
now[0] = 2
cache.get("a")          # "a" is now the most recently used
now[0] = 10.5           # "a" has expired, "b" is still live
cache["c"] = 3
cache.get("b")          # expected 2, got None: "b" was evicted instead of expired "a"
```

## Expected behaviour

* Entries stop being visible at exactly `t + ttl` through every access path:
  `get`, `[]`, `in` and `keys()`.
* `len()` counts only live entries.
* Expired entries never take up capacity. A live entry is only evicted when
  the cache holds `maxsize` *live* entries.
* LRU behaviour among live entries, and the public API, stay unchanged.
