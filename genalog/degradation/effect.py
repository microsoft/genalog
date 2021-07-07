# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# ---------------------------------------------------------

from math import floor

import cv2
import numpy as np


def blur(src, radius=5):
    """Wrapper function for cv2.GaussianBlur

    Arguments:
        src (numpy.ndarray) : source image of shape (rows, cols)
        radius (int, optional) : size of the square kernel, MUST be an odd integer.
                                 Defaults to 5.

    Returns:
        numpy.ndarray: a copy of the source image after apply the effect
    """
    return cv2.GaussianBlur(src, (radius, radius), cv2.BORDER_DEFAULT)


def overlay_weighted(src, background, alpha, beta, gamma=0):
    """overlay two images together, pixels from each image is weighted as follow

        dst[i] = alpha*src[i] + beta*background[i] + gamma

    Arguments:
        src (numpy.ndarray) : source image of shape (rows, cols)
        background (numpy.ndarray) : background image. Must be in same shape are `src`
        alpha (float) : transparent factor for the foreground
        beta (float) : transparent factor for the background
        gamma (int, optional) : luminance constant. Defaults to 0.

    Returns:
        numpy.ndarray: a copy of the source image after apply the effect
    """
    return cv2.addWeighted(src, alpha, background, beta, gamma).astype(np.uint8)


def overlay(src, background):
    """Overlay two images together via bitwise-and:

        dst[i] = src[i] & background[i]

    Arguments:
        src (numpy.ndarray) : source image of shape (rows, cols)
        background (numpy.ndarray) : background image. Must be in same shape are `src`

    Returns:
        numpy.ndarray: a copy of the source image after apply the effect
    """
    return cv2.bitwise_and(src, background).astype(np.uint8)


def translation(src, offset_x, offset_y):
    """Shift the image in x, y direction

    Arguments:
        src (numpy.ndarray) : source image of shape (rows, cols)
        offset_x (int) : pixels in the x direction.
                          Positive value shifts right and negative shifts right.
        offset_y (int) : pixels in the y direction.
                          Positive value shifts down and negative shifts up.

    Returns:
        numpy.ndarray: a copy of the source image after apply the effect
    """
    rows, cols = src.shape
    trans_matrix = np.float32([[1, 0, offset_x], [0, 1, offset_y]])
    # size of the output image should be in the form of (width, height)
    dst = cv2.warpAffine(src, trans_matrix, (cols, rows), borderValue=255)
    return dst.astype(np.uint8)


def bleed_through(src, background=None, alpha=0.8, gamma=0, offset_x=0, offset_y=5):
    """Apply bleed through effect, background is flipped horizontally.

    Arguments:
        src (numpy.ndarray) : source image of shape (rows, cols)
        background (numpy.ndarray, optional) : background image. Must be in same
                                               shape as foreground. Defaults to None.
        alpha (float, optional) : transparent factor for the foreground. Defaults to 0.8.
        gamma (int, optional) : luminance constant. Defaults to 0.
        offset_x (int, optional) : background translation offset. Defaults to 0.
                                   Positive value shifts right and negative shifts right.
        offset_y (int, optional) : background translation offset. Defaults to 5.
                                   Positive value shifts down and negative shifts up.

    Returns:
        numpy.ndarray: a copy of the source image after apply the effect. Pixel value ranges [0, 255]
    """
    if background is None:
        background = src.copy()
    background = cv2.flip(background, 1)  # flipped horizontally
    background = translation(background, offset_x, offset_y)
    beta = 1 - alpha
    return overlay_weighted(src, background, alpha, beta, gamma)


def pepper(src, amount=0.05):
    """Randomly sprinkle dark pixels on src image.
    Wrapper function for skimage.util.noise.random_noise().
    See https://scikit-image.org/docs/stable/api/skimage.util.html#random-noise

    Arguments:
        src (numpy.ndarray) : source image of shape (rows, cols)
        amount (float, optional) : proportion of pixels in range [0, 1] to apply the effect.
                                   Defaults to 0.05.

    Returns:
        numpy.ndarray: a copy of the source image after apply the effect.
        Pixel value ranges [0, 255] as uint8.
    """
    dst = src.copy()
    # Method returns random floats in uniform distribution [0, 1)
    noise = np.random.random(src.shape)
    dst[noise < amount] = 0
    return dst.astype(np.uint8)


