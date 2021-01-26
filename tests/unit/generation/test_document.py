from unittest.mock import MagicMock, patch

import pytest

from genalog.generation.document import DEFAULT_DOCUMENT_STYLE
from genalog.generation.document import Document, DocumentGenerator


FRENCH = "fr"
CONTENT = ["some text"]
MOCK_COMPILED_DOCUMENT = "<p>populated document</p>"
MOCK_TEMPLATE = MagicMock()
MOCK_TEMPLATE.render.return_value = MOCK_COMPILED_DOCUMENT

IMG_BYTES = open("tests/unit/generation/2x2.jpg", "rb").read()

FILE_DESTINATION_PDF = "sample.pdf"
FILE_DESTINATION_PNG = "sample.png"

CUSTOM_TEMPLATE_PATH = "tests/unit/generation/templates"
CUSTOM_TEMPLATE_NAME = "mock.html.jinja"
DEFAULT_TEMPLATE_NAME = "text_block.html.jinja"
DEFAULT_PACKAGE_NAME = "genalog.generation"
DEFAULT_TEMPLATE_FOLDER = "templates"


@pytest.fixture
def default_document():
    mock_jinja_template = MagicMock()
    mock_jinja_template.render.return_value = MOCK_COMPILED_DOCUMENT
    return Document(CONTENT, mock_jinja_template)


@pytest.fixture
def french_document():
    mock_jinja_template = MagicMock()
    mock_jinja_template.render.return_value = MOCK_COMPILED_DOCUMENT
    return Document(CONTENT, mock_jinja_template, language=FRENCH)


def test_document_init(default_document):
    assert default_document.styles == DEFAULT_DOCUMENT_STYLE
    assert default_document._document is not None
    assert default_document.compiled_html is not None


def test_document_init_with_kwargs(french_document):
    assert french_document.styles["language"] == FRENCH
    assert french_document._document is not None
    assert french_document.compiled_html is not None


def test_document_render_html(french_document):
    compiled_document = french_document.render_html()
    assert compiled_document == MOCK_COMPILED_DOCUMENT
    french_document.template.render.assert_called_with(
        content=CONTENT, **french_document.styles
    )


def test_document_render_pdf(default_document):
    default_document._document = MagicMock()
    # run tested function
    default_document.render_pdf(target=FILE_DESTINATION_PDF, zoom=2)
    default_document._document.write_pdf.assert_called_with(
        target=FILE_DESTINATION_PDF, zoom=2
    )


def test_document_render_png(default_document):
    default_document._document = MagicMock()
    # run tested function
    default_document.render_png(target=FILE_DESTINATION_PNG, resolution=100)
    default_document._document.write_png.assert_called_with(
        target=FILE_DESTINATION_PNG, resolution=100
    )


def test_document_render_png_split_pages(default_document):
    default_document._document.copy = MagicMock()
    # run tested function
    default_document.render_png(
        target=FILE_DESTINATION_PNG, split_pages=True, resolution=100
    )
    result_destination = FILE_DESTINATION_PNG.replace(".png", "_pg_0.png")
    # assertion
    document_copy = default_document._document.copy.return_value
    document_copy.write_png.assert_called_with(
        target=result_destination, resolution=100
    )


def test_document_render_array_valid_args(default_document):
    # setup mock
    mock_surface = MagicMock()
    mock_surface.get_format.return_value = 0  # 0 == cairocffi.FORMAT_ARGB32
    mock_surface.get_data = MagicMock(return_value=IMG_BYTES)  # loading a 2x2 image
    mock_write_image_surface = MagicMock(return_value=(mock_surface, 2, 2))
    default_document._document.write_image_surface = mock_write_image_surface

    channel_types = ["RGBA", "RGB", "GRAYSCALE", "BGRA", "BGR"]
    expected_img_shape = [(2, 2, 4), (2, 2, 3), (2, 2), (2, 2, 4), (2, 2, 3)]

    for channel_type, expected_img_shape in zip(channel_types, expected_img_shape):
        img_array = default_document.render_array(resolution=100, channel=channel_type)
        assert img_array.shape == expected_img_shape


def test_document_render_array_invalid_args(default_document):
    invalid_channel_types = "INVALID"
    with pytest.raises(ValueError):
        default_document.render_array(resolution=100, channel=invalid_channel_types)


def test_document_render_array_invalid_format(default_document):
    # setup mock
    mock_surface = MagicMock()
    mock_surface.get_format.return_value = 1  # 1 != cairocffi.FORMAT_ARGB32
    mock_write_image_surface = MagicMock(return_value=(mock_surface, 2, 2))
    default_document._document.write_image_surface = mock_write_image_surface

    with pytest.raises(RuntimeError):
        default_document.render_array(resolution=100)


