from unittest.mock import patch

import numpy as np
import pytest

from genalog.degradation import effect

NEW_IMG_SHAPE = (100, 100)
MOCK_IMG_SHAPE = (100, 120)
MOCK_IMG = np.ones(MOCK_IMG_SHAPE, dtype=np.uint8)


def test_blur():
    dst = effect.blur(MOCK_IMG, radius=3)
    assert dst.dtype == np.uint8  # preverse dtype
    assert dst.shape == MOCK_IMG_SHAPE  # preverse image size


def test_translation():
    offset_x = offset_y = 1
    # Test that border pixels are not white (<255)
    assert all([col_pixel < 255 for col_pixel in MOCK_IMG[:, 0]])
    assert all([row_pixel < 255 for row_pixel in MOCK_IMG[0, :]])
    dst = effect.translation(MOCK_IMG, offset_x, offset_y)
    # Test that border pixels are white (255)
    assert all([col_pixel == 255 for col_pixel in dst[:, 0]])
    assert all([row_pixel == 255 for row_pixel in dst[0, :]])
    assert dst.dtype == np.uint8
    assert dst.shape == MOCK_IMG_SHAPE


def test_overlay_weighted():
    src = MOCK_IMG.copy()
    src[0][0] = 10
    alpha = beta = 1
    dst = effect.overlay_weighted(src, src, alpha, beta)
    assert dst.dtype == np.uint8
    assert dst.shape == MOCK_IMG_SHAPE
    assert dst[0][0] == src[0][0] * alpha + src[0][0] * beta


def test_overlay():
    src1 = MOCK_IMG.copy()
    src2 = MOCK_IMG.copy()
    src1[0][0] = 100
    src2[0][0] = 0
    dst = effect.overlay(src1, src2)
    assert dst.dtype == np.uint8
    assert dst.shape == MOCK_IMG_SHAPE
    assert dst[0][0] == 0
    assert dst[0][1] == 1


@patch("genalog.degradation.effect.translation")
def test_bleed_through_default(mock_translation):
    mock_translation.return_value = MOCK_IMG
    dst = effect.bleed_through(MOCK_IMG)
    assert mock_translation.called
    assert dst.dtype == np.uint8
    assert dst.shape == MOCK_IMG_SHAPE


@pytest.mark.parametrize(
    "foreground, background, error_thrown",
    [
        (MOCK_IMG, MOCK_IMG, None),
        # Test unmatched shape
        (MOCK_IMG, MOCK_IMG[:, :-1], Exception),
    ],
)
def test_bleed_through_kwargs(foreground, background, error_thrown):
    if error_thrown:
        assert foreground.shape != background.shape
        with pytest.raises(error_thrown):
            effect.bleed_through(foreground, background=background)
    else:
        dst = effect.bleed_through(foreground, background=background)
        assert dst.dtype == np.uint8
        assert dst.shape == MOCK_IMG_SHAPE


def test_pepper():
    dst = effect.pepper(MOCK_IMG, amount=0.1)
    assert dst.dtype == np.uint8
    assert dst.shape == MOCK_IMG_SHAPE


def test_salt():
    dst = effect.salt(MOCK_IMG, amount=0.1)
    assert dst.dtype == np.uint8
    assert dst.shape == MOCK_IMG_SHAPE


def test_salt_then_pepper():
    dst = effect.salt_then_pepper(MOCK_IMG, 0.5, 0.001)
    assert dst.dtype == np.uint8
    assert dst.shape == MOCK_IMG_SHAPE


def test_pepper_then_salt():
    dst = effect.pepper_then_salt(MOCK_IMG, 0.001, 0.5)
    assert dst.dtype == np.uint8
    assert dst.shape == MOCK_IMG_SHAPE


@pytest.mark.parametrize(
    "kernel_shape, kernel_type",
    [((3, 3), "NOT_VALID_TYPE"), (1, "ones"), ((1, 2, 3), "ones")],
)
def test_create_2D_kernel_error(kernel_shape, kernel_type):
    with pytest.raises(Exception):
        effect.create_2D_kernel(kernel_shape, kernel_type)


@pytest.mark.parametrize(
    "kernel_shape, kernel_type, expected_kernel",
    [
        ((2, 2), "ones", np.array([[1, 1], [1, 1]])),  # sq kernel
        ((1, 2), "ones", np.array([[1, 1]])),  # horizontal
        ((2, 1), "ones", np.array([[1], [1]])),  # vertical
        ((2, 2), "upper_triangle", np.array([[1, 1], [0, 1]])),
        ((2, 2), "lower_triangle", np.array([[1, 0], [1, 1]])),
        ((2, 2), "x", np.array([[1, 1], [1, 1]])),
        ((3, 3), "x", np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]])),
        ((2, 2), "plus", np.array([[0, 1], [1, 1]])),
        ((3, 3), "plus", np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])),
        ((3, 3), "ellipse", np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])),
        (
            (5, 5),
            "ellipse",
            np.array(
                [
                    [0, 0, 1, 0, 0],
                    [1, 1, 1, 1, 1],
                    [1, 1, 1, 1, 1],
                    [1, 1, 1, 1, 1],
                    [0, 0, 1, 0, 0],
                ]
            ),
        ),
    ],
)
def test_create_2D_kernel(kernel_shape, kernel_type, expected_kernel):
    kernel = effect.create_2D_kernel(kernel_shape, kernel_type)
    assert np.array_equal(kernel, expected_kernel)


def test_morphology_with_error():
    INVALID_OPERATION = "NOT_A_OPERATION"
    with pytest.raises(ValueError):
        effect.morphology(MOCK_IMG, operation=INVALID_OPERATION)


@pytest.mark.parametrize(
    "operation, kernel_shape, kernel_type",
    [
        ("open", (3, 3), "ones"),
        ("close", (3, 3), "ones"),
        ("dilate", (3, 3), "ones"),
        ("erode", (3, 3), "ones"),
    ],
)
def test_morphology(operation, kernel_shape, kernel_type):
    dst = effect.morphology(
        MOCK_IMG,
        operation=operation,
        kernel_shape=kernel_shape,
        kernel_type=kernel_type,
    )
    assert dst.dtype == np.uint8
    assert dst.shape == MOCK_IMG_SHAPE


@pytest.fixture(
    params=["ones", "upper_triangle", "lower_triangle", "x", "plus", "ellipse"]
)
def kernel(request):
    return effect.create_2D_kernel((5, 5), request.param)


def test_open(kernel):
    dst = effect.open(MOCK_IMG, kernel)
    assert dst.dtype == np.uint8
    assert dst.shape == MOCK_IMG_SHAPE


def test_close(kernel):
    dst = effect.close(MOCK_IMG, kernel)
    assert dst.dtype == np.uint8
    assert dst.shape == MOCK_IMG_SHAPE


def test_erode(kernel):
    dst = effect.erode(MOCK_IMG, kernel)
    assert dst.dtype == np.uint8
    assert dst.shape == MOCK_IMG_SHAPE


def test_dilate(kernel):
    dst = effect.dilate(MOCK_IMG, kernel)
    assert dst.dtype == np.uint8
    assert dst.shape == MOCK_IMG_SHAPE
