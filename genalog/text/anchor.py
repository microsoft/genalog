# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# ---------------------------------------------------------

"""
Baseline alignment algorithm is slow on long documents.
The idea is to break down the longer text into smaller fragments
for quicker alignment on individual pieces. We refer "anchor words"
as these points of breakage.

The bulk of this algorithm is to identify these "anchor words".

This is an re-implementation of the algorithm in this paper
"A Fast Alignment Scheme for Automatic OCR Evaluation of Books"
(https://ieeexplore.ieee.org/document/6065412)

We rely on `genalog.text.alignment` to align the subsequences.
"""
import itertools
from collections import Counter

from genalog.text import alignment, preprocess
from genalog.text.alignment import GAP_CHAR
from genalog.text.lcs import LCS

# The recursively portion of the algorithm will run on
# segments longer than this value to find anchor points in
# the longer segment (to break it up further).
MAX_ALIGN_SEGMENT_LENGTH = 100  # in characters length


def get_unique_words(tokens, case_sensitive=False):
    """Get a set of unique words from a Counter dictionary of word occurrences

    Arguments:
        d (dict) : a Counter dictionary of word occurrences
        case_sensitive (bool, optional) : whether unique words are case sensitive.
                                          Defaults to False.

    Returns:
        set: a set of unique words (original alphabetical case of the word is preserved)
    """
    if case_sensitive:
        word_count = Counter(tokens)
        return {word for word, count in word_count.items() if count < 2}
    else:
        tokens_lowercase = [tk.lower() for tk in tokens]
        word_count = Counter(tokens_lowercase)
        return {tk for tk in tokens if word_count[tk.lower()] < 2}


def segment_len(tokens):
    """Get length of the segment

    Arguments:
        segment (list) : a list of tokens
    Returns:
        int : the length of the segment
    """
    return sum(map(len, tokens))


def get_word_map(unique_words, src_tokens):
    """Arrange the set of unique words by the order they original appear in the text

    Arguments:
        unique_words (set) : a set of unique words
        src_tokens (list) : a list of tokens

    Returns:
        list : a ``word_map``: a list of word corrdinate tuples ``(word, word_index)`` defined as follow:

        1. ``word`` is a typical word token
        2. ``word_index`` is the index of the word in the source token array
    """
    # Find the indices of the unique words in the source text
    unique_word_indices = map(src_tokens.index, unique_words)
    word_map = list(zip(unique_words, unique_word_indices))
    word_map.sort(key=lambda x: x[1])  # Re-arrange order by the index
    return word_map


def get_anchor_map(gt_tokens, ocr_tokens, min_anchor_len=2):
    """Find the location of anchor words in both the gt and ocr text.
    Anchor words are location where we can split both the source gt
    and ocr text into smaller text fragment for faster alignment.

    Arguments:
        gt_tokens (list) : a list of ground truth tokens
        ocr_tokens (list) : a list of tokens from OCR'ed document
        min_anchor_len (int, optional) : minimum len of the anchor word.
                                         Defaults to 2.

    Returns:
        tuple: a 2-element ``(anchor_map_gt, anchor_map_ocr)`` tuple:

    1. ``anchor_map_gt`` is a ``word_map`` that locates all the anchor words in the gt tokens
    2. ``anchor_map_gt`` is a ``word_map`` that locates all the anchor words in the ocr tokens

    And ``len(anchor_map_gt) == len(anchor_map_ocr)``

    ::

        For example:
            Input:
                gt_tokens:  ["b", "a", "c"]
                ocr_tokens: ["c", "b", "a"]
            Ourput:
                ([("b", 0), ("a", 1)], [("b", 1), ("a", 2)])

    """
    # 1. Get unique words common in both gt and ocr
    unique_words_gt = get_unique_words(gt_tokens)
    unique_words_ocr = get_unique_words(ocr_tokens)
    unique_words_common = unique_words_gt.intersection(unique_words_ocr)
    if not unique_words_common:
        return [], []

    # 2. Arrange the common unique words in their original order
    unique_word_map_gt = get_word_map(unique_words_common, gt_tokens)
    unique_word_map_ocr = get_word_map(unique_words_common, ocr_tokens)
    # Unzip to get the ordered unique_words
    ordered_unique_words_gt, _ = zip(*unique_word_map_gt)
    ordered_unique_words_ocr, _ = zip(*unique_word_map_ocr)
    # Join words into a space-separated string for finding LCS
    unique_words_gt_str = preprocess.join_tokens(ordered_unique_words_gt)
    unique_words_ocr_str = preprocess.join_tokens(ordered_unique_words_ocr)

    # 3. Find the LCS between the two ordered list of unique words
    lcs = LCS(unique_words_gt_str, unique_words_ocr_str)
    lcs_str = lcs.get_str()

    # 4. Break up the LCS string into tokens
    lcs_words = set(preprocess.tokenize(lcs_str))

    # 5. Anchor words are the unique words in the lcs string
    anchor_words = lcs_words.intersection(unique_words_common)

    # 6. Filter the unique words to keep the anchor words ONLY
    anchor_map_gt = list(
        filter(
            # This is a list of (unique_word, unique_word_index)
            lambda word_coordinate: word_coordinate[0] in anchor_words,
            unique_word_map_gt,
        )
    )
    anchor_map_ocr = list(
        filter(
            lambda word_coordinate: word_coordinate[0] in anchor_words,
            unique_word_map_ocr,
        )
    )
    return anchor_map_gt, anchor_map_ocr


