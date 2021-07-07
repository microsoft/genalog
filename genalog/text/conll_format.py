# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# ---------------------------------------------------------

"""This is a utility tool to create CoNLL-formatted token+label files for OCR'ed text
by extracting text from grok OCR output JSON files and propagating labels from clean
text to OCR text.

Usage:
::

    conll_format.py [-h] [--train_subset] [--test_subset]
                    [--gt_folder GT_FOLDER]
                    base_folder degraded_folder

    Positional Argument:
        base_folder            base directory containing the collection of dataset
        degraded_folder        directory name containing train and test subset for degradation

    Optional Arguments:
        --train_subset            include if only train directory should be processed
        --test_subset             include if only test directory should be processed
        --gt_folder GT_FOLDER     directory name containing ground truth (default to `shared`)

    Seek Help:
        -h, --help                show this help message and exit

Example Usage:

.. code-block:: shell

    # to run for specified degradation of the dataset on both train and test
    python -m genalog.text.conll_format '/data/enki/datasets/synthetic_dataset/' 'hyphens_all'

    # to run for specified degradation of the dataset and ground truth
    python -m genalog.text.conll_format '/data/enki/datasets/synthetic_dataset/' 'hyphens_all' --gt_folder='shared'

    # to run for specified degradation of the dataset  on only test subset
    python -m genalog.text.conll_format '/data/enki/datasets/synthetic_dataset/' 'hyphens_all' --test_subset

    # to run for specified degradation of the dataset  on only train subset
    python -m genalog.text.conll_format '/data/enki/datasets/synthetic_dataset/' 'hyphens_all' --train_subset
"""
import argparse
import concurrent.futures
import difflib
import itertools
import json
import os
import timeit

from tqdm import tqdm

from genalog.text import alignment, ner_label

EMPTY_SENTENCE_SENTINEL = "<<<<EMPTY_OCR_SENTENCE>>>>"
EMPTY_SENTENCE_SENTINEL_NER_LABEL = "O"


def propagate_labels_sentences(clean_tokens, clean_labels, clean_sentences, ocr_tokens):
    """
    propagate_labels_sentences propagates clean labels for clean tokens to ocr tokens and splits ocr tokens into sentences

    Parameters
    ----------
    clean_tokens : list
        list of tokens in clean text
    clean_labels : list
        list of labels corresponding to clean tokens
    clean_sentences : list
        list of sentences (each sentence is a list of tokens)
    ocr_tokens : list
        list of tokens in ocr text

    Returns
    -------
    list, list
        list of ocr sentences (each sentence is a list of tokens)
        list of labels for ocr sentences
    """
    # Ensure equal number of tokens in both clean_tokens and clean_sentences
    merged_sentences = list(itertools.chain(*clean_sentences))
    if merged_sentences != clean_tokens:
        delta = "\n".join(
            difflib.unified_diff(
                merged_sentences,
                clean_tokens,
                fromfile="merged_clean_sentences",
                tofile="clean_tokens",
            )
        )
        raise ValueError(
            "Inconsistent tokens. "
            + f"Delta between clean_text and clean_labels:\n{delta}"
        )
    # Ensure that there's OCR result
    if len(ocr_tokens) == 0:
        raise ValueError("Empty OCR tokens.")
    elif len(clean_tokens) == 0:
        raise ValueError("Empty clean tokens.")

    # 1. Propagate labels + alig
    ocr_labels, aligned_clean, aligned_ocr, gap_char = ner_label.propagate_label_to_ocr(
        clean_labels, clean_tokens, ocr_tokens
    )

    # 2. Parse alignment to get mapping
    gt_to_ocr_mapping, ocr_to_gt_mapping = alignment.parse_alignment(
        aligned_clean, aligned_ocr, gap_char=gap_char
    )

    # 3. Find sentence breaks in clean text sentences
    gt_to_ocr_mapping_is_empty = [len(mapping) == 0 for mapping in gt_to_ocr_mapping]

    sentence_index = []
    sentence_token_counts = 0
    for sentence in clean_sentences:
        sentence_index.append(sentence_token_counts)
        sentence_token_counts += len(sentence)
    sentence_index.append(sentence_token_counts)

    # 4. propagate sentence breaks to ocr text
    gt_start_n_end = list(zip(sentence_index[:-1], sentence_index[1:]))
    ocr_text_sentences = []
    ocr_labels_sentences = []
    for gt_start, gt_end in gt_start_n_end:
        # Corner Case: 1st gt token is not mapped to any ocr token
        if gt_start == 0 and len(gt_to_ocr_mapping[gt_start]) < 1:
            ocr_start = 0
        # if gt token at sentence break is not mapped to any ocr token
        elif len(gt_to_ocr_mapping[gt_start]) < 1:
            try:  # finding next gt token that is mapped to an ocr token
                new_gt_start = gt_to_ocr_mapping_is_empty.index(False, gt_start)
                ocr_start = gt_to_ocr_mapping[new_gt_start][0]
            # If no valid token mapping in the remaining gt tokens
            except ValueError:
                ocr_start = len(ocr_tokens)  # use the last ocr token
        else:
            ocr_start = gt_to_ocr_mapping[gt_start][0]

        # if gt token is not map to any ocr token
        if gt_end >= len(gt_to_ocr_mapping):
            ocr_end = len(ocr_tokens)
        elif len(gt_to_ocr_mapping[gt_end]) < 1:
            try:  # finding next gt token that is mapped to an ocr token
                new_gt_end = gt_to_ocr_mapping_is_empty.index(False, gt_end)
                ocr_end = gt_to_ocr_mapping[new_gt_end][0]
            # If no valid token mapping in the remaining gt tokens
            except ValueError:
                ocr_end = len(ocr_tokens)  # use the last ocr token
        else:
            ocr_end = gt_to_ocr_mapping[gt_end][0]
        ocr_sentence = ocr_tokens[ocr_start:ocr_end]
        ocr_sentence_labels = ocr_labels[ocr_start:ocr_end]
        ocr_text_sentences.append(ocr_sentence)
        ocr_labels_sentences.append(ocr_sentence_labels)
    return ocr_text_sentences, ocr_labels_sentences


