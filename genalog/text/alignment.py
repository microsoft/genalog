# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# ---------------------------------------------------------

import re

from Bio import pairwise2

from genalog.text.preprocess import _is_spacing, tokenize

# Configuration params for global sequence alignment algorithm (Needleman-Wunsch)
MATCH_REWARD = 1
GAP_PENALTY = -0.5
GAP_EXT_PENALTY = -0.5
MISMATCH_PENALTY = -0.5
GAP_CHAR = "@"
ONE_ALIGNMENT_ONLY = False
SPACE_MISMATCH_PENALTY = 0.1


def _join_char_list(alignment_tuple):
    """ Post-process alignment results for unicode support """
    gt_char_list, noise_char_list, score, start, end = alignment_tuple
    return "".join(gt_char_list), "".join(noise_char_list), score, start, end


def _align_seg(
    gt,
    noise,
    match_reward=MATCH_REWARD,
    mismatch_pen=MISMATCH_PENALTY,
    gap_pen=GAP_PENALTY,
    gap_ext_pen=GAP_EXT_PENALTY,
    space_mismatch_penalty=SPACE_MISMATCH_PENALTY,
    gap_char=GAP_CHAR,
    one_alignment_only=ONE_ALIGNMENT_ONLY,
):
    """Wrapper function for Bio.pairwise2.align.globalms(), which
    calls the sequence alignment algorithm (Needleman-Wunsch)

    Arguments:
        gt (str) : a ground truth string
        noise (str) : a string with ocr noise
        match_reward (int, optional) : reward for matching characters. Defaults to ``MATCH_REWARD``.
        mismatch_pen (int, optional) : penalty for mistmatching characters. Defaults to ``MISMATCH_PENALTY``.
        gap_pen      (int, optional) : penalty for creating a gap. Defaults to ``GAP_PENALTY``.
        gap_ext_pen  (int, optional) : penalty for extending a gap. Defaults to ``GAP_EXT_PENALTY``.

    Returns:
        list : a list of alignment tuples. Each alignment tuple
        is one possible alignment candidate.

        A tuple (str, str, int, int, int) contains the following information:
            (aligned_gt, aligned_noise, alignment_score, alignment_start, alignment_end)

        Example:
            [
                ("alignm@ent", "alignrnent", 10, 0, 10),
                ("align@ment", "alignrnent", 10, 0, 10),
                ...
            ]
    """

    def match_reward_fn(x, y):
        if x == y:
            return match_reward
        elif x == " " or y == " ":
            # mismatch of a character with a space get a stronger penalty
            return mismatch_pen - space_mismatch_penalty
        else:
            return mismatch_pen

    # NOTE: Work-around to enable support full Unicode character set - passing string as a list of characters
    alignments = pairwise2.align.globalcs(
        list(gt),
        list(noise),
        match_reward_fn,
        gap_pen,
        gap_ext_pen,
        gap_char=[gap_char],
        one_alignment_only=ONE_ALIGNMENT_ONLY,
    )
    # Alignment result is a list of char instead of string because of the work-around
    return list(map(_join_char_list, alignments))


def _select_alignment_candidates(alignments, target_num_gt_tokens):
    """Return an alignment that contains the desired number
    of ground truth tokens from a list of possible alignments

    Case Analysis:
        Invariant 1: aligned strings are equal in length. This should
                     be guaranteed by the nature of text alignment.
        Invariant 2: we should not expect alignment introducing
                     additional ground truth tokens.
            However, in some cases, the alignment algorithm can
            introduce a group of GAP_CHARs as a separate token at the
            end of string, especially if there are lingering whitespaces.
                E.g:
                    gt: "Boston is big "  (num_tokens = 3)
                 noise: "B oston bi g"
            aligned_gt: "B@oston is big @" (num_tokens = 4)
         aligned_noise: "B oston @@@bi@ g"

        Remember, the example above is just one out of the many possible alignment
        candidates, and we need to search for the one with the target number of gt_tokens
                E.g:
                    gt: "Boston is big "   (num_tokens = 3)
                 noise: "B oston bi g"
            aligned_gt: "B@oston is bi@g " (num_tokens = 3)
         aligned_noise: "B oston @@@bi g@"

        This method is to search for such candidate that satisfy the invariant.

    Arguments:
        alignments (list) : a list of alignment tuples as follows:
                            [(str1, str2, alignment_score, alignment_start, alignment_end), (str1, str2, ...), ...]
        target_num_gt_tokens (int) : the number of token in the aligned ground truth string should have

    Raises:
        ValueError: raises this error if
        1. all the alignment candidates does NOT have the target number of tokens OR
        2. the aligned strings (str1 and str2) in the selected candidate are NOT EQUAL in length

    Returns:
        an alignment tuple (str, str, int, int, int) with following information:
            (str1, str2, alignment_score, alignment_start, alignment_end)
    """
    for alignment in alignments:
        aligned_gt = alignment[0]
        aligned_noise = alignment[1]
        num_aligned_gt_tokens = len(tokenize(aligned_gt))
        # Invariant 2
        if num_aligned_gt_tokens == target_num_gt_tokens:
            # Invariant 1
            if len(aligned_gt) != len(aligned_noise):
                raise ValueError(
                    f"Aligned strings are not equal in length: \naligned_gt: '{aligned_gt}'\naligned_noise '{aligned_noise}'\n"
                )
            # Returns the FIRST candidate that satisfies the invariant
            return alignment

    raise ValueError(
        f"No alignment candidates with {target_num_gt_tokens} tokens. Total candidates: {len(alignments)}"
    )


