import pytest

import genalog.ocr.metrics
from genalog.ocr.metrics import get_align_stats, get_editops_stats, get_stats
from genalog.text.alignment import align, GAP_CHAR
from genalog.text.ner_label import _find_gap_char_candidates


genalog.ocr.metrics.LOG_LEVEL = 0


@pytest.mark.parametrize(
    "src_string, target, expected_stats",
    [
        (
            "a worn coat",
            "a wom coat",
            {
                "edit_insert": 1,
                "edit_delete": 0,
                "edit_replace": 1,
                "edit_insert_spacing": 0,
                "edit_delete_spacing": 0,
            },
        ),
        (
            " ",
            "a",
            {
                "edit_insert": 0,
                "edit_delete": 0,
                "edit_replace": 1,
                "edit_insert_spacing": 0,
                "edit_delete_spacing": 0,
            },
        ),
        (
            "a",
            " ",
            {
                "edit_insert": 0,
                "edit_delete": 0,
                "edit_replace": 1,
                "edit_insert_spacing": 0,
                "edit_delete_spacing": 0,
            },
        ),
        (
            "a",
            "a",
            {
                "edit_insert": 0,
                "edit_delete": 0,
                "edit_replace": 0,
                "edit_insert_spacing": 0,
                "edit_delete_spacing": 0,
            },
        ),
        (
            "ab",
            "ac",
            {
                "edit_insert": 0,
                "edit_delete": 0,
                "edit_replace": 1,
                "edit_insert_spacing": 0,
                "edit_delete_spacing": 0,
            },
        ),
        (
            "ac",
            "ab",
            {
                "edit_insert": 0,
                "edit_delete": 0,
                "edit_replace": 1,
                "edit_insert_spacing": 0,
                "edit_delete_spacing": 0,
            },
        ),
        (
            "New York is big.",
            "N ewYork kis big.",
            {
                "edit_insert": 0,
                "edit_delete": 1,
                "edit_replace": 0,
                "edit_insert_spacing": 1,
                "edit_delete_spacing": 1,
            },
        ),
        (
            "B oston grea t",
            "Boston is great",
            {
                "edit_insert": 0,
                "edit_delete": 2,
                "edit_replace": 0,
                "edit_insert_spacing": 2,
                "edit_delete_spacing": 1,
            },
        ),
        (
            "New York is big.",
            "N ewyork kis big",
            {
                "edit_insert": 1,
                "edit_delete": 1,
                "edit_replace": 1,
                "edit_insert_spacing": 1,
                "edit_delete_spacing": 1,
            },
        ),
        (
            "dog",
            "d@g",  # Test against default gap_char "@"
            {
                "edit_insert": 0,
                "edit_delete": 0,
                "edit_replace": 1,
                "edit_insert_spacing": 0,
                "edit_delete_spacing": 0,
            },
        ),
        (
            "some@one.com",
            "some@one.com",
            {
                "edit_insert": 0,
                "edit_delete": 0,
                "edit_replace": 0,
                "edit_insert_spacing": 0,
                "edit_delete_spacing": 0,
            },
        ),
    ],
)
def test_editops_stats(src_string, target, expected_stats):
    gap_char_candidates, input_char_set = _find_gap_char_candidates(
        [src_string], [target]
    )
    gap_char = (
        GAP_CHAR if GAP_CHAR in gap_char_candidates else gap_char_candidates.pop()
    )
    alignment = align(target, src_string)
    stats, actions = get_editops_stats(alignment, gap_char)
    for k in expected_stats:
        assert stats[k] == expected_stats[k], (k, stats[k], expected_stats[k])


