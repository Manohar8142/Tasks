from datetime import timedelta

import pytest

from durations import format_duration, parse_duration


def test_parse_single_units():
    assert parse_duration("90s") == timedelta(seconds=90)
    assert parse_duration("2h") == timedelta(hours=2)


def test_parse_rejects_garbage():
    with pytest.raises(ValueError):
        parse_duration("soon")


def test_format():
    assert format_duration(timedelta(hours=1, seconds=5)) == "1h5s"
