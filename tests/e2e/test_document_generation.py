import os

import pytest

from genalog.generation.content import CompositeContent, ContentType
from genalog.generation.document import DocumentGenerator

CONTENT = CompositeContent(
    ["foo", "bar"], [ContentType.PARAGRAPH, ContentType.PARAGRAPH]
)
UNSUPPORTED_CONTENT_FORMAT = ["foo bar"]
UNSUPPORTED_CONTENT_TYPE = CompositeContent(["foo"], [ContentType.TITLE])

CUSTOM_TEMPLATE_PATH = "tests/unit/generation/templates"
CUSTOM_TEMPLATE_NAME = "mock.html.jinja"
CUSTOM_STYLE_TEMPLATE_NAME = "font_family.html.jinja"
MULTI_PAGE_TEMPLATE_NAME = "multipage.html.jinja"
UNDEFINED_TEMPLATE_NAME = "not a valid template"

TEST_OUTPUT_DIR = "test_out"
FILE_DESTINATION = os.path.join(TEST_OUTPUT_DIR, "save.png")

CUSTOM_STYLE = {
    "font_family": ["Calibri", "Times"],
    "font_size": ["10px"],
    "text_align": ["right"],
    "hyphenate": [True, False],
}


def test_default_template_generation():
    doc_gen = DocumentGenerator()
    generator = doc_gen.create_generator(CONTENT, doc_gen.template_list)
    for doc in generator:
        html_str = doc.render_html()
        assert "Unsupported Content Type:" not in html_str
        assert "No content loaded" not in html_str


def test_default_template_generation_w_unsupported_content_format():
    doc_gen = DocumentGenerator()
    generator = doc_gen.create_generator(
        UNSUPPORTED_CONTENT_FORMAT, doc_gen.template_list
    )
    for doc in generator:
        html_str = doc.render_html()
        assert "No content loaded" in html_str


def test_default_template_generation_w_unsupported_content_type():
    doc_gen = DocumentGenerator()
    generator = doc_gen.create_generator(
        UNSUPPORTED_CONTENT_TYPE, ["text_block.html.jinja"]
    )
    for doc in generator:
        html_str = doc.render_html()
        assert "Unsupported Content Type: ContentType.TITLE" in html_str


def test_custom_template_generation():
    doc_gen = DocumentGenerator(template_path=CUSTOM_TEMPLATE_PATH)
    generator = doc_gen.create_generator(CONTENT, [CUSTOM_TEMPLATE_NAME])
    doc = next(generator)
    result = doc.render_html()
    assert result == str(CONTENT)


def test_undefined_template_generation():
    doc_gen = DocumentGenerator()
    assert UNDEFINED_TEMPLATE_NAME not in doc_gen.template_list
    generator = doc_gen.create_generator(CONTENT, [UNDEFINED_TEMPLATE_NAME])
    with pytest.raises(FileNotFoundError):
        next(generator)


def test_custom_style_template_generation():
    doc_gen = DocumentGenerator(template_path=CUSTOM_TEMPLATE_PATH)
    assert len(doc_gen.styles_to_generate) == 1
    doc_gen.set_styles_to_generate(CUSTOM_STYLE)
    generator = doc_gen.create_generator(CONTENT, [CUSTOM_STYLE_TEMPLATE_NAME])
    assert len(doc_gen.styles_to_generate) == 4
    for doc in generator:
        result = doc.render_html()
        assert doc.styles["font_family"] == result


def test_render_pdf_and_png():
    doc_gen = DocumentGenerator(template_path=CUSTOM_TEMPLATE_PATH)
    generator = doc_gen.create_generator(CONTENT, [CUSTOM_TEMPLATE_NAME])
    for doc in generator:
        pdf_bytes = doc.render_pdf()
        png_bytes = doc.render_png()
        assert pdf_bytes is not None
        assert png_bytes is not None


def test_save_document_as_png():
    if not os.path.exists(TEST_OUTPUT_DIR):
        os.mkdir(TEST_OUTPUT_DIR)
    doc_gen = DocumentGenerator(template_path=CUSTOM_TEMPLATE_PATH)
    generator = doc_gen.create_generator(CONTENT, [CUSTOM_TEMPLATE_NAME])
    for doc in generator:
        doc.render_png(target=FILE_DESTINATION, resolution=100)
    # Check if the document is saved in filepath
    assert os.path.exists(FILE_DESTINATION)


def test_save_document_as_separate_png():
    if not os.path.exists(TEST_OUTPUT_DIR):
        os.mkdir(TEST_OUTPUT_DIR)
    doc_gen = DocumentGenerator(template_path=CUSTOM_TEMPLATE_PATH)
    generator = doc_gen.create_generator(CONTENT, [MULTI_PAGE_TEMPLATE_NAME])

    document = next(generator)
    document.render_png(target=FILE_DESTINATION, split_pages=True, resolution=100)
    # Check if the document is saved as separated .png files
    for page_num in range(len(document._document.pages)):
        printed_doc_name = FILE_DESTINATION.replace(".png", f"_pg_{page_num}.png")
        assert os.path.exists(printed_doc_name)


def test_overwriting_style():
    new_font = "NewFontFamily"
    doc_gen = DocumentGenerator(template_path=CUSTOM_TEMPLATE_PATH)
    generator = doc_gen.create_generator(CONTENT, [CUSTOM_STYLE_TEMPLATE_NAME])
    doc = next(generator)
    # overwrite with new style during document rendering
    assert doc.styles["font_family"] != new_font
    doc.update_style(font_family=new_font)
    result = doc.render_html()
    assert new_font == result
