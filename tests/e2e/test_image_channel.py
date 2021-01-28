import cv2
import pytest

from genalog.generation.content import CompositeContent, ContentType
from genalog.generation.document import DocumentGenerator

TEMPLATE_PATH = "tests/e2e/templates"
TEST_OUT_FOLDER = "test_out/"
SAMPLE_TXT = "foo"
CONTENT = CompositeContent([SAMPLE_TXT], [ContentType.PARAGRAPH])


@pytest.fixture
def doc_generator():
    return DocumentGenerator(template_path=TEMPLATE_PATH)


@pytest.mark.io
def test_red_channel(doc_generator):
    generator = doc_generator.create_generator(CONTENT, ["solid_bg.html.jinja"])
    for doc in generator:
        doc.update_style(background_color="red")
        img_array = doc.render_array(resolution=100, channel="BGRA")
        # css "red" is rgb(255,0,0) or bgra(0,0,255,255)
        assert tuple(img_array[0][0]) == (0, 0, 255, 255)
        cv2.imwrite(TEST_OUT_FOLDER + "red.png", img_array)


@pytest.mark.io
def test_green_channel(doc_generator):
    generator = doc_generator.create_generator(CONTENT, ["solid_bg.html.jinja"])
    for doc in generator:
        doc.update_style(background_color="green")
        img_array = doc.render_array(resolution=100, channel="BGRA")
        # css "green" is rgb(0,128,0) or bgra(0,128,0,255)
        assert tuple(img_array[0][0]) == (0, 128, 0, 255)
        cv2.imwrite(TEST_OUT_FOLDER + "green.png", img_array)


@pytest.mark.io
def test_blue_channel(doc_generator):
    generator = doc_generator.create_generator(CONTENT, ["solid_bg.html.jinja"])
    for doc in generator:
        doc.update_style(background_color="blue")
        img_array = doc.render_array(resolution=100, channel="BGRA")
        # css "blue" is rgb(0,0,255) or bgra(255,0,0,255)
        assert tuple(img_array[0][0]) == (255, 0, 0, 255)
        cv2.imwrite(TEST_OUT_FOLDER + "blue.png", img_array)