def align(gt, noise, gap_char=GAP_CHAR):
    """Align two text segments via sequence alignment algorithm

    **NOTE**: this algorithm is O(N^2) and is NOT efficient for longer text.
    Please refer to `genalog.text.anchor` for faster alignment on longer strings.

    Arguments:
        gt (str) : ground true text (should not contain GAP_CHAR)
        noise (str) : str with ocr noise (should not contain GAP_CHAR)
        gap_char (char, optional) : gap char used in alignment algorithm (default: GAP_CHAR)

    Returns:
        tuple(str, str) : a tuple of aligned ground truth and noise

    Invariants:
        The returned aligned strings will satisfy the following invariants:

        1. ``len(aligned_gt) == len(aligned_noise)``
        2. ``number of tokens in gt == number of tokens in aligned_gt``

    Example:
    ::

                    gt: "New York is big" (num_tokens = 4)
            aligned_gt: "N@ew @@York @is big@@" (num_tokens = 4)

    """
    if not gt and not noise:  # Both inputs are empty string
        return "", ""
    elif not gt:  # Either is empty
        return gap_char * len(noise), noise
    elif not noise:
        return gt, gap_char * len(gt)
    else:
        num_gt_tokens = len(tokenize(gt))
        alignments = _align_seg(gt, noise, gap_char=gap_char)
        try:
            aligned_gt, aligned_noise, _, _, _ = _select_alignment_candidates(
                alignments, num_gt_tokens
            )
        except ValueError as e:
            raise ValueError(
                f"Error with input strings '{gt}' and '{noise}': \n{str(e)}"
            )
        return aligned_gt, aligned_noise


def _format_alignment(align1, align2):
    """Wrapper function for Bio.pairwise2.format_alignment()

    Arguments:
        align1 (str) : alignment str
        align2 (str) : second str for alignment

    Returns:
        a string with formatted alignment.
            '|' is for matching character
            '.' is for substition
            '-' indicates gap

        For example:
            "
            New York is big.
            |||||.|| |||||||
            New Yerk@is big.
            "
    """
    formatted_str = pairwise2.format_alignment(
        align1, align2, 0, 0, len(align1), full_sequences=True
    )
    # Remove the "Score=0" from the str
    formatted_str_no_score = formatted_str.replace("\n  Score=0", "")
    return formatted_str_no_score


def _find_token_start(s, index):
    """Find the position of the start of token

    Arguments:
        s (str) : string to search in
        index (int) : index to begin search from

    Returns:
        - position {int} of the first non-whitespace character

    Raises:
        ValueError: if input s is an empty string
        IndexError: if is out-of-bound index
    """
    max_index = len(s) - 1
    if len(s) == 0:
        raise ValueError("Cannot search in an empty string")
    if index > max_index:
        raise IndexError(f"Out-of-bound index: {index} in string: {s}")

    while index < max_index and _is_spacing(s[index]):
        index += 1
    return index


def _find_token_end(s, index):
    """Find the position of the end of a token

    *** Important ***
        This method ALWAYS return index within the bound of the string.
        So, for single character string (eg. "c"), it will return 0.

    Arguments:
        s (str) : string to search in
        index (int) : index to begin search from

    Returns:
        - position {int} of the first non-whitespace character

    Raises:
        ValueError: if input s is an empty string
        IndexError: if is out-of-bound index
    """
    max_index = len(s) - 1
    if len(s) == 0:
        raise ValueError("Cannot search in an empty string")
    if index > max_index:
        raise IndexError(f"Out-of-bound index: {index} in string: {s}")

    while index < max_index and not _is_spacing(s[index]):
        index += 1
    return index


