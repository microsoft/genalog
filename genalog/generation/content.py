from enum import auto, Enum


class ContentType(Enum):
    PARAGRAPH = auto()
    TITLE = auto()
    IMAGE = auto()
    COMPOSITE = auto()


class Content:
    def __init__(self):
        self.iterable = True
        self._content = None

    def set_content_type(self, content_type):
        if type(content_type) != ContentType:
            raise TypeError(
                f"Invalid content type: {content_type}, valid types are {list(ContentType)}"
            )
        self.content_type = content_type

    def validate_content(self):
        NotImplementedError

    def __str__(self):
        return self._content.__str__()

    def __iter__(self):
        return self._content.__iter__()

    def __getitem__(self, key):
        return self._content.__getitem__(key)


class Paragraph(Content):
    def __init__(self, content):
        self.set_content_type(ContentType.PARAGRAPH)
        self.validate_content(content)
        self._content = content

    def validate_content(self, content):
        if not isinstance(content, str):
            raise TypeError(f"Expect a str, but got {type(content)}")


class Title(Content):
    def __init__(self, content):
        self.set_content_type(ContentType.TITLE)
        self.validate_content(content)
        self._content = content

    def validate_content(self, content):
        if not isinstance(content, str):
            raise TypeError(f"Expect a str, but got {type(content)}")


class CompositeContent(Content):
    def __init__(self, content_list, content_type_list):
        self.set_content_type(ContentType.COMPOSITE)
        self.validate_content(content_list)
        self.construct_content(content_list, content_type_list)
        self.iterable = True

    def validate_content(self, content_list):
        if not isinstance(content_list, list):
            raise TypeError(f"Expect a list of content, but got {type(content_list)}")

    def construct_content(self, content_list, content_type_list):
        self._content = []
        for content, content_type in zip(content_list, content_type_list):
            if content_type == ContentType.TITLE:
                self._content.append(Title(content))
            elif content_type == ContentType.PARAGRAPH:
                self._content.append(Paragraph(content))
            else:
                raise NotImplementedError(f"{content_type} is not currently supported")

    def insert_content(self, new_content, index):
        NotImplementedError

    def delete_content(self, index):
        NotImplementedError

    def __repr__(self):
        return "CompositeContent(" + self._content.__repr__() + ")"

    def __str__(self):
        """get a string transparent of the nested object types"""
        transparent_str = "["
        for content in self._content:
            transparent_str += '"' + content.__str__() + '", '
        return transparent_str + "]"