def find_anchor_recur(
    gt_tokens,
    ocr_tokens,
    start_pos_gt=0,
    start_pos_ocr=0,
    max_seg_length=MAX_ALIGN_SEGMENT_LENGTH,
):
    """Recursively find anchor positions in the gt and ocr text

    Arguments:
        gt_tokens (list) : a list of ground truth tokens
        ocr_tokens (list) : a list of tokens from OCR'ed document
        start_pos (int, optional) : a constant to add to all the resulting indices.
                                    Defaults to 0.
        max_seg_length (int, optional) : trigger recursion if any text segment is larger than this.
                                         Defaults to ``MAX_ALIGN_SEGMENT_LENGTH``.

    Raises:
        ValueError: when there different number of anchor points in gt and ocr.

    Returns:
        tuple : two lists of token indices where each list is the position of the anchor in the input
        ``gt_tokens`` and ``ocr_tokens``
    """
    # 1. Try to find anchor words
    anchor_word_map_gt, anchor_word_map_ocr = get_anchor_map(gt_tokens, ocr_tokens)

    # 2. Check invariant
    if len(anchor_word_map_gt) != len(anchor_word_map_ocr):
        raise ValueError("Unequal number of anchor points across gt and ocr string")
    # Return empty if no anchor word found
    if len(anchor_word_map_gt) == 0:
        return [], []

    # 3. Unzip map to get indices of the anchor tokens
    _, anchor_indices_gt = map(list, zip(*anchor_word_map_gt))
    _, anchor_indices_ocr = map(list, zip(*anchor_word_map_ocr))

    output_gt_anchors = set(map(lambda x: x + start_pos_gt, anchor_indices_gt))
    output_ocr_anchors = set(map(lambda x: x + start_pos_ocr, anchor_indices_ocr))
    # 4. Find split point of each segment
    seg_start_gt = list(itertools.chain([0], anchor_indices_gt))
    seg_start_ocr = list(itertools.chain([0], anchor_indices_ocr))
    start_n_end_gt = zip(seg_start_gt, itertools.chain(anchor_indices_gt, [None]))
    start_n_end_ocr = zip(seg_start_ocr, itertools.chain(anchor_indices_ocr, [None]))
    gt_segments = [gt_tokens[start:end] for start, end in start_n_end_gt]
    ocr_segments = [ocr_tokens[start:end] for start, end in start_n_end_ocr]
    # 4. Loop through each segment
    for gt_seg, ocr_seg, gt_start, ocr_start in zip(
        gt_segments, ocr_segments, seg_start_gt, seg_start_ocr
    ):
        if (
            segment_len(gt_seg) > max_seg_length
            or segment_len(ocr_seg) > max_seg_length
        ):
            # recur on the segment in between the two anchors.
            # We assume the first token in the segment is an anchor word
            gt_anchors, ocr_anchors = find_anchor_recur(
                gt_seg[1:],
                ocr_seg[1:],
                start_pos_gt=gt_start + 1,
                start_pos_ocr=ocr_start + 1,
                max_seg_length=max_seg_length,
            )
            # shift the token indices
            # (these are indices of a subsequence and does not reflect true position in the source sequence)
            gt_anchors = set(map(lambda x: x + start_pos_gt, gt_anchors))
            ocr_anchors = set(map(lambda x: x + start_pos_ocr, ocr_anchors))
            # merge recursion results
            output_gt_anchors = output_gt_anchors.union(gt_anchors)
            output_ocr_anchors = output_ocr_anchors.union(ocr_anchors)

    return sorted(output_gt_anchors), sorted(output_ocr_anchors)


