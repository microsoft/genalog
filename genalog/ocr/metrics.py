# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# ---------------------------------------------------------

"""
Utility functions to support getting OCR metrics

OCR Metrics
1. word/character accuracy like in this paper https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=6065412.
Accuracy = Correct Words/Total Words (in target strings)

2. Count of edit distance ops:
insert, delete, substitutions; like in the paper "Deep Statistical Analysis of OCR Errors for Effective Post-OCR Processing".
This is based on Levenshtein edit distance.

3. By looking at the gaps in alignment we also generate substitution dicts:
e.g: if we have text "a worn coat" and ocr is "a wom coat" , "rn" -> "m" will be captured as a substitution
since the rest of the segments align.The assumption here is that we do not expect to have very long gaps in alignment,
hence collecting and counting these substitutions will be managable.

"""
import argparse
import json
import multiprocessing
import os
import re
from multiprocessing import Pool

import pandas as pd
from tqdm import tqdm

from genalog.text.alignment import GAP_CHAR
from genalog.text.anchor import align_w_anchor
from genalog.text.ner_label import _find_gap_char_candidates

LOG_LEVEL = 0
WORKERS_PER_CPU = 2


def _log(*args, **kwargs):
    if LOG_LEVEL:
        print(args)


def _trim_whitespace(src_string):
    return re.sub(r"\s+", " ", src_string.strip())


def _update_align_stats(src, target, align_stats, substitution_dict, gap_char):
    """Given two string that differ and have no alignment at all,
     update the alignment dict and fill in substitution if replacements are found.
     update alignment stats with counts of the edit operation to transform the source
     string to the targes

    Args:
        src (str): source string
        target (str): target string at the
        align_stats (dict): key-value dictionary that stores the counts of inserts, deletes,
            spacing and replacements
        substitution_dict (dict): store the counts of mapping from one substring to another of
            the replacement edit operation. e.g if 'rm' in source needs to map to 'm' in the target 2
            times this will be { ('rm','m'): 2}
        gap_char (str): gap character used in alignment
    """
    _log("getting gap stats for", src, target)
    spacing_count = 0
    for char1, char2 in zip(target, src):
        if (char1 == gap_char and char2 == " ") or (char1 == " " and char2 == gap_char):
            spacing_count += 1
    source_substr = src.strip(f"{gap_char} ")
    target_substr = target.strip(f"{gap_char} ")
    if source_substr != "" or target_substr != "":
        if source_substr == "":
            _log("inserting", target_substr)
            align_stats["insert"] += 1
        elif target_substr == "":
            _log("deleting", source_substr)
            align_stats["delete"] += 1
        else:
            align_stats["replace"] += 1
            _log("replacing", source_substr, target_substr)
            substitution_dict[source_substr, target_substr] = (
                substitution_dict.get((source_substr, target_substr), 0) + 1
            )
    _log("spacing count", spacing_count)
    align_stats["spacing"] += spacing_count


def _update_word_stats(
    aligned_src,
    aligned_target,
    gap_char,
    start,
    end,
    matching_chars_count,
    matching_words_count,
    matching_alnum_words_count,
):
    """Given two string segments that align. update the counts of matching words and characters

    Args:
        aligned_src (str): full source string
        aligned_target (str): full target string
        gap_char (str): gap character used in alignment
        start (int): start position of alignment
        end (int): end position of alignment
        matching_chars_count (int): current count of matching characters
        matching_words_count (int): current count of matching words
        matching_alnum_words_count (int): current count of alphanumeric matching words

    Returns:
        tuple(int,int,int): the updated matching_chars_count, matching_words_count, matching_alnum_words_count
    """
    aligned_part = aligned_src[start:end]
    matching_chars_count += end - start
    # aligned_part = seq.strip()
    _log("aligned", aligned_part, start, end)
    if len(aligned_src) != len(aligned_target):
        raise ValueError("alignment strings are of different length")
    if aligned_part.strip() != "":
        words = re.split(r"\s+", aligned_part.strip())
        matching_words_count += len(words)
        matching_alnum_words_count += len(words)

        for i, word in enumerate(words):
            # remove words that dont have an alphanumeric char from the alphanumeric word count
            if not re.search(r"\w", word):
                matching_alnum_words_count -= 1

            # handle the edge case for the first and last words as these are at the boundary and need
            # to be compared with the full string to see if they have space before or after

            if i == 0:
                if start != 0 and (
                    aligned_target[start] != " " or aligned_src[start] != " "
                ):
                    # if this was the start of the string in the target or source
                    if not (
                        aligned_src[:start].replace(gap_char, "").replace(" ", "") == ""
                        and aligned_target[start - 1] == " "
                    ) and not (
                        aligned_target[:start].replace(gap_char, "").replace(" ", "")
                        == ""
                        and aligned_src[start - 1] == " "
                    ):
                        # beginning word not matching completely
                        _log("removing first match word from count", word, aligned_part)
                        matching_words_count -= 1
                        if re.search(r"\w", word):
                            matching_alnum_words_count -= 1
                        continue

            if i == len(words) - 1:
                if end != len(aligned_target) and (
                    aligned_target[end] != " " or aligned_src[end] != " "
                ):
                    # this was not the end of the string in the src and not end of string in target
                    if not (
                        aligned_src[end:].replace(gap_char, "").replace(" ", "") == ""
                        and aligned_target[end] == " "
                    ) and not (
                        aligned_target[end:].replace(gap_char, "").replace(" ", "")
                        == ""
                        and aligned_src[end] == " "
                    ):
                        # last word not matching completely
                        _log("removing last match word from count", word, aligned_part)
                        matching_words_count -= 1
                        if re.search(r"\w", word):
                            matching_alnum_words_count -= 1

    _log("matched count", matching_words_count)
    _log("matched alnum count", matching_alnum_words_count)
    return matching_chars_count, matching_words_count, matching_alnum_words_count


