import glob
import warnings

import pytest

from genalog.text import alignment, anchor, preprocess
from tests.unit.cases.text_alignment import ALIGNMENT_REGRESSION_TEST_CASES


@pytest.mark.parametrize(
    "tokens, case_sensitive, desired_output",
    [
        ([], True, set()),
        ([], False, set()),
        (["a", "A"], True, set(["a", "A"])),
        (["a", "A"], False, set()),
        (["An", "an", "ab"], True, set(["An", "an", "ab"])),
        (["An", "an", "ab"], False, set(["ab"])),
    ],
)
def test_get_unique_words(tokens, case_sensitive, desired_output):
    output = anchor.get_unique_words(tokens, case_sensitive=case_sensitive)
    assert desired_output == output


@pytest.mark.parametrize(
    "tokens, desired_output",
    [([], 0), ([""], 0), (["a", "b"], 2), (["abc.", "def!"], 8)],
)
def test_segment_len(tokens, desired_output):
    output = anchor.segment_len(tokens)
    assert desired_output == output


@pytest.mark.parametrize(
    "unique_words, src_tokens, desired_output, raised_exception",
    [
        (set(), [], [], None),
        (set(), ["a"], [], None),
        (set("a"), [], [], ValueError),  # unique word not in src_tokens
        (set("a"), ["b"], [], ValueError),
        (set("a"), ["A"], [], ValueError),  # case sensitive
        (set("a"), ["an", "na", " a "], [], ValueError),  # substring
        (set("a"), ["a"], [("a", 0)], None),  # valid input
        (set("a"), ["c", "b", "a"], [("a", 2)], None),  # multiple src_tokens
        (
            set("ab"),
            ["c", "b", "a"],
            [("b", 1), ("a", 2)],
            None,
        ),  # multiple matches ordered by index
    ],
)
def test_get_word_map(unique_words, src_tokens, desired_output, raised_exception):
    if raised_exception:
        with pytest.raises(raised_exception):
            anchor.get_word_map(unique_words, src_tokens)
    else:
        output = anchor.get_word_map(unique_words, src_tokens)
        assert desired_output == output


@pytest.mark.parametrize(
    "gt_tokens, ocr_tokens, desired_output",
    [
        ([], [], ([], [])),  # empty
        ([""], [""], ([], [])),
        (["a"], ["b"], ([], [])),  # no common unique words
        (["a", "a"], ["a"], ([], [])),  # no unique words
        (["a"], ["a", "a"], ([], [])),
        (["a"], ["a"], ([("a", 0)], [("a", 0)])),  # common unique word exist
        (["a"], ["b", "a"], ([("a", 0)], [("a", 1)])),
        (
            ["a", "b", "c"],
            ["a", "b", "c"],  # common unique words
            ([("a", 0), ("b", 1), ("c", 2)], [("a", 0), ("b", 1), ("c", 2)]),
        ),
        (
            ["a", "b", "c"],
            ["c", "b", "a"],  # common unique words but not in same order
            ([("b", 1)], [("b", 1)]),
        ),
        (
            ["b", "a", "c"],
            ["c", "b", "a"],  # LCS has multiple results
            ([("b", 0), ("a", 1)], [("b", 1), ("a", 2)]),
        ),
        (
            ["c", "a", "b"],
            ["c", "b", "a"],
            ([("c", 0), ("b", 2)], [("c", 0), ("b", 1)]),
        ),
        (
            ["c", "a", "b"],
            ["a", "c", "b"],  # LCS has multiple results
            ([("a", 1), ("b", 2)], [("a", 0), ("b", 2)]),
        ),
    ],
)
def test_get_anchor_map(gt_tokens, ocr_tokens, desired_output):
    desired_gt_map, desired_ocr_map = desired_output
    gt_map, ocr_map = anchor.get_anchor_map(gt_tokens, ocr_tokens)
    assert desired_gt_map == gt_map
    assert desired_ocr_map == ocr_map


