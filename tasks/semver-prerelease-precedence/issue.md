# Pre-release versions sort in the wrong order

`Version` comparisons do not follow the precedence rules in the
[SemVer 2.0.0 spec, section 11](https://semver.org/#spec-item-11). This makes
our release tooling pick the wrong "latest" version.

## Reproduction

```python
from semverlite import Version

Version.parse("1.0.0-rc.1") < Version.parse("1.0.0")
# expected True, got False

sorted(["1.0.0-alpha.10", "1.0.0-alpha.2"], key=Version.parse)
# expected ['1.0.0-alpha.2', '1.0.0-alpha.10'], got the reverse
```

## Expected behaviour

Ordering must match the spec, including:

* A pre-release version has lower precedence than the associated normal
  version (`1.0.0-rc.1 < 1.0.0`).
* Pre-release identifiers are compared one dot-separated identifier at a time.
  Identifiers made only of digits compare numerically; others compare
  lexically in ASCII order.
* Numeric identifiers always have lower precedence than non-numeric ones.
* A larger set of identifiers has higher precedence when all preceding
  identifiers are equal.
* Build metadata is still ignored for both ordering and equality, and equal
  versions must still hash equally.