def _get_align_stats(alignment, src_string, target, gap_char):
    """Given an alignment, this function get the align stats and substitution mapping to
    transform the source string to the target string

    Args:
        alignment (tuple(str, str)): the result of calling align on the two strings
        src_source (str): the source string
        target (str) : the target string
        gap_char (str) : the gap character used in alignment

    Raises:
        ValueError: if any of the aligned string are empty

    Returns:
        tuple(dict, dict): align stats dict, substitution mappings dict
    """

    aligned_src, aligned_target = alignment

    if src_string.strip() == "" or target.strip() == "":
        raise ValueError("one of the input strings is empty")
    _log("src, target", src_string, target)
    substitution_dict = {}

    # words are defined as here as string sepated by whitespace
    words = re.split(r"\s+", target.strip())
    word_count = len(words)

    # alphanumeric words are defined here as words with at least one alphanumeric character
    alnum_words_count = len(list(filter(lambda x: re.search(r"\w", x), words)))

    char_count = max(len(target), len(src_string))
    matching_chars_count = 0
    matching_words_count = 0
    matching_alnum_words_count = 0

    align_stats = {
        "insert": 0,
        "delete": 0,
        "replace": 0,
        "spacing": 0,
        "total_chars": char_count,
        "total_words": word_count,
        "total_alnum_words": alnum_words_count,
    }
    start = 0

    _log("######### Alignment ############")
    _log(aligned_src)
    _log(aligned_target)
    _log("################################")

    gap_start = None
    for i, (char_1, char_2) in enumerate(zip(aligned_src, aligned_target)):
        if char_1 != char_2:
            # since characters don't match here start:i is a substring of the string that align
            # since this substring aligns, simple count the number of matching words and chars in and update
            # the word stats
            end = i
            _log(
                "sequences",
                aligned_src[start:end],
                aligned_target[start:end],
                start,
                end,
            )
            assert aligned_src[start:end] == aligned_target[start:end]
            (
                matching_chars_count,
                matching_words_count,
                matching_alnum_words_count,
            ) = _update_word_stats(
                aligned_src,
                aligned_target,
                gap_char,
                start,
                end,
                matching_chars_count,
                matching_words_count,
                matching_alnum_words_count,
            )
            start = end + 1
            if gap_start is None:
                gap_start = end
        else:
            gap_end = i
            if gap_start is not None:
                # since characters now match  gap_start:i contains a substring of the characters that didnt align before
                # handle this gap alignment by calling _update_align_stats
                _log(
                    "gap",
                    aligned_src[gap_start:gap_end],
                    aligned_target[gap_start:gap_end],
                    gap_start,
                    gap_end,
                )
                _update_align_stats(
                    aligned_src[gap_start:gap_end],
                    aligned_target[gap_start:gap_end],
                    align_stats,
                    substitution_dict,
                    gap_char,
                )
            gap_start = None

    # Now compare any left overs string segments from the for loop
    if gap_start is not None:
        # handle last alignment gap
        _log("last gap", aligned_src[gap_start:], aligned_target[gap_start:])
        _update_align_stats(
            aligned_src[gap_start:],
            aligned_target[gap_start:],
            align_stats,
            substitution_dict,
            gap_char,
        )
    else:
        # handle last aligned substring
        seq = aligned_src[start:]
        aligned_part = seq.strip()
        end = len(aligned_src)
        _log("last aligned", aligned_part)
        (
            matching_chars_count,
            matching_words_count,
            matching_alnum_words_count,
        ) = _update_word_stats(
            aligned_src,
            aligned_target,
            gap_char,
            start,
            end,
            matching_chars_count,
            matching_words_count,
            matching_alnum_words_count,
        )

    align_stats["matching_chars"] = matching_chars_count
    align_stats["matching_alnum_words"] = matching_alnum_words_count
    align_stats["matching_words"] = matching_words_count
    align_stats["alnum_word_accuracy"] = matching_alnum_words_count / alnum_words_count
    align_stats["word_accuracy"] = matching_words_count / word_count
    align_stats["char_accuracy"] = matching_chars_count / char_count
    return align_stats, substitution_dict


