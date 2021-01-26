import glob
import itertools

import pytest

from genalog.text import conll_format


@pytest.mark.slow
@pytest.mark.parametrize(
    "required_args", [(["tests/e2e/data/synthetic_dataset", "test_version"])]
)
@pytest.mark.parametrize(
    "optional_args",
    [
        (["--train_subset"]),
        (["--test_subset"]),
        (["--gt_folder", "shared"]),
    ],
)
def test_conll_format(required_args, optional_args):
    parser = conll_format.create_parser()
    arg_list = required_args + optional_args
    args = parser.parse_args(args=arg_list)
    conll_format.main(args)


basepath = "tests/e2e/data/conll_formatter/"


@pytest.mark.slow
@pytest.mark.parametrize(
    "clean_label_filename, ocr_text_filename",
    zip(
        sorted(glob.glob("tests/e2e/data/conll_formatter/clean_labels/*.txt")),
        sorted(glob.glob("tests/e2e/data/conll_formatter/ocr_text/*.txt")),
    ),
)
def test_propagate_labels_sentence_single_file(clean_label_filename, ocr_text_filename):
    with open(clean_label_filename, "r", encoding="utf-8") as clf:
        tokens_labels_str = clf.readlines()
    clean_tokens = [
        line.split()[0].strip() for line in tokens_labels_str if len(line.split()) == 2
    ]
    clean_labels = [
        line.split()[1].strip() for line in tokens_labels_str if len(line.split()) == 2
    ]
    clean_sentences = conll_format.get_sentences_from_iob_format(tokens_labels_str)
    # read ocr tokens
    with open(ocr_text_filename, "r", encoding="utf-8") as otf:
        ocr_text_str = " ".join(otf.readlines())
    ocr_tokens = [
        token.strip() for token in ocr_text_str.split()
    ]  # already tokenized in data

    ocr_text_sentences, ocr_labels_sentences = conll_format.propagate_labels_sentences(
        clean_tokens, clean_labels, clean_sentences, ocr_tokens
    )
    ocr_sentences_flatten = list(itertools.chain(*ocr_text_sentences))
    assert len(ocr_text_sentences) == len(clean_sentences)
    assert len(ocr_text_sentences) == len(ocr_labels_sentences)
    assert len(ocr_sentences_flatten) == len(
        ocr_tokens
    )  # ensure aligned ocr tokens == ocr tokens
