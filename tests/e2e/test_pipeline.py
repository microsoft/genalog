import os
import glob

import pytest

from genalog import pipeline
from genalog.generation.document import DocumentGenerator

EXAMPLE_TEXT_FILE = "tests/unit/text/data/gt_1.txt"
INPUT_TEXT_FILENAMES = glob.glob("tests/unit/text/data/gt_*.txt")

STYLES = {"font_size": ["5px"]}
STYLES_COMBINATION = {"font_size": ["5px", "6px"]}  # Multiple values per style are not supported right now
DEGRATIONS = [
    ("blur", {"radius": 3}),
    ("morphology", {"operation": "close"})
]


@pytest.fixture
def default_analog_generator():
    return pipeline.AnalogDocumentGeneration()


@pytest.fixture
def custom_analog_generator():
    return pipeline.AnalogDocumentGeneration(
        styles=STYLES, degradations=DEGRATIONS, resolution=300
    )


def test_default_generate_img(default_analog_generator):
    assert len(default_analog_generator.list_templates()) > 0
    example_template = default_analog_generator.list_templates()[0]
    default_analog_generator.generate_img(
        EXAMPLE_TEXT_FILE, example_template, target_folder=None
    )


def test_custom_generate_img(custom_analog_generator):
    assert len(custom_analog_generator.list_templates()) > 0
    example_template = custom_analog_generator.list_templates()[0]
    custom_analog_generator.generate_img(
        EXAMPLE_TEXT_FILE, example_template, target_folder=None
    )


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
    pipeline.generate_dataset_multiprocess(
        INPUT_TEXT_FILENAMES, output_folder, styles, DEGRATIONS, "text_block.html.jinja"
    )
    num_generated_img = glob.glob(os.path.join(output_folder, "**/*.png"))
    assert len(num_generated_img) > 0
    assert len(num_generated_img) == len(INPUT_TEXT_FILENAMES) * len(DocumentGenerator.expand_style_combinations(styles))
