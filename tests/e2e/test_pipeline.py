import glob
import os

import numpy as np
import pytest

from genalog.generation.document import DocumentGenerator
from genalog.pipeline import AnalogDocumentGeneration, generate_dataset_multiprocess

EXAMPLE_TEXT_FILE = "tests/unit/text/data/gt_1.txt"
INPUT_TEXT_FILENAMES = glob.glob("tests/unit/text/data/gt_*.txt")

STYLES = {"font_size": ["5px"]}
STYLES_COMBINATION = {"font_size": ["5px", "6px"]}  # Multiple values per style are not supported right now
DEGRATIONS = [
    ("blur", {"radius": 3}),
    ("morphology", {"operation": "close"})
]


@pytest.fixture
def default_doc_generator():
    return AnalogDocumentGeneration()


@pytest.fixture
def custom_doc_generator():
    return AnalogDocumentGeneration(styles=STYLES, degradations=DEGRATIONS, resolution=300)


@pytest.fixture
def empty_style_doc_generator():
    return AnalogDocumentGeneration(styles={})


@pytest.mark.parametrize("doc_generator", [
    pytest.lazy_fixture('default_doc_generator'),
    pytest.lazy_fixture('custom_doc_generator')
])
def test_generate_img_array(doc_generator):
    # Precondition checks
    assert len(doc_generator.list_templates()) > 0

    example_template = doc_generator.list_templates()[0]
    sample_img = doc_generator.generate_img(
        EXAMPLE_TEXT_FILE, example_template, target_folder=None
    )
    assert sample_img is not None
    assert isinstance(sample_img, np.ndarray)


def test_generate_img_array_empty(empty_style_doc_generator):
    # Precondition checks
    assert len(empty_style_doc_generator.list_templates()) > 0

    example_template = empty_style_doc_generator.list_templates()[0]
    sample_img = empty_style_doc_generator.generate_img(
        EXAMPLE_TEXT_FILE, example_template, target_folder=None
    )
    assert sample_img is None


@pytest.mark.io
@pytest.mark.parametrize("doc_generator", [
    pytest.lazy_fixture('default_doc_generator'),
    pytest.lazy_fixture('custom_doc_generator')
])
def test_generate_img_write_to_disk(tmpdir, doc_generator):
    os.makedirs(os.path.join(tmpdir, "img"))  # TODO: generate_img() store image under "img" folder
    output_img_wildcard = os.path.join(tmpdir, "img", "*.png")
    num_generated_img = glob.glob(output_img_wildcard)
    # Precondition checks
    assert len(num_generated_img) == 0
    assert len(doc_generator.list_templates()) > 0

    example_template = doc_generator.list_templates()[0]
    doc_generator.generate_img(
        EXAMPLE_TEXT_FILE, example_template, target_folder=tmpdir
    )
    num_generated_img = glob.glob(output_img_wildcard)  # look for any jpg on file
    assert len(num_generated_img) > 0


@pytest.mark.io
@pytest.mark.parametrize("styles", [
    STYLES,
    pytest.param(
        STYLES_COMBINATION, marks=pytest.mark.xfail(
            reason="Style combinations are not supported. Only one value per style", strict=True)
    )
])
@pytest.mark.parametrize("folder_name", ["result", "result/"])
def test_generate_dataset_multiprocess(tmpdir, folder_name, styles):
    assert len(INPUT_TEXT_FILENAMES) > 0
    output_folder = os.path.join(tmpdir, folder_name)
    generate_dataset_multiprocess(
        INPUT_TEXT_FILENAMES, output_folder, styles, DEGRATIONS, "text_block.html.jinja"
    )
    num_generated_img = glob.glob(os.path.join(output_folder, "**", "*.png"))
    assert len(num_generated_img) > 0
    assert len(num_generated_img) == len(INPUT_TEXT_FILENAMES) * len(DocumentGenerator.expand_style_combinations(styles))
