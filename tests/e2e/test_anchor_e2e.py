import difflib
import glob
import warnings

import pytest

from genalog.text import alignment, anchor, preprocess


@pytest.mark.slow
@pytest.mark.parametrize(
    "gt_file, ocr_file",
    zip(
        sorted(glob.glob("tests/unit/text/data/gt_*.txt")),
        sorted(glob.glob("tests/unit/text/data/ocr_*.txt")),
    ),
)
def test_align_w_anchor_and_align(gt_file, ocr_file):
    gt_text = open(gt_file, "r").read()
    ocr_text = open(ocr_file, "r").read()
    aligned_anchor_gt, aligned_anchor_noise = anchor.align_w_anchor(gt_text, ocr_text)
    aligned_gt, aligned_noise = alignment.align(gt_text, ocr_text)

    if aligned_gt != aligned_anchor_gt:
        aligned_anchor_gt = aligned_anchor_gt.split(".")
        aligned_gt = aligned_gt.split(".")
        str_diff = "\n".join(difflib.unified_diff(aligned_gt, aligned_anchor_gt))
        warnings.warn(
            UserWarning(
                "\n"
                + f"{str_diff}"
                + "\n\n**** Inconsistent Alignment Results between align() and "
                + "align_w_anchor(). Ignore this if the delta is not significant. ****\n"
            )
        )


@pytest.mark.slow
@pytest.mark.parametrize(
    "gt_file, ocr_file",
    zip(
        sorted(glob.glob("tests/unit/text/data/gt_*.txt")),
        sorted(glob.glob("tests/unit/text/data/ocr_*.txt")),
    ),
)
@pytest.mark.parametrize("max_seg_length", [25, 50, 75, 100, 150])
def test_find_anchor_recur_e2e(gt_file, ocr_file, max_seg_length):
    gt_text = open(gt_file, "r").read()
    ocr_text = open(ocr_file, "r").read()
    gt_tokens = preprocess.tokenize(gt_text)
    ocr_tokens = preprocess.tokenize(ocr_text)
    gt_anchors, ocr_anchors = anchor.find_anchor_recur(
        gt_tokens, ocr_tokens, max_seg_length=max_seg_length
    )
    for gt_anchor, ocr_anchor in zip(gt_anchors, ocr_anchors):
        # Ensure that each anchor word is the same word in both text
        assert gt_tokens[gt_anchor] == ocr_tokens[ocr_anchor]
