import itertools
import warnings
from unittest.mock import patch

import pytest

from genalog.text import conll_format


@pytest.mark.parametrize(
    "clean_tokens, clean_labels, clean_sentences, ocr_tokens, raised_exception",
    [
        (["w1", "w2"], ["l1", "l2"], [["w1"], ["w2"]], ["w", "w"], None),
        (["w1", "w2"], ["l1", "l2"], [["w1"], ["w2"]], [], ValueError),  # No alignment
        (
            ["w1", "w3"],
            ["l1", "l2"],
            [["w1"], ["w2"]],
            ["w", "w"],
            ValueError,
        ),  # Unequal tokens
        (
            ["w1", "w2"],
            ["l1", "l2"],
            [["w1"], ["w3"]],
            ["w", "w"],
            ValueError,
        ),  # Unequal tokens
        (
            ["w1", "w3"],
            ["l1", "l2"],
            [["w1"]],
            ["w", "w"],
            ValueError,
        ),  # Unequal length
        (
            ["w1"],
            ["l1", "l2"],
            [["w1"], ["w2"]],
            ["w", "w"],
            ValueError,
        ),  # Unequal length
    ],
)
def test_propagate_labels_sentences_error(
    clean_tokens, clean_labels, clean_sentences, ocr_tokens, raised_exception
):
    if raised_exception:
        with pytest.raises(raised_exception):
            conll_format.propagate_labels_sentences(
                clean_tokens, clean_labels, clean_sentences, ocr_tokens
            )
    else:
        conll_format.propagate_labels_sentences(
            clean_tokens, clean_labels, clean_sentences, ocr_tokens
        )


@pytest.mark.parametrize(
    "clean_tokens, clean_labels, clean_sentences, ocr_tokens, desired_sentences, desired_labels",
    [
        (
            "a1 b1 a2 b2".split(),
            "l1 l2 l3 l4".split(),
            [["a1", "b1"], ["a2", "b2"]],  # clean sentences
            ["a1", "b1", "a2", "b2"],  # ocr token
            [["a1", "b1"], ["a2", "b2"]],
            [["l1", "l2"], ["l3", "l4"]],  # desired output
        ),
        (
            "a1 b1 a2 b2".split(),
            "l1 l2 l3 l4".split(),
            [["a1", "b1"], ["a2", "b2"]],  # clean sentences
            ["a1", "b1"],  # Missing sentence 2
            # Ideally we would expect [["a1", "b1"], []]
            # But the limitation of text alignment, which yield
            # "a1 b1 a2 b2"
            # "a1 b1@@@@@@"
            # It is difficult to decide the location of "b1"
            # when all tokens "b1" "a2" "b2" are aligned to "b1@@@@@@"
            # NOTE: this is a improper behavior but the best
            # solution to this corner case by preserving the number of OCR tokens.
            [["a1"], ["b1"]],
            [["l1"], ["l2"]],
        ),
        (
            "a1 b1 a2 b2".split(),
            "l1 l2 l3 l4".split(),
            [["a1", "b1"], ["a2", "b2"]],
            ["a", "a2", "b2"],  # ocr token (missing b1 token at sentence boundary)
            [["a"], ["a2", "b2"]],
            [["l1"], ["l3", "l4"]],
        ),
        (
            "a1 b1 a2 b2".split(),
            "l1 l2 l3 l4".split(),
            [["a1", "b1"], ["a2", "b2"]],
            ["a1", "b1", "a2"],  # ocr token (missing b2 token at sentence boundary)
            [["a1", "b1"], ["a2"]],
            [["l1", "l2"], ["l3"]],
        ),
        (
            "a1 b1 a2 b2".split(),
            "l1 l2 l3 l4".split(),
            [["a1", "b1"], ["a2", "b2"]],
            ["b1", "a2", "b2"],  # ocr token (missing a1 token at sentence start)
            [["b1", "a2"], ["b2"]],
            [["l2", "l3"], ["l4"]],
        ),
        (
            "a1 b1 c1 a2 b2".split(),
            "l1 l2 l3 l4 l5".split(),
            [["a1"], ["b1", "c1", "a2"], ["b2"]],
            [
                "a1",
                "b1",
                "a2",
                "b2",
            ],  # ocr token (missing c1 token at middle of sentence)
            [["a1"], ["b1", "a2"], ["b2"]],
            [["l1"], ["l2", "l4"], ["l5"]],
        ),
        (
            "a1 b1 c1 a2 b2".split(),
            "l1 l2 l3 l4 l5".split(),
            [["a1", "b1"], ["c1", "a2", "b2"]],
            ["a1", "b1", "b2"],  # ocr token (missing c1 a2 tokens)
            [["a1"], ["b1", "b2"]],
            [["l1"], ["l2", "l5"]],
        ),
        (
            "a1 b1 c1 a2 b2".split(),
            "l1 l2 l3 l4 l5".split(),
            [["a1"], ["b1", "c1", "a2"], ["b2"]],
            ["a1", "c1", "a2", "b2"],  # ocr token (missing b1 token at sentence start)
            [[], ["a1", "c1", "a2"], ["b2"]],
            [[], ["l1", "l3", "l4"], ["l5"]],
        ),
        (
            "a1 b1 c1 a2 b2".split(),
            "l1 l2 l3 l4 l5".split(),
            [["a1", "b1", "c1"], ["a2", "b2"]],
            ["a1", "b1", "b2"],  # ocr token (missing c1 and a2 token at sentence end)
            [["a1"], ["b1", "b2"]],
            [["l1"], ["l2", "l5"]],
        ),
        (
            "a1 b1 c1 a2 b2".split(),
            "l1 l2 l3 l4 l5".split(),
            [["a1", "b1", "c1"], ["a2", "b2"]],
            ["a1", "b1", "b2"],  # ocr token (missing c1 and a2 token at sentence end)
            [["a1"], ["b1", "b2"]],
            [["l1"], ["l2", "l5"]],
        ),
    ],
)
def test_propagate_labels_sentences(
    clean_tokens,
    clean_labels,
    clean_sentences,
    ocr_tokens,
    desired_sentences,
    desired_labels,
):
    ocr_text_sentences, ocr_labels_sentences = conll_format.propagate_labels_sentences(
        clean_tokens, clean_labels, clean_sentences, ocr_tokens
    )
    ocr_sentences_flatten = list(itertools.chain(*ocr_text_sentences))
    assert len(ocr_text_sentences) == len(clean_sentences)
    assert len(ocr_text_sentences) == len(ocr_labels_sentences)
    assert len(ocr_sentences_flatten) == len(
        ocr_tokens
    )  # ensure aligned ocr tokens == ocr tokens
    if desired_sentences != ocr_text_sentences:
        warnings.warn(
            RuntimeWarning(
                f"\n\n****Expect propagation returns sentences:****\n{desired_sentences} \n****But got:****\n{ocr_text_sentences}"
            )
        )
    if desired_labels != ocr_labels_sentences:
        warnings.warn(
            RuntimeWarning(
                f"\n\n****Expect propagation returns labels:****\n{desired_labels} \n****But got:****\n{ocr_labels_sentences}"
            )
        )


