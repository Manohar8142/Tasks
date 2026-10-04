from datetime import timedelta

import pytest

from durations import format_duration, parse_duration


@pytest.mark.parametrize("text,expected", [
    ("1h30m", timedelta(hours=1, minutes=30)),
    ("2d4h", timedelta(days=2, hours=4)),
    ("1d2h3m4s", timedelta(days=1, hours=2, minutes=3, seconds=4)),
    ("1m30s500ms", timedelta(minutes=1, seconds=30, milliseconds=500)),
    ("2h0m", timedelta(hours=2)),
])
def test_compound(text, expected):
    assert parse_duration(text) == expected


@pytest.mark.parametrize("text,expected", [
    (" 1h 30m ", timedelta(hours=1, minutes=30)),
    ("2 h", timedelta(hours=2)),
    ("1d\t12h", timedelta(days=1, hours=12)),
])
def test_whitespace(text, expected):
    assert parse_duration(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("1.5h", timedelta(hours=1, minutes=30)),
    ("0.25s", timedelta(milliseconds=250)),
    ("0.1s", timedelta(milliseconds=100)),
    ("2.5d1.5h", timedelta(days=2, hours=13, minutes=30)),
    ("1.0000005s", timedelta(seconds=1, microseconds=0)),
])
def test_fractional(text, expected):
    assert abs(parse_duration(text) - expected) <= timedelta(microseconds=1)


def test_fractional_is_exact_where_representable():
    assert parse_duration("0.3s") == timedelta(microseconds=300000)
    assert parse_duration("1.1h") == timedelta(seconds=3960)


def test_milliseconds_unit():
    assert parse_duration("250ms") == timedelta(milliseconds=250)
    assert parse_duration("1s1ms") == timedelta(seconds=1, milliseconds=1)


@pytest.mark.parametrize("text", [
    "1h2h", "30m1h", "1s1m", "1ms1s", "1m1m",
    ".5h", "5.h", "+1h", "-1h", "1e3s", "1h30", "h", "1 h x", "1hh",
    "1x", "1h,30m", "1h-30m",
])
def test_invalid_compound_inputs(text):
    with pytest.raises(ValueError):
        parse_duration(text)


@pytest.mark.parametrize("seconds", [1, 59, 3600, 3661, 86400 + 61, 10 * 86400 + 7])
def test_roundtrip_with_format(seconds):
    delta = timedelta(seconds=seconds)
    assert parse_duration(format_duration(delta)) == delta