def get_sentences_from_iob_format(iob_format_str):
    sentences = []
    sentence = []
    for line in iob_format_str:
        if line.strip() == "":  # if line is empty (sentence separator)
            sentences.append(sentence)
            sentence = []
        else:
            token = line.split()[0].strip()
            sentence.append(token)
    sentences.append(sentence)
    # filter any empty sentences
    return list(filter(lambda sentence: len(sentence) > 0, sentences))


def propagate_labels_sentence_single_file(arg):
    (
        clean_labels_dir,
        output_text_dir,
        output_labels_dir,
        clean_label_ext,
        input_filename,
    ) = arg

    clean_labels_file = os.path.join(clean_labels_dir, input_filename).replace(
        clean_label_ext, ".txt"
    )
    ocr_text_file = os.path.join(output_text_dir, input_filename)
    ocr_labels_file = os.path.join(output_labels_dir, input_filename)
    if not os.path.exists(clean_labels_file):
        print(
            f"Warning: missing clean label file '{clean_labels_file}'. Please check file corruption. Skipping this file index..."
        )
        return
    elif not os.path.exists(ocr_text_file):
        print(
            f"Warning: missing ocr text file '{ocr_text_file}'. Please check file corruption. Skipping this file index..."
        )
        return
    else:
        with open(clean_labels_file, "r", encoding="utf-8") as clf:
            tokens_labels_str = clf.readlines()
        clean_tokens = [
            line.split()[0].strip()
            for line in tokens_labels_str
            if len(line.split()) == 2
        ]
        clean_labels = [
            line.split()[1].strip()
            for line in tokens_labels_str
            if len(line.split()) == 2
        ]
        clean_sentences = get_sentences_from_iob_format(tokens_labels_str)
        # read ocr tokens
        with open(ocr_text_file, "r", encoding="utf-8") as otf:
            ocr_text_str = " ".join(otf.readlines())
            ocr_tokens = [
                token.strip() for token in ocr_text_str.split()
            ]  # already tokenized in data
        try:
            ocr_tokens_sentences, ocr_labels_sentences = propagate_labels_sentences(
                clean_tokens, clean_labels, clean_sentences, ocr_tokens
            )
        except Exception as e:
            print(
                f"\nWarning: error processing '{input_filename}': {str(e)}.\nSkipping this file..."
            )
            return
        # Write result to file
        with open(ocr_labels_file, "w", encoding="utf-8") as olf:
            for ocr_tokens, ocr_labels in zip(
                ocr_tokens_sentences, ocr_labels_sentences
            ):
                if len(ocr_tokens) == 0:  # if empty OCR sentences
                    olf.write(
                        f"{EMPTY_SENTENCE_SENTINEL}\t{EMPTY_SENTENCE_SENTINEL_NER_LABEL}\n"
                    )
                else:
                    for token, label in zip(ocr_tokens, ocr_labels):
                        olf.write(f"{token}\t{label}\n")
                olf.write("\n")


