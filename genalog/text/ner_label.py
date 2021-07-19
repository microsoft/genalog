# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# ---------------------------------------------------------

import itertools
import re
import string

from genalog.text import alignment, anchor
from genalog.text import preprocess

# Both regex below has the following behavior:
#   1. whitespace-tolerant at both ends of the string
#   2. separate the token into two groups:
#       For example, given a label 'B-PLACE'
#       Group 1 (denoted by \1): Label Indicator (B-)
#       Group 2 (denoted by \2): Label Name (PLACE)
MULTI_TOKEN_BEGIN_LABEL_REGEX = r"^\s*(B-)([a-z|A-Z]+)\s*$"
MULTI_TOKEN_INSIDE_LABEL_REGEX = r"^\s*(I-)([a-z|A-Z]+)\s*$"
MULTI_TOKEN_LABEL_REGEX = r"^\s*([B|I]-)([a-z|A-Z]+)\s*"

# To avoid confusion in the Python interpreter,
# gap char should not be any of the following special characters
SPECIAL_CHAR = set(
    " \t\n'\x0b''\x0c''\r'"
)  # Notice space characters (' ', '\t', '\n') are in this set.
GAP_CHAR_SET = set(string.printable).difference(SPECIAL_CHAR)
# GAP_CHAR_SET = '!"#$%&()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~'


class GapCharError(Exception):
    pass


def _is_begin_label(label):
    """ Return true if the NER label is a begin label (eg. B-PLACE) """
    return re.match(MULTI_TOKEN_BEGIN_LABEL_REGEX, label) is not None


def _is_inside_label(label):
    """ Return true if the NER label is an inside label (eg. I-PLACE) """
    return re.match(MULTI_TOKEN_INSIDE_LABEL_REGEX, label) is not None


def _is_multi_token_label(label):
    """ Return true if the NER label is a multi token label (eg. B-PLACE, I-PLACE) """
    return re.match(MULTI_TOKEN_LABEL_REGEX, label) is not None


def _clean_multi_token_label(label):
    """ Rid the multi-token-labels of whitespaces"""
    return re.sub(MULTI_TOKEN_LABEL_REGEX, r"\1\2", label)


def _convert_to_begin_label(label):
    """Convert an inside label, or I-label, (ex. I-PLACE) to a begin label, or B-Label, (ex. B-PLACE)

    Arguments:
        label (str) : an NER label

    Returns:
        an NER label. This method DOES NOT alter the label unless it is an inside label
    """
    if _is_inside_label(label):
        # Replace the Label Indicator to 'B-'(\1) and keep the Label Name (\2)
        return re.sub(MULTI_TOKEN_INSIDE_LABEL_REGEX, r"B-\2", label)
    return label


def _convert_to_inside_label(label):
    """Convert a begin label, or B-label, (ex. B-PLACE) to an inside label, or I-Label, (ex. B-PLACE)

    Arguments:
        label (str) : an NER label

    Returns:
        an NER label. This method DOES NOT alter the label unless it is a begin label
    """
    if _is_begin_label(label):
        # Replace the Label Indicator to 'I-'(\1) and keep the Label Name (\2)
        return re.sub(MULTI_TOKEN_BEGIN_LABEL_REGEX, r"I-\2", label)
    return label


def _is_missing_begin_label(begin_label, inside_label):
    """Validate a inside label given an begin label

    Arguments:
        begin_label (str) : a begin NER label used to
            check if the given label is part of a multi-token label
        inside_label (str) : an inside label to check for its validity

    Returns:
        True if the inside label paired with the begin_label. False otherwise.
        Also False if input is not an inside label
    """
    if not _is_inside_label(inside_label):
        return False

    if begin_label:
        # clean the two labels before comparison
        inside_label = _clean_multi_token_label(inside_label)
        begin_label = _clean_multi_token_label(begin_label)
        # convert inside label to a begin label for string comparison
        # True if the two labels have different names
        # (e.g. B-LOC followed by I-ORG, and I-ORG is missing a begin label)
        return _convert_to_begin_label(inside_label) != begin_label
    else:
        return True


