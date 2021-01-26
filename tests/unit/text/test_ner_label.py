import pytest

from genalog.text import ner_label
from tests.unit.cases.label_propagation import LABEL_PROPAGATION_REGRESSION_TEST_CASES


@pytest.mark.parametrize(
    "label, desired_output",
    [
        # Positive Cases
        ("B-org", True),
        (" B-org ", True),  # whitespae tolerant
        ("\tB-ORG\n", True),
        # Negative Cases
        ("I-ORG", False),
        ("O", False),
        ("other-B-label", False),
    ],
)
def test__is_begin_label(label, desired_output):
    output = ner_label._is_begin_label(label)
    assert output == desired_output


@pytest.mark.parametrize(
    "label, desired_output",
    [
        # Positive Cases
        ("I-ORG", True),
        (" \t I-ORG ", True),
        # Negative Cases
        ("O", False),
        ("B-LOC", False),
        ("B-ORG", False),
    ],
)
def test__is_inside_label(label, desired_output):
    output = ner_label._is_inside_label(label)
    assert output == desired_output


@pytest.mark.parametrize(
    "label, desired_output",
    [
        # Positive Cases
        ("I-ORG", True),
        ("B-ORG", True),
        # Negative Cases
        ("O", False),
    ],
)
def test__is_multi_token_label(label, desired_output):
    output = ner_label._is_multi_token_label(label)
    assert output == desired_output


@pytest.mark.parametrize(
    "label, desired_output",
    [
        # Positive Cases
        ("I-Place", "B-Place"),
        (" \t I-place ", "B-place"),
        # Negative Cases
        ("O", "O"),
        ("B-LOC", "B-LOC"),
        (" B-ORG ", " B-ORG "),
    ],
)
def test__convert_to_begin_label(label, desired_output):
    output = ner_label._convert_to_begin_label(label)
    assert output == desired_output


@pytest.mark.parametrize(
    "label, desired_output",
    [
        # Positive Cases
        ("B-LOC", "I-LOC"),
        (" B-ORG ", "I-ORG"),
        # Negative Cases
        ("", ""),
        ("O", "O"),
        ("I-Place", "I-Place"),
        (" \t I-place ", " \t I-place "),
    ],
)
def test__convert_to_inside_label(label, desired_output):
    output = ner_label._convert_to_inside_label(label)
    assert output == desired_output


@pytest.mark.parametrize(
    "begin_label, inside_label, desired_output",
    [
        # Positive Cases
        ("", "I-LOC", True),
        ("B-LOC", "I-ORG", True),
        ("", "I-ORG", True),
        # Negative Cases
        ("", "", False),
        ("O", "O", False),
        ("", "", False),
        ("B-LOC", "O", False),
        ("B-LOC", "B-ORG", False),
        ("B-LOC", "I-LOC", False),
        (" B-ORG ", "I-ORG", False),
    ],
)
def test__is_missing_begin_label(begin_label, inside_label, desired_output):
    output = ner_label._is_missing_begin_label(begin_label, inside_label)
    assert output == desired_output


@pytest.mark.parametrize(
    "gt_tokens, ocr_tokens, desired_input_char_set",
    [
        (["a", "b"], ["c", "d"], set("abcd")),
        (["New", "York"], ["is", "big"], set("NewYorkisbig")),
        (["word1", "word2"], ["word1", "word2"], set("word12")),
    ],
)
def test__find_gap_char_candidates(gt_tokens, ocr_tokens, desired_input_char_set):
    gap_char_candidates, input_char_set = ner_label._find_gap_char_candidates(
        gt_tokens, ocr_tokens
    )
    assert input_char_set == desired_input_char_set
    assert ner_label.GAP_CHAR_SET.difference(input_char_set) == gap_char_candidates


@pytest.mark.parametrize(
    "gt_labels, gt_tokens, ocr_tokens, raised_exception",
    [
        (["o"], ["New York"], ["NewYork"], ValueError),  # non-atomic gt_token
        (["o"], ["NewYork"], ["New York"], ValueError),  # non-atomic ocr_token
        (["o"], [" @ New"], ["@ @"], ValueError),  # non-atomic tokens with GAP_CHAR
        (["o", "o"], ["New"], ["New"], ValueError),  # num gt_labels != num gt_tokens
        (
            ["o"],
            ["@"],
            ["New"],
            ner_label.GapCharError,
        ),  # invalid token with gap char only (gt_token)
        (
            ["o"],
            ["New"],
            ["@"],
            ner_label.GapCharError,
        ),  # invalid token with gap char only (ocr_token)
        (
            ["o", "o"],
            ["New", "@"],
            ["New", "@"],
            ner_label.GapCharError,
        ),  # invalid token (both)
        (
            ["o"],
            [" \n\t@@"],
            ["New"],
            ner_label.GapCharError,
        ),  # invalid token with gap char and space chars (gt_token)
        (
            ["o"],
            ["New"],
            [" \n\t@"],
            ner_label.GapCharError,
        ),  # invalid token with gap char and space chars (ocr_token)
        (["o"], [""], ["New"], ValueError),  # invalid token: empty string (gt_token)
        (["o"], ["New"], [""], ValueError),  # invalid token: empty string (ocr_token)
        (
            ["o"],
            [" \n\t"],
            ["New"],
            ValueError,
        ),  # invalid token: space characters only (gt_token)
        (
            ["o"],
            ["New"],
            [" \n\t"],
            ValueError,
        ),  # invalid token: space characters only (ocr_token)
        (["o"], ["New"], ["New"], None),  # positive case
        (["o"], ["New@"], ["New"], None),  # positive case with gap char
        (["o"], ["New"], ["@@New"], None),  # positive case with gap char
    ],
)
def test__propagate_label_to_ocr_error(
    gt_labels, gt_tokens, ocr_tokens, raised_exception
):
    if raised_exception:
        with pytest.raises(raised_exception):
            ner_label._propagate_label_to_ocr(
                gt_labels, gt_tokens, ocr_tokens, gap_char="@"
            )
    else:
        ner_label._propagate_label_to_ocr(
            gt_labels, gt_tokens, ocr_tokens, gap_char="@"
        )


