# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# ---------------------------------------------------------

"""This is a utility tool to split CoNLL formated files.
It has the capability to pack sentences into generated pages more tightly.

usage: splitter.py [-h] [--doc_sep DOC_SEP] [--line_sep LINE_SEP]
                   [--force_doc_sep]
                   input_file output_folder

positional arguments:
  input_file           path to input CoNLL formated file.
  output_folder        folder to write results to.

optional arguments:
  -h, --help           show this help message and exit
  --doc_sep DOC_SEP    CoNLL doc seperator
  --line_sep LINE_SEP  CoNLL line seperator
  --force_doc_sep      If set, documents are forced to be split by the doc seperator (recommended to turn this off)

example usage:

    python -m genalog.text.splitter --doc_sep="-DOCSTART-\tO" CoNLL-2003_test.txt conll2003_test

    python -m genalog.text.splitter CoNLL-2012_train.txt conll2012_train

"""
import argparse
import multiprocessing
import os
from multiprocessing.pool import ThreadPool

from tqdm import tqdm

from genalog.generation.content import CompositeContent, ContentType
from genalog.generation.document import DocumentGenerator
from genalog.text import preprocess

# default buffer. Preferebly set this to something large
# It holds the lines read from the CoNLL file
BUFFER_SIZE = 50000

CONLL2012_DOC_SEPERATOR = ""
CONLL2003_DOC_SEPERATOR = "-DOCSTART-"

SEPERATOR = ""
STARTING_SPLIT_GUESS = 100  # starting estimate of point where to split text
MAX_SIZE = 100  # max number of sentences to pack on a doc page

SPLIT_ITERS = 2  # number of iterations to run to find a good split
WORKERS_PER_CPU = 2

default_generator = DocumentGenerator()


def unwrap(size, accumulator):
    words = []
    labels = []
    for i in range(size[0], size[1]):
        sentence = accumulator[i]
        for word, tok in sentence:
            words.append(word)
            labels.append((word, tok))
    return words, labels


def find_split_position(
    accumulator, start_pos, iters=SPLIT_ITERS, template_name="text_block.html.jinja"
):
    """Run a few iterations of binary search to find the best split point
    from the start to pack in sentences into a page without overflow.

    Args:
        accumulator (list): buffer containing sentences
        iters (int, optional): Max number of iterations. Defaults to SPLIT_ITERS.

    Returns:
        the best split position for a doc, the doc, its labels and text
    """
    global STARTING_SPLIT_GUESS
    # use binary search to find page split point
    start, end = start_pos, min(len(accumulator), MAX_SIZE + start_pos)
    best = None
    count = 0
    while start <= end:
        if count == 0 and (
            STARTING_SPLIT_GUESS + start_pos > start
            and STARTING_SPLIT_GUESS + start_pos < end
        ):
            split_point = STARTING_SPLIT_GUESS
        else:
            split_point = (start + end) // 2
        doc_buf = (start_pos, split_point)
        content_words, labels = unwrap(doc_buf, accumulator)
        content_types = [ContentType.PARAGRAPH]

        text = " ".join(content_words)
        content = CompositeContent([text], content_types)
        doc_gen = default_generator.create_generator(content, [template_name])

        doc = next(doc_gen)

        if len(doc._document.pages) > 1:
            end = split_point - 1
        else:
            start = split_point + 1
            best = split_point, doc, labels, text
            if count >= iters:
                break
        count += 1
    STARTING_SPLIT_GUESS = split_point
    return best