def salt(src, amount=0.3):
    """Randomly sprinkle white pixels on src image.
    Wrapper function for skimage.util.noise.random_noise().
    See https://scikit-image.org/docs/stable/api/skimage.util.html#random-noise

    Arguments:
        src (numpy.ndarray) : source image of shape (rows, cols)
        amount (float, optional) : proportion of pixels in range [0, 1] to apply the effect.
                                   Defaults to 0.05.

    Returns:
        numpy.ndarray: a copy of the source image after apply the effect.
        Pixel value ranges [0, 255]
    """
    dst = src.copy()
    # Method returns random floats in uniform distribution [0, 1)
    noise = np.random.random(src.shape)
    dst[noise < amount] = 255
    return dst.astype(np.uint8)


def salt_then_pepper(src, salt_amount=0.1, pepper_amount=0.05):
    """Randomly add salt then add pepper onto the image.

    Arguments:
        src (numpy.ndarray) : source image of shape (rows, cols)
        salt_amount (float) : proportion of pixels in range [0, 1] to
                              apply the salt effect.
                              Defaults to 0.1.
        pepper_amount (float) : proportion of pixels in range [0, 1] to
                                apply the pepper effect.
                                Defaults to 0.05.

    Returns:
        numpy.ndarray: a copy of the source image after apply the effect.
        Pixel value ranges [0, 255] as uint8.
    """
    salted = salt(src, amount=salt_amount)
    return pepper(salted, amount=pepper_amount)


def pepper_then_salt(src, pepper_amount=0.05, salt_amount=0.1):
    """Randomly add pepper then salt onto the image.

    Arguments:
        src (numpy.ndarray) : source image of shape (rows, cols)
        pepper_amount (float) : proportion of pixels in range [0, 1] to
                                apply the pepper effect.
                                Defaults to 0.05.
        salt_amount (float) : proportion of pixels in range [0, 1] to
                              apply the salt effect.
                              Defaults to 0.1.

    Returns:
        numpy.ndarray: a copy of the source image after apply the effect.
        Pixel value ranges [0, 255] as uint8.
    """
    peppered = pepper(src, amount=pepper_amount)
    return salt(peppered, amount=salt_amount)


def create_2D_kernel(kernel_shape, kernel_type="ones"):
    """Create 2D kernel for morphological operations.

    Arguments:
        kernel_shape (tuple) : shape of the kernel (rows, cols)
        kernel_type (str, optional) : type of kernel. Defaults to "ones".
    ::

        All supported kernel types are below:

        "ones": kernel is filled with all 1s in shape (rows, cols)
                    [[1,1,1],
                    [1,1,1],
                    [1,1,1]]
        "upper_triangle": upper triangular matrix filled with ones
                    [[1,1,1],
                    [0,1,1],
                    [0,0,1]]
        "lower_triangle": lower triangular matrix filled with ones
                    [[1,0,0],
                    [1,1,0],
                    [1,1,1]]
        "x": "X" shape cross
                    [[1,0,1],
                    [0,1,0],
                    [1,0,1]]
        "plus": "+" shape cross
                    [[0,1,0],
                    [1,1,1],
                    [0,1,0]]
        "ellipse": elliptical kernel
                    [[0, 0, 1, 0, 0],
                    [1, 1, 1, 1, 1],
                    [1, 1, 1, 1, 1],
                    [1, 1, 1, 1, 1],
                    [0, 0, 1, 0, 0]]

    Raises:
        ValueError: if kernel is not a 2-element tuple or
                    kernel_type is not one of the supported values

    Returns:
        numpy.ndarray: a 2D array of shape `kernel_shape`.
    """
    if len(kernel_shape) != 2:
        raise ValueError("Kernel shape must be a tuple of 2 integers")
    kernel_rows, kernel_cols = kernel_shape
    if kernel_type == "ones":
        kernel = np.ones(kernel_shape)
    elif kernel_type == "upper_triangle":
        kernel = np.triu(np.ones(kernel_shape))
    elif kernel_type == "lower_triangle":
        kernel = np.tril(np.ones(kernel_shape))
    elif kernel_type == "x":
        diagonal = np.eye(kernel_rows, kernel_cols)
        kernel = np.add(diagonal, np.fliplr(diagonal))
        kernel[kernel > 1] = 1
    elif kernel_type == "plus":
        kernel = np.zeros(kernel_shape)
        center_col = floor(kernel.shape[0] / 2)
        center_row = floor(kernel.shape[1] / 2)
        kernel[:, center_col] = 1
        kernel[center_row, :] = 1
    elif kernel_type == "ellipse":
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, kernel_shape)
    else:
        valid_kernel_types = {
            "ones",
            "upper_triangle",
            "lower_triangle",
            "x",
            "plus",
            "ellipse",
        }
        raise ValueError(
            f"Invalid kernel_type: {kernel_type}. Valid types are {valid_kernel_types}"
        )

    return kernel.astype(np.uint8)


