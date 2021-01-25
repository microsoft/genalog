import pytest

from genalog.text.lcs import LCS


@pytest.fixture(
    params=[
        ("", ""),  # empty
        ("abcde", "ace"),  # naive case
    ]
)
def lcs(request):
    str1, str2 = request.param
    return LCS(str1, str2)


def test_lcs_init(lcs):
    assert lcs._lcs_len is not None
    assert lcs._lcs is not None


@pytest.mark.parametrize(
    "str1, str2, expected_len, expected_lcs",
    [
        ("", "", 0, ""),  # empty
        ("abc", "abc", 3, "abc"),
        ("abcde", "ace", 3, "ace"),  # naive case
        ("a", "", 0, ""),  # no results
        ("abc", "cba", 1, "c"),  # multiple cases
        ("abcdgh", "aedfhr", 3, "adh"),
        ("abc.!\t\nd", "dxab", 2, "ab"),  # with punctuations
        (
            "New York @",
            "New @ York",
            len("New York"),
            "New York",
        ),  # with space-separated, tokens
        ("Is A Big City", "A Big City Is", len("A Big City"), "A Big City"),
        ("Is A Big City", "City Big Is A", len(" Big "), " Big "),  # reversed order
        # mixed order with similar tokens
        ("Is A Big City IS", "IS Big A City Is", len("I Big City I"), "I Big City I"),
        # casing
        (
            "Is A Big City IS a",
            "IS a Big City Is A",
            len("I  Big City I "),
            "I  Big City I ",
        ),
    ],
)
def test_lcs_e2e(str1, str2, expected_len, expected_lcs):
    lcs = LCS(str1, str2)
    assert expected_lcs == lcs.get_str()
    assert expected_len == lcs.get_len()
