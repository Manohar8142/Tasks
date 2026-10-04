# durations

Parse and format human-readable durations.

```python
>>> from durations import parse_duration, format_duration
>>> parse_duration("2h")
datetime.timedelta(seconds=7200)
>>> format_duration(parse_duration("2h"))
'2h'
```

Run the tests with `python -m pytest tests`.