def get_editops_stats(alignment, gap_char):
    """Get stats for character level edit operations that need to be done to
    transform the source string to the target string. Inputs must not be empty
    and must be the result of calling the runing the align function.

    Args:
        alignment (tuple(str, str)): the results from the string alignment biopy function
        gap_char (str): gap character used in alignment

    Raises:
        ValueError: If any of the string in the alignment are empty

    Returns:
        [type]: [description]
    """

    aligned_src, aligned_target = alignment
    if aligned_src == "" or aligned_target == "":
        raise ValueError("one of the input strings is empty")
    stats = {
        "edit_insert": 0,
        "edit_delete": 0,
        "edit_replace": 0,
        "edit_insert_spacing": 0,
        "edit_delete_spacing": 0,
    }
    actions = {}
    for i, (char_1, char_2) in enumerate(zip(aligned_src, aligned_target)):
        if LOG_LEVEL > 1:
            _log(char_1, char_2)
        if char_1 == gap_char:
            # insert
            if char_2 == " ":
                stats["edit_insert_spacing"] += 1
            else:
                stats["edit_insert"] += 1
            actions[i] = ("I", char_2)
        elif char_2 == gap_char:
            # delete
            if char_1 == " ":
                stats["edit_delete_spacing"] += 1
            else:
                stats["edit_delete"] += 1
            actions[i] = "D"
        elif char_2 != char_1:
            stats["edit_replace"] += 1
            actions[i] = ("R", char_2)
    return stats, actions


def get_align_stats(alignment, src_string, target, gap_char):
    """Get alignment stats

    Args:
        alignment (tuple(str,str)): the result of calling the align function
        src_string (str): the original source string
        target (str): the original target string
        gap_char (str): the gap character used in alignment

    Raises:
        ValueError: if any of the strings are empty

    Returns:
        tuple(dict, dict): dict of the align starts and dict of the substitution mappings
    """
    if src_string.strip() == "" or target.strip() == "":
        raise ValueError("one of the input strings is empty")

    _log("alignment results")
    _log(alignment)
    align_stats, substitution_dict = _get_align_stats(
        alignment, src_string, target, gap_char
    )
    return align_stats, substitution_dict


def get_stats(target, src_string):
    """Get align stats, edit stats, and substitution mappings for transforming the
    source string to the target string. Edit stats refers to character level edit operation
    required to transform the source to target. Align stats referers to substring level operation
    required to transform the source to target. Align stats have keys insert,replace,delete and the special
    key spacing which counts spacing differences between the two strings. Edit stats have the keys edit_insert,
    edit_replace, edit_delete which count the character level edits.

    Args:
        src_string (str): the source string
        target (str): the target string

    Returns:
       tuple(str, str): One dict containing the edit and align stats, another dict containing the substitutions
    """
    gap_char_candidates, input_char_set = _find_gap_char_candidates(
        [src_string], [target]
    )
    gap_char = (
        GAP_CHAR if GAP_CHAR in gap_char_candidates else gap_char_candidates.pop()
    )
    alignment = align_w_anchor(src_string, target, gap_char=gap_char)
    align_stats, substitution_dict = get_align_stats(
        alignment, src_string, target, gap_char
    )
    edit_stats, actions = get_editops_stats(alignment, gap_char)
    _log("alignment", align_stats)
    return {**edit_stats, **align_stats}, substitution_dict, actions