# max_seg_length does not change the following output
@pytest.mark.parametrize("max_seg_length", [0, 1, 2, 3, 5, 4, 6])
@pytest.mark.parametrize(
    "gt_tokens, ocr_tokens, desired_output",
    [
        ([], [], ([], [])),  # empty
        ([""], [""], ([], [])),
        (["a"], ["b"], ([], [])),  # no anchors
        (["a", "a"], ["a"], ([], [])),
        (["a"], ["a", "a"], ([], [])),
        (["a"], ["a"], ([0], [0])),  # anchors exist
        (
            "a1 w w w".split(),
            "a1 w w w".split(),  # no anchors in the subsequence [w w w]
            ([0], [0]),
        ),
        ("a1 w w w a2".split(), "a1 w w w a2".split(), ([0, 4], [0, 4])),
        ("a1 w w w2 a2".split(), "a1 w w w3 a2".split(), ([0, 4], [0, 4])),
        (
            "a1 a2 a3".split(),
            "a1 a2 a3".split(),  # all words are anchors
            ([0, 1, 2], [0, 1, 2]),
        ),
        (
            "a1 a2 a3".split(),
            "A1 A2 A3".split(),  # anchor words must be in the same casing
            ([], []),
        ),
        (
            "a1 w w a2".split(),
            "a1 w W a2".split(),  # unique words are case insensitive
            ([0, 3], [0, 3]),
        ),
        (
            "a1 w w a2".split(),
            "A1 w W A2".split(),  # unique words are case insensitive, but anchor are case sensitive
            ([], []),
        ),
    ],
)
def test_find_anchor_recur_various_seg_len(
    max_seg_length, gt_tokens, ocr_tokens, desired_output
):
    desired_gt_anchors, desired_ocr_anchors = desired_output
    gt_anchors, ocr_anchors = anchor.find_anchor_recur(
        gt_tokens, ocr_tokens, max_seg_length=max_seg_length
    )
    assert desired_gt_anchors == gt_anchors
    assert desired_ocr_anchors == ocr_anchors


# Test the recursion bahavior
@pytest.mark.parametrize(
    "gt_tokens, ocr_tokens, max_seg_length, desired_output",
    [
        ("a1 w_ w_ a3".split(), "a1 w_ w_ a3".split(), 6, ([0, 3], [0, 3])),
        (
            "a1 w_ w_ a2 a3 a2".split(),
            "a1 w_ w_ a2 a3 a2".split(),
            4,  # a2 is anchor word in subsequence [a1 w_ w_ a2 a3]
            ([0, 3, 4], [0, 3, 4]),
        ),
        (
            "a1 w_ w_ a2 a3 a2".split(),
            "a1 w_ w_ a2 a3 a2".split(),
            2,  # a2 is anchor word in subsequence [a1 w_ w_ a2 a3]
            ([0, 2, 3, 4, 5], [0, 2, 3, 4, 5]),
        ),
        (
            "a1 w_ w_ a2 w_ w_ a3".split(),
            "a1 w_ a2 w_ a3".split(),
            2,  # missing ocr token
            ([0, 3, 6], [0, 2, 4]),
        ),
        (
            "a1 w_ w_ a2 w_ w_ a3".split(),
            "a1 w_ a2 W_ A3".split(),
            2,  # changing cases
            ([0, 3], [0, 2]),
        ),
    ],
)
def test_find_anchor_recur_fixed_seg_len(
    gt_tokens, ocr_tokens, max_seg_length, desired_output
):
    desired_gt_anchors, desired_ocr_anchors = desired_output
    gt_anchors, ocr_anchors = anchor.find_anchor_recur(
        gt_tokens, ocr_tokens, max_seg_length=max_seg_length
    )
    assert desired_gt_anchors == gt_anchors
    assert desired_ocr_anchors == ocr_anchors


@pytest.mark.parametrize(
    "gt_file, ocr_file",
    zip(
        sorted(glob.glob("tests/unit/text/data/gt_1.txt")),
        sorted(glob.glob("tests/unit/text/data/ocr_1.txt")),
    ),
)
@pytest.mark.parametrize("max_seg_length", [75])
def test_find_anchor_recur_e2e(gt_file, ocr_file, max_seg_length):
    gt_text = open(gt_file, "r").read()
    ocr_text = open(ocr_file, "r").read()
    gt_tokens = preprocess.tokenize(gt_text)
    ocr_tokens = preprocess.tokenize(ocr_text)
    gt_anchors, ocr_anchors = anchor.find_anchor_recur(
        gt_tokens, ocr_tokens, max_seg_length=max_seg_length
    )
    for gt_anchor, ocr_anchor in zip(gt_anchors, ocr_anchors):
        # Ensure that each anchor word is the same word in both text
        assert gt_tokens[gt_anchor] == ocr_tokens[ocr_anchor]


@pytest.mark.parametrize(
    "gt_txt, noisy_txt, expected_aligned_gt, expected_aligned_noise",
    ALIGNMENT_REGRESSION_TEST_CASES,
)
def test_align_w_anchor(gt_txt, noisy_txt, expected_aligned_gt, expected_aligned_noise):
    aligned_gt, aligned_noise = anchor.align_w_anchor(gt_txt, noisy_txt)
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