def correct_ner_labels(labels):
    """Correct the given list of labels for the following case:

    1. Missing B-Label (i.e. I-PLACE I-PLACE -> B-PLACE I-PLACE)

    Arguments:
        labels (list) : list of NER labels

    Returns:
        a list of NER labels
    """
    cur_begin_label = ""
    for i, label in enumerate(labels):
        if _is_multi_token_label(label):
            if _is_begin_label(label):
                cur_begin_label = label
            # else is an inside label, so we check if it's missing a begin label
            else:
                if _is_missing_begin_label(cur_begin_label, label):
                    labels[i] = _convert_to_begin_label(label)
                    # Update current begin label
                    cur_begin_label = labels[i]
        else:
            cur_begin_label = ""
    return labels


def _select_from_multiple_ner_labels(label_indices):
    """Private method to select a NER label from a list of candidate

    Note: this method is used to tackle the issue when multiple gt tokens
    are aligned to ONE ocr_token

    For example:

        gt_labels:  B-p   I-p    O   O
                     |     |     |   |
            gt:     New   York   is big
                     |      \\   /   |
            ocr:    New     Yorkis  big
                     |        |      |
       ocr_labels:  B-p      I-p     O

    We need to decide whether the token "Yorkis" should be labeled as "I-place", "o" or both.
    Currently the FIRST label takes precedence.

    Arguments:
        label_indices (list) : a list of token indices

    Returns:
        a specific index
    """
    # TODO: may need a more sophisticated way to select from multiple NER labels
    return label_indices[0]


def _find_gap_char_candidates(gt_tokens, ocr_tokens):
    """Find a set of suitable GAP_CHARs based not in the set of input characters

    Arguments:
        gt_tokens (list) : a list of tokens
        ocr_tokens (list) : a list of tokens

    Returns:
        (set, set) -- a 2-element tuple of
            1. the set of suitable GAP_CHARs
            2. the set of input characters
    """
    input_char_set = set(
        "".join(itertools.chain(gt_tokens, ocr_tokens))
    )  # The set of input characters
    gap_char_set = GAP_CHAR_SET  # The set of possible GAP_CHARs
    # Find a set of gap_char that is NOT in the set of input characters
    gap_char_candidates = gap_char_set.difference(input_char_set)
    return gap_char_candidates, input_char_set


def propagate_label_to_ocr(gt_labels, gt_tokens, ocr_tokens, use_anchor=True):
    """Propagate NER label for ground truth tokens to to ocr tokens.

        NOTE that `gt_tokens` and `ocr_tokens` MUST NOT contain invalid tokens.
            Invalid tokens are:
                1. non-atomic tokens, or space-separated string ("New York")
                3. empty string ("")
                4. string with spaces ("  ")

    Arguments:
        gt_labels (list) : a list of NER label for ground truth token
        gt_tokens (list) : a list of ground truth string tokens
        ocr_tokens (list) : a list of OCR'ed text tokens
        gap_char (char, optional) : gap char used in alignment algorithm. Defaults to ``alignment.GAP_CHAR``.
        use_anchor (bool, optional) : use faster alignment method with anchors if set to True. Defaults to True.

    Raises:
        GapCharError:
            when the set of input character is EQUAL
            to set of all possible gap characters (GAP_CHAR_SET)

    Returns:
        tuple : a tuple of 3 elements ``(ocr_labels, aligned_gt, aligned_ocr, gap_char)`` where
        1. ``ocr_labels`` is a list of NER label for the corresponding ocr tokens
        2. ``aligned_gt`` is the ground truth string aligned with the ocr text
        3. ``aligned_ocr`` is the ocr text aligned with ground true
        4. ``gap_char`` is the char used to alignment for inserting gaps
    """
    # Find a set of suitable GAP_CHAR based not in the set of input characters
    gap_char_candidates, input_char_set = _find_gap_char_candidates(
        gt_tokens, ocr_tokens
    )
    if len(gap_char_candidates) == 0:
        raise GapCharError(
            "Exhausted all possible GAP_CHAR candidates for alignment."
            + " Consider reducing cardinality of the input character set.\n"
            + f"The set of possible GAP_CHAR candidates is: '{''.join(sorted(GAP_CHAR_SET))}'\n"
            + f"The set of input character is: '{''.join(sorted(input_char_set))}'"
        )
    else:
        if alignment.GAP_CHAR in gap_char_candidates:
            gap_char = alignment.GAP_CHAR  # prefer to use default GAP_CHAR
        else:
            gap_char = gap_char_candidates.pop()
        return _propagate_label_to_ocr(
            gt_labels, gt_tokens, ocr_tokens, gap_char=gap_char, use_anchor=use_anchor
        )


