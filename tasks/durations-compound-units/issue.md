# Support compound and fractional durations in `parse_duration`

`format_duration` produces strings like `"1h30m"`, but `parse_duration`
rejects them because it only accepts a single integer and unit. So
`parse_duration(format_duration(x))` fails for most values, and users of our
config files cannot write natural values like `1h30m` or `1.5h`.

## Requested behaviour

Extend `parse_duration` so it accepts a sequence of one or more
`<number><unit>` components:

* **Units:** `d` (days), `h` (hours), `m` (minutes), `s` (seconds) and a new
  `ms` (milliseconds).
* **Numbers:** non-negative integers or decimals with digits on both sides of
  the point (`1.5h`, `0.25s`). Forms like `.5h`, `5.h`, signs and exponents
  are invalid.
* **Order:** each unit may appear at most once, from largest to smallest
  (`d`, `h`, `m`, `s`, `ms`). `1h30m` is valid; `30m1h` and `1h2h` are not.
* **Whitespace:** allowed around the whole string, between components, and
  between a number and its unit (`" 1h 30m "`, `"2 h"`).
* **Result:** the total as a `timedelta`, exact to the microsecond (for
  example `1.5h == timedelta(hours=1, minutes=30)` and
  `0.1s == timedelta(milliseconds=100)`).

Everything else must keep raising `ValueError`, including the empty string,
a bare unit, a number with no unit, an unknown unit and trailing garbage.
Non-string input keeps raising `TypeError`, and existing single-unit inputs
keep working unchanged. `format_duration` is out of scope and should not change.
