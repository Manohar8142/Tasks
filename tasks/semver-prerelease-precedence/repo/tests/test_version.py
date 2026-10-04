import pytest

from semverlite import Version


def test_parse_core():
    v = Version.parse("1.2.3")
    assert (v.major, v.minor, v.patch) == (1, 2, 3)
    assert v.prerelease is None


def test_parse_prerelease_and_build():
    v = Version.parse("1.0.0-rc.1+build.5")
    assert v.prerelease == "rc.1"
    assert v.build == "build.5"


@pytest.mark.parametrize("text", ["1.2", "01.2.3", "1.2.3-", "1.2.3-01", "v1.2.3"])
def test_parse_rejects_invalid(text):
    with pytest.raises(ValueError):
        Version.parse(text)


def test_core_ordering():
    assert Version.parse("1.2.3") < Version.parse("1.10.0")