def _find_next_token(s, start):
    """Return the start and end index of a token in a string

    *** Important ***
        This method ALWAYS return indices within the bound of the string.
        So, for single character string (eg. "c"), it will return (0,0)

    Arguments:
        s (str) : the string to search token in
        start (int) : the starting index to start search in

    Returns:
        a tuple of (int, int) responding to the start and end indices of
        a token in the given s.
    """

    token_start = _find_token_start(s, start)
    token_end = _find_token_end(s, token_start)
    return token_start, token_end


def _is_valid_token(token, gap_char=GAP_CHAR):
    """Returns true if token is valid (i.e. compose of non-gap characters)
        Invalid tokens are
            1. multiple occurrences of the GAP_CHAR (e.g. '@@@')
            2. empty string ("")
            3. string with spaces ("  ")

        **Important: this method expects one token and not multiple space-separated tokens

    Arguments:
        token (str) : input string token
        gap_char (char, optional) : gap char used in alignment algorithm. Defaults to GAP_CHAR.

    Returns:
        bool : True if is a valid token, false otherwise
    """
    # Matches multiples of 'gap_char' that are padded with whitespace characters on either end
    INVALID_TOKEN_REGEX = (
        rf"^\s*{re.escape(gap_char)}*\s*$"  # Escape special regex chars
    )
    return not re.match(INVALID_TOKEN_REGEX, token)


