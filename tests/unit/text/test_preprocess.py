import pytest

from genalog.text import preprocess
from genalog.text.alignment import GAP_CHAR


@pytest.mark.parametrize(
    "token, replacement, desired_output",
    [
        ("", "_", ""),  # Do nothing to empty string
        (" ", "_", " "),  # Do nothing to whitespaces
        (" \n\t", "_", " \n\t"),
        ("ascii", "_", "ascii"),
        ("a s\nc\tii", "_", "a s\nc\tii"),
        ("ascii·", "_", "ascii"),  # Tokens with non-ASCII values
        ("·", "_", "_"),  # Tokens with non-ASCII values
    ],
)
def test_remove_non_ascii(token, replacement, desired_output):
    for code in range(128, 1000):  # non-ASCII values
        token.replace("·", chr(code))
        output = preprocess.remove_non_ascii(token, replacement)
        assert output == desired_output


@pytest.mark.parametrize(
    "s, desired_output",
    [
        (" New  \t \n", ["New"]),
        # Mixed in gap char "@"
        (" @ @", ["@", "@"]),
        ("New York is big", ["New", "York", "is", "big"]),
        # Mixed multiple spaces and tabs
        (" New  York \t is  \t  big", ["New", "York", "is", "big"]),
        # Mixed in punctuation
        ("New .York is, big !", ["New", ".York", "is,", "big", "!"]),
        # Mixed in gap char "@"
        ("@N@ew York@@@is,\t  big@@@@@", ["@N@ew", "York@@@is,", "big@@@@@"]),
    ],
)
def test_tokenize(s, desired_output):
    output = preprocess.tokenize(s)
    assert output == desired_output


@pytest.mark.parametrize(
    "tokens, desired_output",
    [
        (
            ["New", "York", "is", "big"],
            "New York is big",
        ),
        # Mixed in punctuation
        (
            ["New", ".York", "is,", "big", "!"],
            "New .York is, big !",
        ),
        # Mixed in gap char "@"
        (
            ["@N@ew", "York@@@is,", "big@@@@@"],
            "@N@ew York@@@is, big@@@@@",
        ),
    ],
)
def test_join_tokens(tokens, desired_output):
    output = preprocess.join_tokens(tokens)
    assert output == desired_output


@pytest.mark.parametrize(
    "c, desired_output",
    [
        # Gap char
        (GAP_CHAR, False),
        # Alphabet char
        ("a", False),
        ("A", False),
        # Punctuation
        (".", False),
        ("!", False),
        (",", False),
        ("-", False),
        # Token separators
        (" ", True),
        ("\n", True),
        ("\t", True),
    ],
)
def test__is_spacing(c, desired_output):
    assert desired_output == preprocess._is_spacing(c)


@pytest.mark.parametrize(
    "text, desired_output",
    [
        ("", ""),
        ("w .", "w ."),
        ("w !", "w !"),
        ("w ?", "w ?"),
        ("w /.", "w /."),
        ("w /!", "w /!"),
        ("w /?", "w /?"),
        ("w1 , w2 .", "w1 , w2 ."),
        ("w1 . w2 .", "w1 . \nw2 ."),
        ("w1 /. w2 /.", "w1 /. \nw2 /."),
        ("w1 ! w2 .", "w1 ! \nw2 ."),
        ("w1 /! w2 /.", "w1 /! \nw2 /."),
        ("w1 ? w2 .", "w1 ? \nw2 ."),
        ("w1 /? w2 /.", "w1 /? \nw2 /."),
        ("U.S. . w2 .", "U.S. . \nw2 ."),
        ("w1 ??? w2 .", "w1 ??? w2 ."),  # not splitting
        ("w1 !!! w2 .", "w1 !!! w2 ."),
        ("w1 ... . w2 .", "w1 ... . \nw2 ."),
        ("w1 ... /. w2 /.", "w1 ... /. \nw2 /."),
        ("w1 /. /. w2 .", "w1 /. /. \nw2 ."),
        ("w1 /. /.", "w1 /. \n/."),
        ("w1 /. /. ", "w1 /. /. \n"),
        ("w1 ? ? ? ? w2 .", "w1 ? ? ? ? \nw2 ."),
        ("w1 /? /? /? /? w2 /.", "w1 /? /? /? /? \nw2 /."),
        ("w1 ! ! ! ! w2 .", "w1 ! ! ! ! \nw2 ."),
        ("w1 /! /! /! /! w2 /.", "w1 /! /! /! /! \nw2 /."),
    ],
)
def test_split_sentences(text, desired_output):
    assert desired_output == preprocess.split_sentences(text)


@pytest.mark.parametrize(
    "token, desired_output",
    [
        ("", False),
        (" ", False),
        ("\n", False),
        ("\t", False),
        (" \n \t", False),
        ("...", False),
        ("???", False),
        ("!!!", False),
        (".", True),
        ("!", True),
        ("?", True),
        ("/.", True),
        ("/!", True),
        ("/?", True),
    ],
)
def test_is_sentence_separator(token, desired_output):
    assert desired_output == preprocess.is_sentence_separator(token)
