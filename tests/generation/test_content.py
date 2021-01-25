import pytest

from genalog.generation.content import CompositeContent, Content, ContentType
from genalog.generation.content import Paragraph, Title

CONTENT_LIST = ["foo", "bar"]
COMPOSITE_CONTENT_TYPE = [ContentType.TITLE, ContentType.PARAGRAPH]
TEXT = "foo bar"


@pytest.fixture
def content_base_class():
    return Content()


@pytest.fixture
def paragraph():
    return Paragraph(TEXT)


@pytest.fixture
def title():
    return Title(TEXT)


@pytest.fixture
def section():
    return CompositeContent(CONTENT_LIST, COMPOSITE_CONTENT_TYPE)


def test_content_set_content_type(content_base_class):
    with pytest.raises(TypeError):
        content_base_class.set_content_type("NOT VALID CONTENT TYPE")
    content_base_class.set_content_type(ContentType.PARAGRAPH)


def test_paragraph_init(paragraph):
    with pytest.raises(TypeError):
        Paragraph([])
    assert paragraph.content_type == ContentType.PARAGRAPH


def test_paragraph_print(paragraph):
    assert paragraph.__str__()


def test_paragraph_iterable_indexable(paragraph):
    for index, character in enumerate(paragraph):
        assert character == paragraph[index]


def test_title_init(title):
    with pytest.raises(TypeError):
        Title([])
    assert title.content_type == ContentType.TITLE


def test_title_iterable_indexable(title):
    for index, character in enumerate(title):
        assert character == title[index]


def test_composite_content_init(section):
    with pytest.raises(TypeError):
        CompositeContent((), [])
    assert section.content_type == ContentType.COMPOSITE


def test_composite_content_iterable(section):
    for index, content in enumerate(section):
        assert content.content_type == COMPOSITE_CONTENT_TYPE[index]


def test_composite_content_print(section):
    assert "foo" in section.__str__()
    assert "bar" in section.__str__()
