from datetime import timedelta

import pytest

from durations import format_duration, parse_duration


@pytest.mark.parametrize("text,expected", [
    ("90s", timedelta(seconds=90)),
    ("15m", timedelta(minutes=15)),
    ("2h", timedelta(hours=2)),
    ("1d", timedelta(days=1)),
    ("0s", timedelta(0)),
    ("  7m ", timedelta(minutes=7)),
])
def test_single_units(text, expected):
    assert parse_duration(text) == expected


@pytest.mark.parametrize("text", ["", "   ", "soon", "10", "10y", "1h!"])
def test_invalid(text):
    with pytest.raises(ValueError):
        parse_duration(text)


@pytest.mark.parametrize("value", [None, 5, 1.5, b"1h"])
def test_non_string_raises_type_error(value):
    with pytest.raises(TypeError):
        parse_duration(value)


def test_format_duration_unchanged():
    assert format_duration(timedelta(0)) == "0s"
    assert format_duration(timedelta(hours=1, seconds=5)) == "1h5s"
    assert format_duration(timedelta(days=1, minutes=1, milliseconds=900)) == "1d1m"
    with pytest.raises(ValueError):
        format_duration(timedelta(seconds=-1))
