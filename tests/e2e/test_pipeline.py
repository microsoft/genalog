import glob

import pytest

from genalog import pipeline

EXAMPLE_TEXT_FILE = "tests/unit/text/data/gt_1.txt"


@pytest.fixture
def default_analog_generator():
    return pipeline.AnalogDocumentGeneration()


@pytest.fixture
def custom_analog_generator():
    custom_styles = {"font_size": ["5px"]}
    custom_degradation = [("blur", {"radius": 3})]
    return pipeline.AnalogDocumentGeneration(
        styles=custom_styles, degradations=custom_degradation, resolution=300
    )


def test_default_generate_img(default_analog_generator):
    example_template = default_analog_generator.list_templates()[0]
    default_analog_generator.generate_img(
        EXAMPLE_TEXT_FILE, example_template, target_folder=None
    )


def test_custom_generate_img(custom_analog_generator):
    example_template = custom_analog_generator.list_templates()[0]
    custom_analog_generator.generate_img(
        EXAMPLE_TEXT_FILE, example_template, target_folder=None
    )


def test_generate_dataset_multiprocess():
    INPUT_TEXT_FILENAMES = glob.glob("tests/unit/text/data/gt_*.txt")
    with pytest.deprecated_call():
        pipeline.generate_dataset_multiprocess(
            INPUT_TEXT_FILENAMES, "test_out", {}, [], "text_block.html.jinja"
        )