def _propagate_label_to_ocr(
    gt_labels, gt_tokens, ocr_tokens, gap_char=alignment.GAP_CHAR, use_anchor=True
):
    r"""Propagate NER label for ground truth tokens to to ocr tokens. Low level implementation

        NOTE: that `gt_tokens` and `ocr_tokens` MUST NOT contain invalid tokens.
        Invalid tokens are:
        1. non-atomic tokens, or space-separated string ("New York")
        2. multiple occurrences of the GAP_CHAR ('@@@')
        3. empty string ("")
        4. string with spaces ("  ")

    ::

        Case Analysis:
        ******************************** MULTI-TOKEN-LABELS ********************************

                    Case 1:         Case 2:         Case 3:         Case 4:         Case 5:
                    one-to-many     many-to-one     many-to-many    missing tokens  missing tokens
                                                   (Case 1&2 comb)  (I-label)       (B-label)
        gt label     B-p    I-p      B-p I-p        B-p   I-p       B-p  I-p        B-p  I-p  I-p
                      |      |        |   |          |     |         |    |          |   |     |
        gt_token     New    York     New York       New  York       New York        New York City
                     / \    / \        \ /           /\   /          |                   |     |
       ocr_token    N   ew Yo  rk    NewYork        N ew@York       New                 York City
                    |   |   |   |       |           |    |           |                   |     |
       ocr label   B-p I-p I-p I-p     B-p          B-p I-p         B-p                 B-p   I-p

        ******************************** SINGLE-TOKEN-LABELS ********************************

                    Case 1:         Case 2:         Case 3:         Case 4:
                    one-to-many     many-to-one     many-to-many    missing tokens
                                                   (Case 1&2 comb)
        gt label         O           V    O          O   V   W       O   O
                         |           |    |          |   |   |       |   |
        gt_token     something       is  big       this is huge      is big
                     / \    \          \ /          /\  /\ /         |
       ocr_token    so  me  thing     isbig       th isi shuge       is
                    |   |     |         |          |  |    |         |
       ocr label    o   o     o         V          O  O    V         O

    Arguments:
        gt_labels (list) : a list of NER label for ground truth token
        gt_tokens (list) : a list of ground truth string tokens
        ocr_tokens (list) : a list of OCR'ed text tokens
        gap_char (char, optional) : gap char used in alignment algorithm . Defaults to ``alignment.GAP_CHAR``.
        use_anchor (bool, optional) : use faster alignment method with anchors if set to True.
                            Defaults to True.
    Raises:
        ValueError: when
        1. there is unequal number of gt_tokens and gt_labels
        2. there is a non-atomic token in gt_tokens or ocr_tokens
        3. there is an empty string in gt_tokens or ocr_tokens
        4. there is a token full of space characters only in gt_tokens or ocr_tokens
        5. gt_to_ocr_mapping has more tokens than gt_tokens
        GapCharError: when
        1. there is a token consisted of GAP_CHAR only


    Returns:
        a tuple of 4 elements: (ocr_labels, aligned_gt, aligned_ocr, gap_char)
        where
        `ocr_labels` is a list of NER label for the corresponding ocr tokens
        `aligned_gt` is the ground truth string aligned with the ocr text
        `aligned_ocr` is the ocr text aligned with ground true
        `gap_char` is the char used to alignment for inserting gaps

    For example, given input:

    >>> _propagate_label_to_ocr(
        ["B-place", "I-place", "o", "o"],
        ["New", "York", "is", "big"],
        ["N", "ewYork", "big"]
    )
    (["B-place", "I-place", "o"], "N@ew York is big", "N ew@York@@@ big", '@')

    """
    # Pseudo-algorithm:

    #                                             ocr_to_gt_mapping = [
    # gt_labels:   B-P I-P  I-P  O  O  B-P I-P          [1, 2], ('YorkCity' maps to 'York' and 'City')
    #               |   |    |   |  |  |   |            [3],    ('i' maps to 'is')
    # gt_txt:     "New York City is in New York"        [3, 4], ('sin' maps to 'is' and 'in')
    #                     \/     /\  |  /\              [5],    ('N' maps to 'New')
    # ocr_txt:        "YorkCity  i sin N ew"            [5]     ('ew' maps to 'New)
    #                     |      |  |  |  |            ]
    #                    I-P     O  O B-P B-P

    # STEP 1: naively propagate NER label based on text-alignment
    #   ** If a ocr token is made of two or more gt tokens, the ocr token
    #      takes the label from the FIRST gt token.
    #            Please see '_select_from_multiple_ner_labels()' from above
    #   ** If gt token is splitted into two of more ocr token, ALL ocr tokens
    #      share the same gt label
    #

    #                                             gt_to_ocr_mapping = [
    # gt_labels:   B-P I-P  I-P  O  O  B-P I-P          [],     ('New' does not map to any ocr token)
    #               |   |    |   |  |  |   |            [0],    ('York' maps to 'YorkCity')
    # gt_txt:     "New York City is in New York"        [0],    ('City' maps to 'YorkCity')
    #                     \/     /\  |  /\              [1, 2], ('is' maps to 'i' and 'sin')
    # ocr_txt:        "YorkCity  i sin N ew"            [2],    ('in' maps to 'sin)
    #                     |      |  |  |  |             [3,4],  ('New' maps to 'N' and 'ew')
    #                    I-P     O  O B-P B-P           []      ('York' does not map to any ocr token)
    #                                                 ]

    # STEP 2, clean up corner cases from multi-token-labels
    #   ** At this point, Step 1 should've taken care all single-token-label cases
    #   ** We need to correct the following corner cases with multi-token-labels
    #       1. Trailing B-labels (MULTI-TOKEN-LABELS Case 1)
    #           Ex: B-PLACE B-PLACE
    #                  N        ew
    #       2. Missing B-label (MULTI-TOKEN-LABELS Case 5)
    #           Ex: I-PLACE
    #               YorkCity

    # We can address MULTI-TOKEN-LABELS Case 1 with following pseudo-algorithm:
    # 1. For each gt_token in gt_to_ocr_mapping:
    # 1. If the gt_token is mapped to 2 or more ocr_tokens AND the gt_token has a B-label
    # 1. For all the ocr_tokens this gt_token mapped to
    # 1. Keep the B-label for the 1st ocr_token
    # 2. For the rest of the ocr_token, convert the B-label to an I-label

    # We can address the MULTI-TOKEN-LABELS Case 5 with the '_correct_ner_labels()' method

    # Sanity check:
    if len(gt_tokens) != len(gt_labels):
        raise ValueError(
            f"Unequal number of gt_tokens ({len(gt_tokens)})"
            + f"to that of gt_labels ({len(gt_labels)})"
        )

    for tk in gt_tokens + ocr_tokens:
        if len(preprocess.tokenize(tk)) > 1:
            raise ValueError(f"Invalid token '{tk}'. Tokens must be atomic.")
        if not alignment._is_valid_token(tk, gap_char=gap_char):
            if re.search(rf"{re.escape(gap_char)}+", tk):  # Escape special regex chars
                raise GapCharError(
                    f"Invalid token '{tk}'. Tokens cannot be a chain repetition of the GAP_CHAR '{gap_char}'"
                )
            else:
                raise ValueError(
                    f"Invalid token '{tk}'. Tokens cannot be an empty string or a mix of space characters (spaces, tabs, newlines)"
                )

    # Stitch tokens together into one string for alignment
    gt_txt = preprocess.join_tokens(gt_tokens)
    ocr_txt = preprocess.join_tokens(ocr_tokens)
    # Align the ground truth and ocr text first
    if use_anchor:
        aligned_gt, aligned_ocr = anchor.align_w_anchor(
            gt_txt, ocr_txt, gap_char=gap_char
        )
    else:
        aligned_gt, aligned_ocr = alignment.align(gt_txt, ocr_txt, gap_char=gap_char)
    gt_to_ocr_mapping, ocr_to_gt_mapping = alignment.parse_alignment(
        aligned_gt, aligned_ocr, gap_char=gap_char
    )
    # Check invariant
    if len(gt_to_ocr_mapping) != len(gt_tokens):
        raise ValueError(
            "Alignment modified number of gt_tokens. aligned_gt_tokens to gt_tokens: "
            + f"{len(gt_to_ocr_mapping)}:{len(gt_tokens)}. \nCheck alignment.parse_alignment()."
        )

    ocr_labels = []
    # STEP 1: naively propagate NER label based on text-alignment
    for ocr_to_gt_token_relationship in ocr_to_gt_mapping:
        # if is not mapping to missing a token (Case 4)
        if ocr_to_gt_token_relationship:
            # Find the corresponding gt_token it is aligned to
            ner_label_index = _select_from_multiple_ner_labels(
                ocr_to_gt_token_relationship
            )
            # Get the NER label for that particular gt_token
            ocr_labels.append(gt_labels[ner_label_index])

    # STEP 2a: resolve MULTI-TOKEN-LABELS Case 1 Trailing B-label)
    for gt_token_index, gt_to_ocr_token_relationship in enumerate(gt_to_ocr_mapping):
        num_connections = len(gt_to_ocr_token_relationship)
        gt_token_label = gt_labels[gt_token_index]
        if num_connections > 1 and _is_begin_label(gt_token_label):
            for connection_index in range(1, num_connections):
                ocr_token_index = gt_to_ocr_token_relationship[connection_index]
                # Get the current label for ocr token
                cur_ocr_label = ocr_labels[ocr_token_index]
                ocr_labels[ocr_token_index] = _convert_to_inside_label(cur_ocr_label)

    # STEP 2b: resolve MULTI-TOKEN-LABELS Case 5 (Missing B-label)
    ocr_labels = correct_ner_labels(ocr_labels)

    return ocr_labels, aligned_gt, aligned_ocr, gap_char