def propagate_labels_sentences_multiprocess(
    clean_labels_dir, output_text_dir, output_labels_dir, clean_label_ext
):
    """
    propagate_labels_sentences_all_files propagates labels and sentences for all files in dataset

    Parameters
    ----------
    clean_labels_dir : str
        path of directory with clean labels -
        CoNLL formatted so contains tokens and corresponding labels
    output_text_dir : dir
        path of directory with ocr text
    output_labels_dir : dir
        path of directory with ocr labels -
        CoNLL formatted so contains tokens and corresponding labels
    clean_label_ext : str
        file extension of the clean_labels
    """
    clean_label_files = os.listdir(clean_labels_dir)
    args = list(
        map(
            lambda clean_label_filename: (
                clean_labels_dir,
                output_text_dir,
                output_labels_dir,
                clean_label_ext,
                clean_label_filename,
            ),
            clean_label_files,
        )
    )
    with concurrent.futures.ProcessPoolExecutor() as executor:
        iterator = executor.map(propagate_labels_sentence_single_file, args)
        for _ in tqdm(iterator, total=len(args)):  # wrapping tqdm for progress report
            pass


def extract_ocr_text(input_file, output_file):
    """
    extract_ocr_text from GROK json

    Parameters
    ----------
    input_file : str
        file path of input file
    output_file : str
        file path of output file
    """
    out_dir = os.path.dirname(output_file)
    in_file_name = os.path.basename(input_file)
    file_pre = in_file_name.split("_")[-1].split(".")[0]
    output_file_name = "{}.txt".format(file_pre)
    output_file = os.path.join(out_dir, output_file_name)
    with open(input_file, "r", encoding="utf-8") as fin:
        json_data = json.load(fin)
    json_dict = json_data[0]
    text = json_dict["text"]
    with open(output_file, "wb") as fout:
        fout.write(text.encode("utf-8"))


def check_n_sentences(clean_labels_dir, output_labels_dir, clean_label_ext):
    """
    check_n_sentences prints file name if number of sentences is different in clean and OCR files

    Parameters
    ----------
    clean_labels_dir : str
        path of directory with clean labels -
        CoNLL formatted so contains tokens and corresponding labels
    output_labels_dir : str
        path of directory with ocr labels -
        CoNLL formatted so contains tokens and corresponding labels
    """
    text_files = os.listdir(output_labels_dir)
    skip_files = []
    for text_filename in tqdm(text_files):
        clean_labels_file = os.path.join(clean_labels_dir, text_filename).replace(
            ".txt", clean_label_ext
        )
        ocr_labels_file = os.path.join(output_labels_dir, text_filename)
        remove_first_line(clean_labels_file, clean_labels_file)
        remove_first_line(ocr_labels_file, ocr_labels_file)
        remove_last_line(clean_labels_file, clean_labels_file)
        remove_last_line(ocr_labels_file, ocr_labels_file)
        with open(clean_labels_file, "r", encoding="utf-8") as lf:
            clean_tokens_labels = lf.readlines()
        with open(ocr_labels_file, "r", encoding="utf-8") as of:
            ocr_tokens_labels = of.readlines()
        error = False
        n_clean_sentences = 0
        nl = False
        for line in clean_tokens_labels:
            if line == "\n":
                if nl is True:
                    error = True
                else:
                    nl = True
                    n_clean_sentences += 1
            else:
                nl = False
        n_ocr_sentences = 0
        nl = False
        for line in ocr_tokens_labels:
            if line == "\n":
                if nl is True:
                    error = True
                else:
                    nl = True
                    n_ocr_sentences += 1
            else:
                nl = False
        if error or n_ocr_sentences != n_clean_sentences:
            print(
                f"Warning: Inconsistent numbers of sentences in '{text_filename}''."
                + f"clean_sentences to ocr_sentences: {n_clean_sentences}:{n_ocr_sentences}"
            )
            skip_files.append(text_filename)
    return skip_files