@pytest.mark.parametrize(
    "src_string, target, expected_stats, expected_substitutions",
    [
        (
            "a worn coat",
            "a wom coat",
            {
                "insert": 0,
                "delete": 0,
                "replace": 1,
                "spacing": 0,
                "total_chars": 11,
                "total_words": 3,
                "matching_chars": 9,
                "matching_words": 2,
                "matching_alnum_words": 2,
                "word_accuracy": 2 / 3,
                "char_accuracy": 9 / 11,
            },
            {("rn", "m"): 1},
        ),
        (
            "a c",
            "def",
            {
                "insert": 0,
                "delete": 0,
                "replace": 1,
                "spacing": 0,
                "total_chars": 3,
                "total_words": 1,
                "matching_chars": 0,
                "matching_words": 0,
                "matching_alnum_words": 0,
                "word_accuracy": 0,
                "char_accuracy": 0,
            },
            {("a c", "def"): 1},
        ),
        (
            "a",
            "a b",
            {
                "insert": 1,
                "delete": 0,
                "replace": 0,
                "spacing": 1,
                "total_chars": 3,
                "total_words": 2,
                "matching_chars": 1,
                "matching_words": 1,
                "matching_alnum_words": 1,
                "word_accuracy": 0.5,
                "char_accuracy": 1 / 3,
            },
            {},
        ),
        (
            "a b",
            "b",
            {
                "insert": 0,
                "delete": 1,
                "replace": 0,
                "spacing": 1,
                "total_chars": 3,
                "total_words": 1,
                "matching_chars": 1,
                "matching_words": 1,
                "matching_alnum_words": 1,
                "word_accuracy": 1,
                "char_accuracy": 1 / 3,
            },
            {},
        ),
        (
            "a b",
            "a",
            {
                "insert": 0,
                "delete": 1,
                "replace": 0,
                "spacing": 1,
                "total_chars": 3,
                "total_words": 1,
                "matching_chars": 1,
                "matching_words": 1,
                "matching_alnum_words": 1,
                "word_accuracy": 1,
                "char_accuracy": 1 / 3,
            },
            {},
        ),
        (
            "b ..",
            "a b ..",
            {
                "insert": 1,
                "delete": 0,
                "replace": 0,
                "spacing": 1,
                "total_chars": 6,
                "total_words": 3,
                "total_alnum_words": 2,
                "matching_chars": 4,
                "matching_words": 2,
                "matching_alnum_words": 1,
                "word_accuracy": 2 / 3,
                "char_accuracy": 4 / 6,
            },
            {},
        ),
        (
            "taxi  cab",
            "taxl c b",
            {
                "insert": 0,
                "delete": 1,
                "replace": 1,
                "spacing": 1,
                "total_chars": 9,
                "total_words": 3,
                "matching_chars": 6,
                "matching_words": 0,
                "matching_alnum_words": 0,
                "word_accuracy": 0,
                "char_accuracy": 6 / 9,
            },
            {("i", "l"): 1},
        ),
        (
            "taxl c b     ri de",
            "taxi  cab ride",
            {
                "insert": 1,
                "delete": 0,
                "replace": 1,
                "spacing": 6,
                "total_chars": 18,
                "total_words": 3,
                "matching_chars": 11,
                "matching_words": 0,
                "matching_alnum_words": 0,
                "word_accuracy": 0,
                "char_accuracy": 11 / 18,
            },
            {("l", "i"): 1},
        ),
        (
            "ab",
            "ac",
            {
                "insert": 0,
                "delete": 0,
                "replace": 1,
                "spacing": 0,
                "total_chars": 2,
                "total_words": 1,
                "matching_chars": 1,
                "matching_words": 0,
                "matching_alnum_words": 0,
                "word_accuracy": 0.0,
                "char_accuracy": 0.5,
            },
            {},
        ),
        (
            "a",
            "a",
            {
                "insert": 0,
                "delete": 0,
                "replace": 0,
                "spacing": 0,
                "total_chars": 1,
                "total_words": 1,
                "matching_chars": 1,
                "matching_words": 1,
                "matching_alnum_words": 1,
                "word_accuracy": 1.0,
                "char_accuracy": 1.0,
            },
            {},
        ),
        (
            "New York is big.",
            "N ewYork kis big.",
            {
                "insert": 1,
                "delete": 0,
                "replace": 0,
                "spacing": 2,
                "total_chars": 17,
                "total_words": 4,
                "matching_chars": 15,
                "matching_words": 1,
                "matching_alnum_words": 1,
                "word_accuracy": 1 / 4,
                "char_accuracy": 15 / 17,
            },
            {},
        ),
        (
            "B oston grea t",
            "Boston is great",
            {
                "insert": 1,
                "delete": 0,
                "replace": 0,
                "spacing": 3,
                "total_chars": 15,
                "total_words": 3,
                "matching_chars": 12,
                "matching_words": 0,
                "matching_alnum_words": 0,
                "word_accuracy": 0.0,
                "char_accuracy": 0.8,
            },
            {},
        ),
        (
            "New York is big.",
            "N ewyork kis big",
            {
                "insert": 1,
                "delete": 1,
                "replace": 1,
                "spacing": 2,
                "total_chars": 16,
                "total_words": 4,
                "matching_chars": 13,
                "matching_words": 0,
                "matching_alnum_words": 0,
                "word_accuracy": 0,
                "char_accuracy": 13 / 16,
            },
            {("Y", "y"): 1},
        ),
        (
            "dog",
            "d@g",
            {
                "insert": 0,
                "delete": 0,
                "replace": 1,
                "spacing": 0,
                "total_chars": 3,
                "total_words": 1,
                "total_alnum_words": 1,
                "matching_chars": 2,
                "matching_alnum_words": 0,
                "matching_words": 0,
                "alnum_word_accuracy": 0.0,
                "word_accuracy": 0.0,
                "char_accuracy": 2 / 3,
            },
            {("o", "@"): 1},
        ),
        (
            "some@one.com",
            "some@one.com",
            {
                "insert": 0,
                "delete": 0,
                "replace": 0,
                "spacing": 0,
                "total_chars": 12,
                "total_words": 1,
                "total_alnum_words": 1,
                "matching_chars": 12,
                "matching_alnum_words": 1,
                "matching_words": 1,
                "alnum_word_accuracy": 1.0,
                "word_accuracy": 1.0,
                "char_accuracy": 1.0,
            },
            {},
        ),
    ],
)
def test_align_stats(src_string, target, expected_stats, expected_substitutions):
    gap_char_candidates, input_char_set = _find_gap_char_candidates(
        [src_string], [target]
    )
    gap_char = (
        GAP_CHAR if GAP_CHAR in gap_char_candidates else gap_char_candidates.pop()
    )
    alignment = align(src_string, target, gap_char=gap_char)
    stats, substitution_dict = get_align_stats(alignment, src_string, target, gap_char)
    for k in expected_stats:
        assert stats[k] == expected_stats[k], (k, stats[k], expected_stats[k])
    for k in expected_substitutions:
        assert substitution_dict[k] == expected_substitutions[k], (
            substitution_dict,
            expected_substitutions,
        )


