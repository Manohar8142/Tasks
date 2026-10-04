import pytest

from semverlite import Version

V = Version.parse

SPEC_CHAIN = [
    "1.0.0-alpha",
    "1.0.0-alpha.1",
    "1.0.0-alpha.beta",
    "1.0.0-beta",
    "1.0.0-beta.2",
    "1.0.0-beta.11",
    "1.0.0-rc.1",
    "1.0.0",
]


def test_prerelease_lower_than_release():
    assert V("1.0.0-rc.1") < V("1.0.0")
    assert V("1.0.0") > V("1.0.0-rc.1")
    assert V("2.0.0-alpha") > V("1.9.9")


def test_numeric_identifiers_compare_numerically():
    assert V("1.0.0-alpha.2") < V("1.0.0-alpha.10")
    assert V("1.0.0-9") < V("1.0.0-10")


def test_numeric_lower_than_alphanumeric():
    assert V("1.0.0-1") < V("1.0.0-alpha")
    assert V("1.0.0-alpha.1") < V("1.0.0-alpha.beta")


def test_longer_identifier_list_wins_when_prefix_equal():
    assert V("1.0.0-alpha") < V("1.0.0-alpha.1")
    assert V("1.0.0-alpha.1") < V("1.0.0-alpha.1.0")


@pytest.mark.parametrize("i", range(len(SPEC_CHAIN) - 1))
def test_spec_chain_pairwise(i):
    assert V(SPEC_CHAIN[i]) < V(SPEC_CHAIN[i + 1])
    assert not V(SPEC_CHAIN[i + 1]) < V(SPEC_CHAIN[i])


def test_sorting_matches_spec():
    shuffled = [SPEC_CHAIN[i] for i in (4, 7, 0, 6, 2, 5, 1, 3)]
    assert [str(v) for v in sorted(map(V, shuffled))] == SPEC_CHAIN
    assert str(max(map(V, shuffled))) == "1.0.0"