def remove_first_line(input_file, output_file):
    """
    remove_first_line from files (some clean CoNLL files have an empty first line)

    Parameters
    ----------
    input_file : str
        input file path
    output_file : str
        output file path
    """
    with open(input_file, "r", encoding="utf-8") as in_f:
        lines = in_f.readlines()
    if len(lines) > 1 and lines[0].strip() == "":
        # the clean CoNLL formatted files had a newline as the first line
        with open(output_file, "w", encoding="utf-8") as out_f:
            out_f.writelines(lines[1:])


def remove_last_line(input_file, output_file):
    """
    remove_last_line from files (some clean CoNLL files have an empty last line)

    Parameters
    ----------
    input_file : str
        input file path
    output_file : str
        output file path
    """

    with open(input_file, "r", encoding="utf-8") as in_f:
        lines = in_f.readlines()
    if len(lines) > 1 and lines[-1].strip() == "":
        with open(output_file, "w", encoding="utf-8") as out_f:
            out_f.writelines(lines[:-1])


def for_all_files(input_dir, output_dir, func):
    """
    for_all_files will apply function to every file in a director

    Parameters
    ----------
    input_dir : str
        directory with input files
    output_dir : str
        directory for output files
    func : function
        function to be applied to all files in input_dir
    """
    text_files = os.listdir(input_dir)
    for text_filename in text_files:
        input_file = os.path.join(input_dir, text_filename)
        output_file = os.path.join(output_dir, text_filename)
        func(input_file, output_file)


def main(args):
    if not args.train_subset and not args.test_subset:
        subsets = ["train", "test"]
    else:
        subsets = []
        if args.train_subset:
            subsets.append("train")

        if args.test_subset:
            subsets.append("test")

    for subset in subsets:
        print("Processing {} subset...".format(subset))

        clean_labels_dir = os.path.join(
            args.base_folder, args.gt_folder, subset, "clean_labels"
        )
        ocr_json_dir = os.path.join(
            args.base_folder, args.degraded_folder, subset, "ocr"
        )

        output_text_dir = os.path.join(
            args.base_folder, args.degraded_folder, subset, "ocr_text"
        )
        output_labels_dir = os.path.join(
            args.base_folder, args.degraded_folder, subset, "ocr_labels"
        )

        # remove first empty line of labels file, if exists
        for_all_files(clean_labels_dir, clean_labels_dir, remove_first_line)

        if not os.path.exists(output_text_dir):
            os.mkdir(output_text_dir)

        # extract text from ocr json output and save to ocr_text/
        for_all_files(ocr_json_dir, output_text_dir, extract_ocr_text)

        if not os.path.exists(output_labels_dir):
            os.mkdir(output_labels_dir)

        # make ocr labels files by propagating clean labels to ocr_text and creating files in ocr_labels
        propagate_labels_sentences_multiprocess(
            clean_labels_dir, output_text_dir, output_labels_dir, args.clean_label_ext
        )
        print("Validating number of sentences in gt and ocr labels")
        check_n_sentences(
            clean_labels_dir, output_labels_dir, args.clean_label_ext
        )  # check number of sentences and make sure same; print anomaly files


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "base_folder", help="base directory containing the collection of dataset"
    )
    parser.add_argument(
        "degraded_folder",
        help="directory containing train and test subset for degradation",
    )
    parser.add_argument(
        "--gt_folder",
        type=str,
        default="shared",
        help="directory containing the ground truth",
    )
    parser.add_argument(
        "--clean_label_ext",
        type=str,
        default=".txt",
        help="file extension of the clean_labels files",
    )
    parser.add_argument(
        "--train_subset",
        help="include if only train folder should be processed",
        action="store_true",
    )
    parser.add_argument(
        "--test_subset",
        help="include if only test folder should be processed",
        action="store_true",
    )
    return parser


if __name__ == "__main__":
    start = timeit.default_timer()
    parser = create_parser()
    args = parser.parse_args()
    main(args)
    elapsed_time = timeit.default_timer() - start
    print(f"Time to format entire dataset: {elapsed_time:0.3f}s")
