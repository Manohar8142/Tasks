# semverlite

A small, dependency-free implementation of [Semantic Versioning 2.0.0](https://semver.org).

```python
from semverlite import Version
sorted(Version.parse(v) for v in ["1.10.0", "1.2.0"])
```

Run the tests with `python -m pytest tests`.
