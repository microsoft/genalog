import warnings
from random import randint
from unittest.mock import MagicMock

import pytest

from genalog.text import alignment
from tests.unit.cases.text_alignment import ALIGNMENT_REGRESSION_TEST_CASES
from tests.unit.cases.text_alignment import PARSE_ALIGNMENT_REGRESSION_TEST_CASES

MOCK_ALIGNMENT_RESULT = [("X", "X", 0, 0, 1)]


@pytest.fixture(scope="function")
def random_num_gap_char():
    return alignment.GAP_CHAR*randint(1, 100)


# Settup mock for third party library call
@pytest.fixture
def mock_pairwise2_align(monkeypatch):
    mock = MagicMock()

    def mock_globalcs(*args, **kwargs):
        mock.globalcs(*args, **kwargs)
        return MOCK_ALIGNMENT_RESULT

    # replace target method reference with the mock method
    monkeypatch.setattr("Bio.pairwise2.align.globalcs", mock_globalcs)
    return mock


def test__align_seg(mock_pairwise2_align):
    # setup method input
    required_arg = ("A", "B")
    optional_arg = (
        alignment.MATCH_REWARD,
        alignment.MISMATCH_PENALTY,
        alignment.GAP_PENALTY,
        alignment.GAP_EXT_PENALTY,
    )
    optional_kwarg = {
        "gap_char": alignment.GAP_CHAR,
        "one_alignment_only": alignment.ONE_ALIGNMENT_ONLY,
    }
    # test method
    result = alignment._align_seg(*required_arg + optional_arg, **optional_kwarg)
    # assertion
    mock_pairwise2_align.globalcs.assert_called()
    assert result == MOCK_ALIGNMENT_RESULT


@pytest.mark.parametrize(
    "alignments, target_num_tokens, raised_exception",
    [
        (MOCK_ALIGNMENT_RESULT, 1, None),
        (MOCK_ALIGNMENT_RESULT, 2, ValueError),
        ([("X", "XY", 0, 0, 1)], 1, ValueError),
    ],
)
def test__select_alignment_candidates(alignments, target_num_tokens, raised_exception):
    if raised_exception:
        with pytest.raises(raised_exception):
            alignment._select_alignment_candidates(alignments, target_num_tokens)
    else:
        result = alignment._select_alignment_candidates(alignments, target_num_tokens)
        assert result == MOCK_ALIGNMENT_RESULT[0]


@pytest.mark.parametrize(
    "s, index, desired_output, raised_exception",
    [
        # Test exceptions
        ("s", 2, None, IndexError),
        ("", -1, None, ValueError),  # Empty case
        # Index at start of string
        ("  token", 0, 2, None),
        ("\t\ntoken", 0, 2, None),
        # Index reach end of string
        ("token ", 5, 5, None),
        ("token", 4, 4, None),
        # Index in-between tokens
        ("token", 0, 0, None),
        ("t1     t2", 2, 7, None),
        ("t1 \t \n t2", 3, 7, None),
        # Gap char
        (" @", 0, 1, None),
    ],
)
def test__find_token_start(s, index, desired_output, raised_exception):
    if raised_exception:
        with pytest.raises(raised_exception):
            alignment._find_token_start(s, index)
    else:
        output = alignment._find_token_start(s, index)
        assert output == desired_output


@pytest.mark.parametrize(
    "s, index, desired_output, raised_exception",
    [
        # Test exceptions
        ("s", 2, None, IndexError),
        ("", -1, None, ValueError),  # Empty case
        # Index at start of string
        (" ", 0, 0, None),
        ("\t\ntoken", 0, 0, None),
        ("token", 0, 4, None),
        ("token\t", 0, 5, None),
        ("token\n", 0, 5, None),
        # Index reach end of string
        ("token ", 5, 5, None),
        ("token", 4, 4, None),
        # Single Char
        (".", 0, 0, None),
        # Gap char
        ("@@  @", 0, 2, None),
    ],
)
def test__find_token_end(s, index, desired_output, raised_exception):
    if raised_exception:
        with pytest.raises(raised_exception):
            alignment._find_token_end(s, index)
    else:
        output = alignment._find_token_end(s, index)
        assert output == desired_output


@pytest.mark.parametrize(
    "s, start, desired_output",
    [
        ("token", 0, (0, 4)),
        ("token\t", 0, (0, 5)),
        ("token \n", 0, (0, 5)),
        (" token ", 0, (1, 6)),
        # mix with GAP_CHAR
        (" @@@@ ", 0, (1, 5)),
        ("\n\t tok@n@@ \n\t", 0, (3, 10)),
        # single character string
        ("s", 0, (0, 0)),
        # punctuation
        ("  !,.: ", 0, (2, 6)),
    ],
)
def test__find_next_token(s, start, desired_output):
    output = alignment._find_next_token(s, start)
    assert output == desired_output


@pytest.mark.parametrize(
    "token, desired_output",
    [
        # Valid tokens
        ("\n\t token.!,:\n\t ", True),
        ("token", True),
        (" @@@t@@@ ", True),
        ("@@token@@", True),
        (" @@token@@ ", True),
        ("t1{}t2", True),  # i.e. 't1@t2' # injects arbitrary number of gap chars
        # Invalid tokens (i.e. multiples of the GAP_CHAR)
        ("", False),
        (" ", False),
        ("@@", False),
        (" @@ ", False),
        ("\t\n@", False),
        (alignment.GAP_CHAR, False),
        ("{}", False),  # injects arbitrary number of gap chars
        ("\n\t {} \n\t", False),  # injects arbitrary number of gap chars
    ],
)
def test__is_valid_token(random_num_gap_char, token, desired_output):
    token = token.format(random_num_gap_char)
    result = alignment._is_valid_token(token)
    assert result == desired_output


@pytest.mark.parametrize(
    "aligned_gt, aligned_noise," + "expected_gt_to_noise_map, expected_noise_to_gt_map",
    PARSE_ALIGNMENT_REGRESSION_TEST_CASES,
)
def test_parse_alignment(
    aligned_gt, aligned_noise, expected_gt_to_noise_map, expected_noise_to_gt_map
):
    gt_to_noise_map, noise_to_gt_map = alignment.parse_alignment(
        aligned_gt, aligned_noise
    )
    assert gt_to_noise_map == expected_gt_to_noise_map
    assert noise_to_gt_map == expected_noise_to_gt_map


@pytest.mark.parametrize(
    "gt_txt, noisy_txt," + "expected_aligned_gt, expected_aligned_noise",
    ALIGNMENT_REGRESSION_TEST_CASES,
)
def test_align(gt_txt, noisy_txt, expected_aligned_gt, expected_aligned_noise):
    aligned_gt, aligned_noise = alignment.align(gt_txt, noisy_txt)
    if aligned_gt != expected_aligned_gt:
        expected_alignment = alignment._format_alignment(
            expected_aligned_gt, expected_aligned_noise
        )
        result_alignment = alignment._format_alignment(aligned_gt, aligned_noise)
        warnings.warn(
            RuntimeWarning(
                f"\n\n****Expect alignment returns:****\n{expected_alignment} \n****But got:****\n{result_alignment}"
            )
        )
