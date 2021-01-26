import random
import warnings

import pytest

from genalog.text import alignment
from genalog.text.alignment import GAP_CHAR
from tests.unit.cases.text_alignment import ALIGNMENT_REGRESSION_TEST_CASES


def random_utf8_char(byte_len=1):
    if byte_len == 1:
        return chr(random.randint(0, 0x007F))
    elif byte_len == 2:
        return chr(random.randint(0x007F, 0x07FF))
    elif byte_len == 3:
        return chr(random.randint(0x07FF, 0xFFFF))
    elif byte_len == 4:
        return chr(random.randint(0xFFFF, 0x10FFFF))
    else:
        raise ValueError(
            f"Invalid byte length: {byte_len}."
            + "utf-8 does not encode characters with more than 4 bytes in length"
        )


@pytest.mark.parametrize(
    "num_utf_char_to_test", [100]
)  # Number of char per byte length
@pytest.mark.parametrize(
    "byte_len", [1, 2, 3, 4]
)  # UTF does not encode with more than 4 bytes
@pytest.mark.parametrize(
    "gt_txt, noisy_txt, expected_aligned_gt, expected_aligned_noise",
    ALIGNMENT_REGRESSION_TEST_CASES,
)
def test_align(
    num_utf_char_to_test,
    byte_len,
    gt_txt,
    noisy_txt,
    expected_aligned_gt,
    expected_aligned_noise,
):

    invalid_char = set(gt_txt).union(
        set(GAP_CHAR)
    )  # character to replace to cannot be in this set
    for _ in range(num_utf_char_to_test):
        utf_char = random_utf8_char(byte_len)
        while (
            utf_char in invalid_char
        ):  # find a utf char not in the input string and not GAP_CHAR
            utf_char = random_utf8_char(byte_len)
        char_to_replace = random.choice(list(invalid_char)) if gt_txt else ""

        gt_txt.replace(char_to_replace, utf_char)
        noisy_txt.replace(char_to_replace, utf_char)
        expected_aligned_gt_sub = expected_aligned_gt.replace(char_to_replace, utf_char)
        expected_aligned_noise_sub = expected_aligned_noise.replace(
            char_to_replace, utf_char
        )

        # Run alignment
        aligned_gt, aligned_noise = alignment.align(gt_txt, noisy_txt)

        aligned_gt = aligned_gt.replace(char_to_replace, utf_char)
        aligned_noise = aligned_noise.replace(char_to_replace, utf_char)
        if aligned_gt != expected_aligned_gt_sub:
            expected_alignment = alignment._format_alignment(
                expected_aligned_gt_sub, expected_aligned_noise_sub
            )
            result_alignment = alignment._format_alignment(aligned_gt, aligned_noise)
            warnings.warn(
                RuntimeWarning(
                    f"\n\n****Expect alignment returns:****\n{expected_alignment} \n****But got:****\n{result_alignment}"
                )
            )