def align_w_anchor(gt, ocr, gap_char=GAP_CHAR, max_seg_length=MAX_ALIGN_SEGMENT_LENGTH):
    """A faster alignment scheme of two text segments. This method first
    breaks the strings into smaller segments with anchor words.
    Then these smaller segments are aligned.

    **NOTE:** this function shares the same contract as `genalog.text.alignment.align()`
    These two methods are interchangeable and their alignment results should be similar.

    ::

        For example:

            Ground Truth: "The planet Mars, I scarcely need remind the reader,"
            Noisy Text:   "The plamet Maris, I scacely neee remind te reader,"

            Here the unique anchor words are "I", "remind" and "reader".

            Thus, the algorithm will split into following segment pairs:

                "The planet Mar, "
                "The plamet Maris, "

                "I scarcely need "
                "I scacely neee "

                "remind the reader,"
                "remind te reader,"

            And run sequence alignment on each pair.

    Arguments:
        gt (str) : ground truth text
        noise (str) : text with ocr noise
        gap_char (str, optional) : gap char used in alignment algorithm . Defaults to GAP_CHAR.
        max_seg_length (int, optional) : maximum segment length. Segments longer than this threshold
            will continued be split recursively into smaller segment. Defaults to ``MAX_ALIGN_SEGMENT_LENGTH``.

    Returns:
        a tuple (str, str) of aligned ground truth and noise:
            (aligned_gt, aligned_noise)
    """
    gt_tokens = preprocess.tokenize(gt)
    ocr_tokens = preprocess.tokenize(ocr)

    # 1. Find anchor positions
    gt_anchors, ocr_anchors = find_anchor_recur(
        gt_tokens, ocr_tokens, max_seg_length=max_seg_length
    )

    # 2. Split into segments
    start_n_end_gt = zip(
        itertools.chain([0], gt_anchors), itertools.chain(gt_anchors, [None])
    )
    start_n_end_ocr = zip(
        itertools.chain([0], ocr_anchors), itertools.chain(ocr_anchors, [None])
    )
    gt_segments = [gt_tokens[start:end] for start, end in start_n_end_gt]
    ocr_segments = [ocr_tokens[start:end] for start, end in start_n_end_ocr]

    # 3. Run alignment on each segment
    aligned_segments_gt = []
    aligned_segments_ocr = []
    for gt_segment, noisy_segment in zip(gt_segments, ocr_segments):
        gt_segment = preprocess.join_tokens(gt_segment)
        noisy_segment = preprocess.join_tokens(noisy_segment)
        # Run alignment algorithm
        aligned_seg_gt, aligned_seg_ocr = alignment.align(
            gt_segment, noisy_segment, gap_char=gap_char
        )
        if aligned_seg_gt and aligned_seg_ocr:  # if not empty string ""
            aligned_segments_gt.append(aligned_seg_gt)
            aligned_segments_ocr.append(aligned_seg_ocr)

    # Stitch all segments together
    aligned_gt = " ".join(aligned_segments_gt)
    aligned_noise = " ".join(aligned_segments_ocr)

    return aligned_gt, aligned_noise