def parse_alignment(aligned_gt, aligned_noise, gap_char=GAP_CHAR):
    r"""Parse alignment to pair ground truth tokens with noise tokens
    ::

                    Case 1:         Case 2:         Case 3:         Case 4:         Case 5:
                    one-to-many     many-to-one     many-to-many    missing tokens  one-to-one
              gt    "New York"      "New York"      "New York"      "New York"      "New York"
                      |   |           |   |           |   |           |   |           |   |
       aligned_gt   "New Yo@rk"     "New York"      "N@ew York"     "New York"      "New York"
                      |   /\           \/             /\/             |   |           |   |
     aligned_noise  "New Yo rk"     "New@York"      "N ew@York"     "New @@@@"      "New York"
                      |   | |           |            |    |           |               |   |
            noise   "New Yo rk"     "NewYork"       "N ewYork"      "New"           "New York"

    Arguments:
        aligned_gt (str) : ground truth string aligned with the nose string
        aligned_noise (str) : noise string aligned with the ground truth
        gap_char (char, optional) : gap char used in alignment algorithm. Defaults to GAP_CHAR.

    Returns:
        tuple : ``(gt_to_noise_mapping, noise_to_gt_mapping)`` of two 2D int arrays:

    where each array defines the mapping between aligned gt tokens
    to noise tokens and vice versa.

    Example:
        Given input
        ::

                    aligned_gt: "N@ew York @is big"
                                /\\   |    |   |
                aligned_noise: "N ew@York kis big."

        The returned output will be:
        ::

                ([[0,1],[1],[2],[3]], [[0],[0,1],[2],[3]])
    """
    # Pseudo-algorithm:
    #
    #              tk_start_gt=12         tk_index_gt = 4      total_tokens = 4
    #              |  tk_end_gt=15        tk_index_noise = 3   total_tokens = 3
    #              |  |
    # "New York is big "                     gt_token:big    gt_to_noise_mapping: [[0][0][][2]]
    # "New@york @@ big "                  noise_token:big    noise_to_gt_mapping: [[0][][3]]
    #              |  |
    #              |  tk_end_noise=15      INVALID TOKENS: @*
    #              tk_start_noise=12

    # 1. Initialization:
    # 1. IMPORTANT: add whitespace padding (' ') to both end of aligned_gt and aligned_noise to avoid overflow
    # 2. find the first gt_token and the first noise_token
    # 3. tk_index_gt = tk_index_noise = 0
    # 2. While tk_index_gt < total_tk_gt and tk_index_noise < total_tk_noise:
    # 1. if tk_end_gt == tk_end_noise (1-1 case)
    # 1. check if the two tokens are valid
    # 1. if so, register tokens in mapping
    # 2. find next gt_token token and next noise_token
    # 3. tk_index_gt ++, tk_index_noise ++
    # 3. if tk_end_gt < tk_end_noise (many-1 case)
    # 1. while tk_end_gt < tk_end_noise
    # 1. check if gt_token and noise_token are BOTH valid
    # 1. if so register tokens in mapping
    # 2. find next gt_token
    # 3. tk_index_gt ++
    # 4. if tk_end_gt > tk_end_noise (1-many case)
    # 1. while tk_end_gt > tk_end_noise
    # 1. check if gt_token and noise_token are BOTH valid
    # 1. if so register tokens in mapping
    # 2. find next noise token
    # 3. tk_index_noise ++
    # sanity check
    if len(aligned_gt) != len(aligned_noise):
        raise ValueError("Aligned strings are not equal in length")

    total_gt_tokens = len(tokenize(aligned_gt))
    total_noise_tokens = len(tokenize(aligned_noise))

    # Initialization
    aligned_gt += " "  # add whitespace padding to prevent ptr overflow
    aligned_noise += " "  # add whitespace padding to prevent ptr overflow
    tk_index_gt = tk_index_noise = 0
    tk_start_gt, tk_end_gt = _find_next_token(aligned_gt, 0)
    tk_start_noise, tk_end_noise = _find_next_token(aligned_noise, 0)
    gt_to_noise_mapping = [[] for i in range(total_gt_tokens)]
    noise_to_gt_mapping = [[] for i in range(total_noise_tokens)]

    while tk_index_gt < total_gt_tokens or tk_index_noise < total_noise_tokens:
        # If both tokens are aligned (one-to-one case)
        if tk_end_gt == tk_end_noise:
            # if both gt_token and noise_token are valid (missing token case)
            if _is_valid_token(
                aligned_gt[tk_start_gt:tk_end_gt], gap_char=gap_char
            ) and _is_valid_token(
                aligned_noise[tk_start_noise:tk_end_noise], gap_char=gap_char
            ):
                # register the index of these tokens in the gt_to_noise_mapping
                index_row = gt_to_noise_mapping[tk_index_gt]
                index_row.append(tk_index_noise)
                # register the index of these tokens in the noise_to_gt_mapping
                index_row = noise_to_gt_mapping[tk_index_noise]
                index_row.append(tk_index_gt)
            # find the start and end the next gt_token and noise_token
            tk_start_gt, tk_end_gt = _find_next_token(aligned_gt, tk_end_gt)
            tk_start_noise, tk_end_noise = _find_next_token(aligned_noise, tk_end_noise)
            tk_index_gt += 1
            tk_index_noise += 1
        # If gt_token is shorter than noise_token (many-to-one case)
        elif tk_end_gt < tk_end_noise:
            while tk_end_gt < tk_end_noise:
                # if both gt_token and noise_token are valid (missing token case)
                if _is_valid_token(
                    aligned_gt[tk_start_gt:tk_end_gt], gap_char=gap_char
                ) and _is_valid_token(
                    aligned_noise[tk_start_noise:tk_end_noise], gap_char=gap_char
                ):
                    # register the index of these tokens in the gt_to_noise_mapping
                    index_row = gt_to_noise_mapping[tk_index_gt]
                    index_row.append(tk_index_noise)
                    # register the index of these tokens in the noise_to_gt_mapping
                    index_row = noise_to_gt_mapping[tk_index_noise]
                    index_row.append(tk_index_gt)
                # Find the next gt_token
                tk_start_gt, tk_end_gt = _find_next_token(aligned_gt, tk_end_gt)
                # Increment index
                tk_index_gt += 1
        # If gt_token is longer than noise_token (one-to-many case)
        else:
            while tk_end_gt > tk_end_noise:
                # if both gt_token and noise_token are valid (missing token case)
                if _is_valid_token(
                    aligned_gt[tk_start_gt:tk_end_gt], gap_char=gap_char
                ) and _is_valid_token(
                    aligned_noise[tk_start_noise:tk_end_noise], gap_char=gap_char
                ):
                    # register the index of these token in the gt_to_noise mapping
                    index_row = gt_to_noise_mapping[tk_index_gt]
                    index_row.append(tk_index_noise)
                    # register the index of these token in the noise_to_gt mapping
                    index_row = noise_to_gt_mapping[tk_index_noise]
                    index_row.append(tk_index_gt)
                # Find the next gt_token
                tk_start_noise, tk_end_noise = _find_next_token(
                    aligned_noise, tk_end_noise
                )
                # Increment index
                tk_index_noise += 1

    return gt_to_noise_mapping, noise_to_gt_mapping