def generate_splits(
    input_file,
    output_folder,
    sentence_seperator="",
    doc_seperator=None,
    pool=None,
    force_doc_sep=False,
    ext="txt",
):
    """Processes the file line by line and add sentences to the buffer for processing.

    Args:
        input_file (str): CoNLL formated file
        output_folder (str): output folder path
        sentence_seperator (str): sentence seperator
        doc_seperator (str, optional): document seperator. Defaults to None.
        pool (ThreadPool, optional): ThreadPool. If not set, no multithreading is used. Defaults to None.
        force_doc_sep (bool, optional): Forces documents to be on separate pages. Defaults to False.
    """
    doc_id = 0
    accumulator = []
    sentence = []
    progress_bar = tqdm(unit=" docs", desc="Split into")
    with open(input_file) as f:
        for line in f:
            if line.strip() == sentence_seperator or line.strip() == doc_seperator:

                if len(sentence) > 0:
                    accumulator.append(sentence)
                sentence = []

                if line.strip() == doc_seperator and force_doc_sep:
                    # progress to processing buffer immediately if force_doc_sep
                    pass
                elif len(accumulator) < BUFFER_SIZE:
                    continue
                start_pos = 0
                while start_pos < len(accumulator):
                    start_pos = next_doc(
                        accumulator, doc_id, start_pos, output_folder, pool
                    )
                    doc_id += 1
                    progress_bar.update(1)
                accumulator = []
                continue

            word, tok = line.split("\t")
            if word.strip() == "":
                continue
            sentence.append((word, tok))

        # process any left over lines
        start_pos = 0
        if len(sentence) > 0:
            accumulator.append(sentence)
        while start_pos < len(accumulator):
            start_pos = next_doc(accumulator, doc_id, start_pos, output_folder, pool)
            doc_id += 1
            progress_bar.update(1)


def next_doc(accumulator, doc_id, start_pos, output_folder, pool, ext="txt"):
    split_pos, doc, labels, text = find_split_position(accumulator, start_pos)
    handle_doc(doc, labels, doc_id, text, output_folder, pool, ext)
    return split_pos


def write_doc(doc, doc_id, labels, text, output_folder, ext="txt", write_png=False):

    if write_png:
        f = f"{output_folder}/img/img_{doc_id}.png"
        doc.render_png(target=f)

    text += " "  # adding a space at EOF
    text = preprocess.split_sentences(text)

    with open(f"{output_folder}/clean_labels/{doc_id}.{ext}", "w") as fp:
        for idx, (token, label) in enumerate(labels):
            fp.write(token + "\t" + label)
            next_token, _ = labels[(idx + 1) % len(labels)]
            if preprocess.is_sentence_separator(
                token
            ) and not preprocess.is_sentence_separator(next_token):
                fp.write("\n")
            if idx == len(labels):  # Reach the end of the document
                fp.write("\n")

    with open(f"{output_folder}/clean_text/{doc_id}.txt", "w") as text_file:
        text_file.write(text)
    return f"wrote: doc id: {doc_id}"


def _error_callback(err):
    raise RuntimeError(err)


def handle_doc(doc, labels, doc_id, text, output_folder, pool, ext="txt"):
    if pool:
        pool.apply_async(
            write_doc,
            args=(doc, doc_id, labels, text, output_folder, ext),
            error_callback=_error_callback,
        )
    else:
        write_doc(doc, doc_id, labels, text, output_folder)


def setup_folder(output_folder):
    os.makedirs(os.path.join(output_folder, "clean_text"), exist_ok=True)
    os.makedirs(os.path.join(output_folder, "clean_labels"), exist_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input_file",
        default="CoNLL-2012_train.txt",
        help="path to input CoNLL formated file.",
    )
    parser.add_argument(
        "output_folder", default="conll2012_train", help="folder to write results to."
    )
    parser.add_argument("--doc_sep", help="CoNLL doc seperator")
    parser.add_argument("--ext", help="file extension", default="txt")
    parser.add_argument(
        "--line_sep", default=CONLL2012_DOC_SEPERATOR, help="CoNLL line seperator"
    )
    parser.add_argument(
        "--force_doc_sep",
        default=False,
        action="store_true",
        help="If set, documents are forced to be split by the doc seperator (recommended to turn this off)",
    )
    args = parser.parse_args()

    unescape = lambda s: s.encode("utf-8").decode("unicode_escape") if s else None  # noqa: E731

    input_file = args.input_file
    output_folder = args.output_folder
    setup_folder(output_folder)

    # allow special characters in seperators
    line_sep = unescape(args.line_sep) or ""
    doc_sep = unescape(args.doc_sep)

    n_workers = WORKERS_PER_CPU * multiprocessing.cpu_count()
    with ThreadPool(processes=n_workers) as pool:
        generate_splits(
            input_file,
            output_folder,
            line_sep,
            doc_seperator=doc_sep,
            pool=pool,
            force_doc_sep=False,
            ext=args.ext,
        )
        pool.close()
        pool.join()