@pytest.mark.parametrize(
    "gt_labels, gt_tokens, ocr_tokens, desired_ocr_labels",
    LABEL_PROPAGATION_REGRESSION_TEST_CASES,
)
def test__propagate_label_to_ocr(gt_labels, gt_tokens, ocr_tokens, desired_ocr_labels):
    gap_char_candidates, _ = ner_label._find_gap_char_candidates(gt_tokens, ocr_tokens)
    # run regression test for each GAP_CHAR candidate to make sure
    # label propagate is function correctly
    for gap_char in gap_char_candidates:
        ocr_labels, _, _, _ = ner_label._propagate_label_to_ocr(
            gt_labels, gt_tokens, ocr_tokens, gap_char=gap_char
        )
        assert ocr_labels == desired_ocr_labels


@pytest.mark.parametrize(
    "gt_labels, gt_tokens, ocr_tokens, raised_exception",
    [
        (["o"], ["New"], ["New"], None),  # positive case
        (["o"], ["New@"], ["New"], None),  # positive case with gap char
        (["o"], ["New"], ["@@New"], None),  # positive case with gap char
        (
            ["o"],
            list(ner_label.GAP_CHAR_SET),
            [""],
            ner_label.GapCharError,
        ),  # input char set == GAP_CHAR_SET
        (
            ["o"],
            [""],
            list(ner_label.GAP_CHAR_SET),
            ner_label.GapCharError,
        ),  # input char set == GAP_CHAR_SET
        # all possible gap chars set split between ocr and gt tokens
        (
            ["o"],
            list(ner_label.GAP_CHAR_SET)[:10],
            list(ner_label.GAP_CHAR_SET)[10:],
            ner_label.GapCharError,
        ),
    ],
)
def test_propagate_label_to_ocr_error(
    gt_labels, gt_tokens, ocr_tokens, raised_exception
):
    if raised_exception:
        with pytest.raises(raised_exception):
            ner_label.propagate_label_to_ocr(gt_labels, gt_tokens, ocr_tokens)
    else:
        ner_label.propagate_label_to_ocr(gt_labels, gt_tokens, ocr_tokens)


@pytest.mark.parametrize(
    "gt_labels, gt_tokens, ocr_tokens, desired_ocr_labels",
    LABEL_PROPAGATION_REGRESSION_TEST_CASES,
)
def test_propagate_label_to_ocr(gt_labels, gt_tokens, ocr_tokens, desired_ocr_labels):
    ocr_labels, _, _, _ = ner_label.propagate_label_to_ocr(
        gt_labels, gt_tokens, ocr_tokens
    )
    assert ocr_labels == desired_ocr_labels


@pytest.mark.parametrize(
    "tokens, labels, label_top, desired_output",
    [
        (
            ["New", "York", "is", "big"],
            ["B-place", "I-place", "o", "o"],
            True,
            "B-place I-place o  o   \n" + "New     York    is big \n",
        ),
        (
            ["New", "York", "is", "big"],
            ["B-place", "I-place", "o", "o"],
            False,
            "New     York    is big \n" + "B-place I-place o  o   \n",
        ),
    ],
)
def test_format_label(tokens, labels, label_top, desired_output):
    output = ner_label.format_labels(tokens, labels, label_top=label_top)
    assert output == desired_output


@pytest.mark.parametrize(
    "gt_labels, gt_tokens, ocr_tokens, desired_ocr_labels",
    LABEL_PROPAGATION_REGRESSION_TEST_CASES,
)
def test_format_gt_ocr_w_labels(gt_labels, gt_tokens, ocr_tokens, desired_ocr_labels):
    ocr_labels, aligned_gt, aligned_ocr, gap_char = ner_label.propagate_label_to_ocr(
        gt_labels, gt_tokens, ocr_tokens
    )
    ner_label.format_label_propagation(
        gt_tokens, gt_labels, ocr_tokens, ocr_labels, aligned_gt, aligned_ocr
    )
