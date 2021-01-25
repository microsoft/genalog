import difflib
import os

from genalog.text.splitter import CONLL2003_DOC_SEPERATOR, generate_splits


def _compare_content(file1, file2):
    txt1 = open(file1, "r").read()
    txt2 = open(file2, "r").read()
    sentences_txt1 = txt1.split("\n")
    sentences_txt2 = txt2.split("\n")
    if txt1 != txt2:
        str_diff = "\n".join(difflib.unified_diff(sentences_txt1, sentences_txt2))
        assert False, f"Delta between outputs: \n {str_diff}"


def test_splitter(tmpdir):
    # tmpdir = "test_out"
    os.makedirs(f"{tmpdir}/clean_labels")
    os.makedirs(f"{tmpdir}/clean_text")

    generate_splits(
        "tests/e2e/data/splitter/example_conll2012.txt",
        tmpdir,
        doc_seperator=CONLL2003_DOC_SEPERATOR,
        sentence_seperator="",
    )

    _compare_content(
        "tests/e2e/data/splitter/example_splits/clean_text/0.txt",
        f"{tmpdir}/clean_text/0.txt",
    )
    _compare_content(
        "tests/e2e/data/splitter/example_splits/clean_text/1.txt",
        f"{tmpdir}/clean_text/1.txt",
    )
    _compare_content(
        "tests/e2e/data/splitter/example_splits/clean_labels/0.txt",
        f"{tmpdir}/clean_labels/0.txt",
    )
    _compare_content(
        "tests/e2e/data/splitter/example_splits/clean_labels/1.txt",
        f"{tmpdir}/clean_labels/1.txt",
    )