@pytest.mark.parametrize(
    "src_string, target, expected_stats, expected_substitutions, expected_actions",
    [
        (
            "ab",
            "a",
            {
                "insert": 0,
                "delete": 1,
                "replace": 0,
                "spacing": 0,
                "total_chars": 2,
                "total_words": 1,
                "total_alnum_words": 1,
                "matching_chars": 1,
                "matching_alnum_words": 0,
                "matching_words": 0,
                "alnum_word_accuracy": 0.0,
                "word_accuracy": 0.0,
                "char_accuracy": 1 / 2,
            },
            {},
            {1: "D"},
        ),
        (
            "ab",
            "abb",
            {
                "insert": 1,
                "delete": 0,
                "replace": 0,
                "spacing": 0,
                "total_chars": 3,
                "total_words": 1,
                "total_alnum_words": 1,
                "matching_chars": 2,
                "matching_alnum_words": 0,
                "matching_words": 0,
                "alnum_word_accuracy": 0.0,
                "word_accuracy": 0.0,
                "char_accuracy": 2 / 3,
            },
            {},
            {2: ("I", "b")},
        ),
        (
            "ab",
            "ac",
            {
                "insert": 0,
                "delete": 0,
                "replace": 1,
                "spacing": 0,
                "total_chars": 2,
                "total_words": 1,
                "total_alnum_words": 1,
                "matching_chars": 1,
                "matching_alnum_words": 0,
                "matching_words": 0,
                "alnum_word_accuracy": 0.0,
                "word_accuracy": 0.0,
                "char_accuracy": 1 / 2,
            },
            {("b", "c"): 1},
            {1: ("R", "c")},
        ),
        (
            "New York is big.",
            "N ewyork kis big",
            {
                "insert": 1,
                "delete": 1,
                "replace": 1,
                "spacing": 2,
                "total_chars": 16,
                "total_words": 4,
                "matching_chars": 13,
                "matching_words": 0,
                "matching_alnum_words": 0,
                "word_accuracy": 0,
                "char_accuracy": 13 / 16,
            },
            {("Y", "y"): 1},
            {1: ("I", " "), 4: "D", 5: ("R", "y"), 10: ("I", "k"), 17: "D"},
        ),
        (
            "dog",
            "d@g",
            {
                "insert": 0,
                "delete": 0,
                "replace": 1,
                "spacing": 0,
                "total_chars": 3,
                "total_words": 1,
                "total_alnum_words": 1,
                "matching_chars": 2,
                "matching_alnum_words": 0,
                "matching_words": 0,
                "alnum_word_accuracy": 0.0,
                "word_accuracy": 0.0,
                "char_accuracy": 2 / 3,
            },
            {("o", "@"): 1},
            {1: ("R", "@")},
        ),
        (
            "some@one.com",
            "some@one.com",
            {
                "insert": 0,
                "delete": 0,
                "replace": 0,
                "spacing": 0,
                "total_chars": 12,
                "total_words": 1,
                "total_alnum_words": 1,
                "matching_chars": 12,
                "matching_alnum_words": 1,
                "matching_words": 1,
                "alnum_word_accuracy": 1.0,
                "word_accuracy": 1.0,
                "char_accuracy": 1.0,
            },
            {},
            {},
        ),
    ],
)
def test_get_stats(
    src_string, target, expected_stats, expected_substitutions, expected_actions
):
    stats, substitution_dict, actions = get_stats(target, src_string)
    for k in expected_stats:
        assert stats[k] == expected_stats[k], (k, stats[k], expected_stats[k])
    for k in expected_substitutions:
        assert substitution_dict[k] == expected_substitutions[k], (
            substitution_dict,
            expected_substitutions,
        )
    for k in expected_actions:
        assert actions[k] == expected_actions[k], (k, actions[k], expected_actions[k])


@pytest.mark.parametrize(
    "src_string, target, expected_actions",
    [
        ("dog and cat", "g and at", {0: ("I", "d"), 1: ("I", "o"), 8: ("I", "c")}),
    ],
)
def test_actions_stats(src_string, target, expected_actions):
    gap_char_candidates, input_char_set = _find_gap_char_candidates(
        [src_string], [target]
    )
    gap_char = (
        GAP_CHAR if GAP_CHAR in gap_char_candidates else gap_char_candidates.pop()
    )
    alignment = align(target, src_string, gap_char=gap_char)
    _, actions = get_editops_stats(alignment, gap_char)
    print(actions)

    for k in expected_actions:
        assert actions[k] == expected_actions[k], (k, actions[k], expected_actions[k])