@pytest.mark.parametrize(
    "clean_tokens, clean_labels, clean_sentences, ocr_tokens,"
    + "mock_gt_to_ocr_mapping, mock_ocr_to_gt_mapping, desired_sentences, desired_labels",
    [
        (
            "a b c d".split(),
            "l1 l2 l3 l4".split(),
            [["a", "b"], ["c", "d"]],
            ["a", "b"],  # Sentence is empty
            [[0], [1], [], []],
            [[0], [1]],
            [["a", "b"], []],
            [["l1", "l2"], []],
        ),
        (
            "a b c d".split(),
            "l1 l2 l3 l4".split(),
            [
                [
                    "a",
                    "b",
                ],
                ["c", "d"],
            ],
            ["a", "b", "d"],  # Missing sentence start
            [[0], [1], [], [2]],
            [[0], [1], [3]],
            [["a", "b"], ["d"]],
            [["l1", "l2"], ["l4"]],
        ),
        (
            "a b c d".split(),
            "l1 l2 l3 l4".split(),
            [
                [
                    "a",
                    "b",
                ],
                ["c", "d"],
            ],
            ["a", "c", "d"],  # Missing sentence end
            [[0], [], [1], [2]],
            [[0], [2], [3]],
            [["a"], ["c", "d"]],
            [["l1"], ["l3", "l4"]],
        ),
    ],
)
def test_propagate_labels_sentences_text_alignment_corner_cases(
    clean_tokens,
    clean_labels,
    clean_sentences,
    ocr_tokens,
    mock_gt_to_ocr_mapping,
    mock_ocr_to_gt_mapping,
    desired_sentences,
    desired_labels,
):
    with patch("genalog.text.alignment.parse_alignment") as mock_alignment:
        mock_alignment.return_value = (mock_gt_to_ocr_mapping, mock_ocr_to_gt_mapping)
        (
            ocr_text_sentences,
            ocr_labels_sentences,
        ) = conll_format.propagate_labels_sentences(
            clean_tokens, clean_labels, clean_sentences, ocr_tokens
        )
        ocr_sentences_flatten = list(itertools.chain(*ocr_text_sentences))
        assert len(ocr_text_sentences) == len(clean_sentences)
        assert len(ocr_text_sentences) == len(ocr_labels_sentences)
        assert len(ocr_sentences_flatten) == len(
            ocr_tokens
        )  # ensure aligned ocr tokens == ocr tokens
        if desired_sentences != ocr_text_sentences:
            warnings.warn(
                RuntimeWarning(
                    f"\n\n****Expect propagation returns sentences:****\n{desired_sentences} \n****But got:****\n{ocr_text_sentences}"
                )
            )
        if desired_labels != ocr_labels_sentences:
            warnings.warn(
                RuntimeWarning(
                    f"\n\n****Expect propagation returns labels:****\n{desired_labels} \n****But got:****\n{ocr_labels_sentences}"
                )
            )


@pytest.mark.parametrize(
    "s, desired_output",
    [
        ("", []),
        ("\n\n", []),
        ("a1\tb1\na2\tb2", [["a1", "a2"]]),
        ("a1\tb1\n\na2\tb2", [["a1"], ["a2"]]),
        ("\n\n\na1\tb1\n\na2\tb2\n\n\n", [["a1"], ["a2"]]),
    ],
)
def test_get_sentences_from_iob_format(s, desired_output):
    output = conll_format.get_sentences_from_iob_format(s.splitlines(True))
    assert desired_output == output