def format_labels(tokens, labels, label_top=True):
    """Format tokens and their NER label for display

    Arguments:
        tokens (list) : a list of word tokens
        labels (list) : a list of NER labels
        label_top (bool, optional) : True if label is place on top of the token.
                                     Defaults to True.

    Returns:
        a str with NER label align to the token it is labeling

    ::

        Given inputs:
            tokens: ["New", "York", "is", "big"]
            labels: ["B-place", "I-place", "o", "o"]
            label_top: True

        Outputs:
            \"B-place I-place o  o \"
            \"New     York    is big\"


    """
    formatted_tokens = ""
    formatted_labels = ""
    token_label_pair = zip(labels, tokens)
    for label, token in token_label_pair:
        # find the length difference
        len_diff = abs(len(label) - len(token))
        # Add padding spaces for whichever is shorter
        if len(label) > len(token):
            formatted_labels += label + " "
            formatted_tokens += token + " " * len_diff + " "
        else:
            formatted_labels += label + " " * len_diff + " "
            formatted_tokens += token + " "
    if label_top:
        return formatted_labels + "\n" + formatted_tokens + "\n"
    else:
        return formatted_tokens + "\n" + formatted_labels + "\n"


def format_label_propagation(
    gt_tokens,
    gt_labels,
    ocr_tokens,
    ocr_labels,
    aligned_gt,
    aligned_ocr,
    show_alignment=True,
):
    """Format label propagation for display

    Arguments:
        gt_tokens (list) : list of ground truth tokens
        gt_labels (list) : list of NER labels for ground truth tokens
        ocr_tokens (list) : list of OCR'ed text tokens
        ocr_labels (list) : list of NER labels for the OCR'ed tokens
        aligned_gt (str) : ground truth string aligned with the OCR'ed text
        aligned_ocr (str) : OCR'ed text aligned with ground truth
        show_alignment (bool, optional) : if true, show alignment result . Defaults to True.

    Returns:
        str: a string formatted for display as follows:

    .. code-block:: python

        if show_alignment:

            "B-PLACE I-PLACE V  O"      # [gt_labels]
            "New     York    is big"    # [gt_txt]
            "New York is big"           # [aligned_gt]
            "||||....|||||||"
            "New @@@@ is big"           # [aligned_ocr]
            "New     is big "           # [ocr_txt]
            "B-PLACE V  O   "           # [ocr_labels]

        else:

            "B-PLACE I-PLACE V  O"     # [gt_labels]
            "New     York    is big"   # [gt_txt]
            "New     is big"           # [ocr_txt]
            "B-PLACE V  O"             # [ocr_labels]

    """

    gt_label_str = format_labels(gt_tokens, gt_labels)
    label_str = format_labels(ocr_tokens, ocr_labels, label_top=False)
    if show_alignment:
        alignment_str = alignment._format_alignment(aligned_gt, aligned_ocr)
        return gt_label_str + alignment_str + label_str
    else:
        return gt_label_str + label_str