def morphology(src, operation="open", kernel_shape=(3, 3), kernel_type="ones"):
    """Dynamic calls different morphological operations
    ("open", "close", "dilate" and "erode") with the given parameters

    Arguments:
        src (numpy.ndarray) : source image of shape (rows, cols)
        operation (str, optional) : name of a morphological operation:
                                    ``("open", "close", "dilate", "erode")``
                                    Defaults to ``"open"``.
        kernel_shape (tuple, optional) : shape of the kernel (rows, cols).
                                         Defaults to (3,3).
        kernel_type (str, optional) : type of kernel.
            ``("ones", "upper_triangle", "lower_triangle", "x", "plus", "ellipse")``
            Defaults to ``"ones"``.

    Returns:
        numpy.ndarray: a copy of the source image after apply the effect.
    """
    kernel = create_2D_kernel(kernel_shape, kernel_type)
    if operation == "open":
        return open(src, kernel)
    elif operation == "close":
        return close(src, kernel)
    elif operation == "dilate":
        return dilate(src, kernel)
    elif operation == "erode":
        return erode(src, kernel)
    else:
        valid_operations = ["open", "close", "dilate", "erode"]
        raise ValueError(
            f"Invalid morphology operation '{operation}'. Valid morphological operations are {valid_operations}"
        )


def open(src, kernel):
    """ "open" morphological operation. Like morphological "erosion", it removes
    foreground pixels (white pixels), however it is less destructive than erosion.

    For more information see:

    1. https://docs.opencv.org/master/d9/d61/tutorial_py_morphological_ops.html
    2. http://homepages.inf.ed.ac.uk/rbf/HIPR2/open.htm

    Arguments:
        src (numpy.ndarray) : source image of shape (rows, cols)
        kernel (numpy.ndarray) : a 2D array for structuring the morphological effect

    Returns:
        numpy.ndarray: a copy of the source image after apply the effect.
    """
    return cv2.morphologyEx(src, cv2.MORPH_OPEN, kernel)


def close(src, kernel):
    """ "close" morphological operation. Like morphological "dilation", it grows the
    boundary of the foreground (white pixels), however, it is less destructive than
    dilation of the original boundary shape.

    For more information see:

    1. https://docs.opencv.org/master/d9/d61/tutorial_py_morphological_ops.html
    2. http://homepages.inf.ed.ac.uk/rbf/HIPR2/close.htm

    Arguments:
        src (numpy.ndarray) : source image of shape (rows, cols)
        kernel (numpy.ndarray) : a 2D array for structuring the morphological effect

    Returns:
        numpy.ndarray: a copy of the source image after apply the effect.
    """
    return cv2.morphologyEx(src, cv2.MORPH_CLOSE, kernel)


def erode(src, kernel):
    """ "erode" morphological operation. Erodes foreground pixels (white pixels).

    For more information see:

    1. https://docs.opencv.org/master/d9/d61/tutorial_py_morphological_ops.html
    2. http://homepages.inf.ed.ac.uk/rbf/HIPR2/erode.htm

    Arguments:
        src (numpy.ndarray) : source image of shape (rows, cols)
        kernel (numpy.ndarray) : a 2D array for structuring the morphological effect

    Returns:
        numpy.ndarray: a copy of the source image after apply the effect.
    """
    return cv2.erode(src, kernel)


def dilate(src, kernel):
    """ "dilate" morphological operation. Grows foreground pixels (white pixels).

    For more information see:

    1. https://docs.opencv.org/master/d9/d61/tutorial_py_morphological_ops.html
    2. http://homepages.inf.ed.ac.uk/rbf/HIPR2/dilate.htm

    Arguments:
        src (numpy.ndarray) : source image of shape (rows, cols)
        kernel (numpy.ndarray) : a 2D array for structuring the morphological effect

    Returns:
        numpy.ndarray: a copy of the source image after apply the effect.
    """
    return cv2.dilate(src, kernel)