def get_metrics(
    src_text_path, ocr_json_path, folder_hash=None, use_multiprocessing=True
):
    """Given a path to the folder containing the source text and a folder containing
    the output OCR json, this generates the metrics for all files in the source folder.
    This assumes that the files json folder are of the same name the text files except they
    are prefixed by the parameter folder_hash followed by underscore and suffixed by .png.json.

    Args:
        src_text_path (str): path to source txt files
        ocr_json_path (str): path to OCR json files
        folder_hash (str): prefix for OCR json files
        use_multiprocessing (bool): use multiprocessing

    Returns:
        tuple(pandas.DataFrame, dict): A pandas dataframe of the metrics with each file in a row,
            a dict containing the substitions mappings for each file. the key to the dict is the
            filename and the values are dicts of the substition mappings for that file.
    """

    rows = []
    substitutions = {}
    actions_map = {}

    # Spin up workers as alignment on many files can take a while
    cpu_count = multiprocessing.cpu_count()
    n_workers = WORKERS_PER_CPU * cpu_count

    job_args = list(
        map(
            lambda f: (f, src_text_path, ocr_json_path, folder_hash),
            os.listdir(src_text_path),
        )
    )

    if use_multiprocessing:
        with Pool(n_workers) as pool:
            for f, stats, actions, subs in tqdm(
                pool.imap_unordered(_worker, job_args), total=len(job_args)
            ):
                substitutions[f] = subs
                actions_map[f] = actions
                rows.append(stats)
    else:
        for f, stats, actions, subs in tqdm(
            map(_worker, job_args), total=len(job_args)
        ):
            substitutions[f] = subs
            actions_map[f] = actions
            rows.append(stats)

    df = pd.DataFrame(rows)
    return df, substitutions, actions_map


def get_file_metrics(f, src_text_path, ocr_json_path, folder_hash):
    src_filename = os.path.join(src_text_path, f)
    if folder_hash:
        ocr_filename = os.path.join(
            ocr_json_path, f"{folder_hash}_{f.split('txt')[0] + 'json'}"
        )
    else:
        ocr_filename = os.path.join(ocr_json_path, f"{f.split('txt')[0] + 'json'}")
    try:
        src_string = open(src_filename, "r", errors="ignore", encoding="utf8").read()
    except FileNotFoundError:
        print(f"File not found: {src_filename}, skipping this file.")
        return f, {}, {}, {}
    try:
        ocr_string = _get_sorted_text(json.load(open(ocr_filename, "rb")))
    except FileNotFoundError:
        print(f"File not found: {ocr_filename}, skipping this file.")
        return f, {}, {}, {}
    # TODO ocr bug? text lines are sometimes not sorted correctly
    ocr_string = _trim_whitespace(ocr_string)
    src_string = _trim_whitespace(src_string)
    try:
        stats, subs, actions = get_stats(ocr_string, src_string)
    except ValueError as e:
        print("Error:", src_filename, ocr_filename, e)
        return f, {}, {}, {}
    stats["txt_path"] = src_filename
    stats["ocr_json_path"] = ocr_filename
    stats["filename"] = f
    return f, stats, actions, subs


def _worker(args):
    (f, src_text_path, ocr_json_path, folder_hash) = args
    return get_file_metrics(f, src_text_path, ocr_json_path, folder_hash)


def _get_sorted_text(ocr_json):
    if "lines" in ocr_json[0]:
        lines = ocr_json[0]["lines"]
        sorted_lines = sorted(lines, key=lambda line: line["boundingBox"][0]["y"])
        return " ".join([line["text"] for line in sorted_lines])
    else:
        return ocr_json[0]["text"]


def substitution_dict_to_json(substitution_dict):
    """Converts substitution dict to list of tuples of (source_substring, target_substring, count)

    Args:
        substitution_dict ([type]): [description]
    """
    to_tuple = lambda x: [(k + (x[k],)) for k in x]  # noqa: E731
    out = {}
    for filename in substitution_dict:
        out[filename] = to_tuple(substitution_dict[filename])
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("src", help="path to folder with text files.")
    parser.add_argument(
        "ocr",
        help="folder with ocr json. the filename must match the text filename prefixed by ocr_prefix.",
    )
    parser.add_argument("--ocr_prefix", help="the prefix of the ocr files")
    parser.add_argument("--output", help="output names of metrics files")

    args = parser.parse_args()
    df, subs, actions = get_metrics(args.src, args.ocr, args.ocr_prefix)

    csv_file, json_file = f"{args.output}.csv", f"{args.output}.json"
    print("got metrics. dumping to files:", csv_file, json_file)
    df.to_csv(csv_file)
    json.dump(substitution_dict_to_json(subs), open(json_file, "w"))