def test_document_update_style(default_document):
    new_style = {"language": FRENCH, "new_property": "some value"}
    # Ensure that a new property is not already defined
    with pytest.raises(KeyError):
        default_document.styles["new_property"]
    assert default_document.styles["language"] != FRENCH
    # update
    default_document.update_style(**new_style)
    assert default_document.styles["language"] == FRENCH
    # Ensure that a new property is added
    assert default_document.styles["new_property"] == new_style["new_property"]


@patch("genalog.generation.document.Environment")
@patch("genalog.generation.document.PackageLoader")
@patch("genalog.generation.document.FileSystemLoader")
def test_document_generator_init_default_setting(
    mock_file_system_loader, mock_package_loader, mock_environment
):
    # setup mock template environment
    mock_environment_instance = mock_environment.return_value
    mock_environment_instance.list_templates.return_value = [DEFAULT_TEMPLATE_NAME]
    # run the tested method
    document_generator = DocumentGenerator()
    # Ensure the right loader is called
    mock_file_system_loader.assert_not_called()
    mock_package_loader.assert_called_with(
        DEFAULT_PACKAGE_NAME, DEFAULT_TEMPLATE_FOLDER
    )
    # Ensure that the default template in the package is loaded
    assert DEFAULT_TEMPLATE_NAME in document_generator.template_list


@patch("genalog.generation.document.Environment")
@patch("genalog.generation.document.PackageLoader")
@patch("genalog.generation.document.FileSystemLoader")
def test_document_generator_init_custom_template(
    mock_file_system_loader, mock_package_loader, mock_environment
):
    # setup mock template environment
    mock_environment_instance = mock_environment.return_value
    mock_environment_instance.list_templates.return_value = [CUSTOM_TEMPLATE_NAME]
    # run the tested method
    document_generator = DocumentGenerator(template_path=CUSTOM_TEMPLATE_PATH)
    # Ensure the right loader is called
    mock_package_loader.assert_not_called()
    mock_file_system_loader.assert_called_with(CUSTOM_TEMPLATE_PATH)
    # Ensure that the expected template is registered
    assert CUSTOM_TEMPLATE_NAME in document_generator.template_list


@pytest.fixture
def default_document_generator():
    with patch("genalog.generation.document.Environment") as MockEnvironment:
        template_environment_instance = MockEnvironment.return_value
        template_environment_instance.list_templates.return_value = [
            DEFAULT_TEMPLATE_NAME
        ]
        template_environment_instance.get_template.return_value = MOCK_TEMPLATE
        doc_gen = DocumentGenerator()
    return doc_gen


def test_document_generator_create_generator(default_document_generator):
    available_templates = default_document_generator.template_list
    assert len(available_templates) < 2
    generator = default_document_generator.create_generator(
        CONTENT, available_templates
    )
    next(generator)
    with pytest.raises(StopIteration):
        next(generator)


def test_document_generator_create_generator_(default_document_generator):
    # setup test case
    available_templates = default_document_generator.template_list
    undefined_template = "NOT A VALID TEMPLATE"
    assert undefined_template not in available_templates

    generator = default_document_generator.create_generator(
        CONTENT, [undefined_template]
    )
    with pytest.raises(FileNotFoundError):
        next(generator)


@pytest.mark.parametrize(
    "template_name, expected_output",
    [
        ("base.html.jinja", False),
        ("text_block.html.jinja", True),
        ("text_block.css.jinja", False),
        ("macro/dimension.css.jinja", False),
    ],
)
def test__keep_templates(template_name, expected_output):
    output = DocumentGenerator._keep_template(template_name)
    assert output == expected_output


def test_set_styles_to_generate(default_document_generator):
    assert len(default_document_generator.styles_to_generate) == 1
    default_document_generator.set_styles_to_generate({"foo": ["bar", "bar"]})
    assert len(default_document_generator.styles_to_generate) == 2


@pytest.mark.parametrize(
    "styles, expected_output",
    [
        ({}, []),  # empty case
        (
            {"size": ["10px"], "color": []},
            [],
        ),  # empty value will result in null combinations
        ({"size": ["10px"], "color": ["red"]}, [{"size": "10px", "color": "red"}]),
        ({"size": ["5px", "10px"]}, [{"size": "5px"}, {"size": "10px"}]),
        (
            {"size": ["10px", "15px"], "color": ["blue"]},
            [{"size": "10px", "color": "blue"}, {"size": "15px", "color": "blue"}],
        ),
    ],
)
def test_document_generator_expand_style_combinations(styles, expected_output):
    output = DocumentGenerator.expand_style_combinations(styles)
    assert output == expected_output
