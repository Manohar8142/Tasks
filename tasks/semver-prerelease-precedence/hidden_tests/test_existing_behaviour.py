import pytest

from semverlite import Version

V = Version.parse


def test_parse_roundtrip():
    for text in ["0.0.1", "1.2.3-rc.1", "1.2.3+meta", "1.2.3-x.7.z.92+exp.sha.5114f85"]:
        assert str(V(text)) == text


@pytest.mark.parametrize("text", ["1.2", "01.2.3", "1.2.3-", "1.2.3-01", "1.2.3+", "a.b.c"])
def test_invalid_versions_rejected(text):
    with pytest.raises(ValueError):
        V(text)


def test_core_ordering():
    assert V("1.2.3") < V("1.10.0") < V("2.0.0")
    assert V("1.2.3") <= V("1.2.3")


def test_build_metadata_ignored():
    assert V("1.0.0+a") == V("1.0.0+b")
    assert hash(V("1.0.0+a")) == hash(V("1.0.0+b"))
    assert not V("1.0.0+a") < V("1.0.0+b")
    assert V("1.0.0-rc.1+x") == V("1.0.0-rc.1")


def test_equal_versions_hash_equal():
    assert len({V("1.0.0-alpha.1"), V("1.0.0-alpha.1+build"), V("1.0.0")}) == 2


def test_bumps():
    assert str(V("1.2.3").bump_major()) == "2.0.0"
    assert str(V("1.2.3").bump_minor()) == "1.3.0"
    assert str(V("1.2.3").bump_patch()) == "1.2.4"
    assert str(V("1.2.3-rc.1").bump_patch()) == "1.2.3"


def test_comparison_with_other_types():
    assert V("1.0.0") != "1.0.0"
    with pytest.raises(TypeError):
        V("1.0.0") < "1.0.0"
