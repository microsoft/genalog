import itertools
import os

import cv2
import numpy as np
from cairocffi import FORMAT_ARGB32
from jinja2 import Environment, select_autoescape
from jinja2 import FileSystemLoader, PackageLoader
from weasyprint import HTML

DEFAULT_DOCUMENT_STYLE = {
    "language": "en_US",
    "font_family": "Segoe UI",
    "font_size": "12px",
    "text_align": "left",
    "hyphenate": False,
}

# Default styles combinations for document generator
DEFAULT_STYLE_COMBINATION = {
    "language": ["en_US"],
    "font_family": ["Segoe UI"],
    "font_size": ["12px"],
    "text_align": ["left"],
    "hyphenate": [False],
}


class Document(object):
    """ A composite object that represents a document """

    def __init__(self, content, template, **styles):
        """Initialize a Document object with source template and content

        Arguments:
            content (CompositeContent) : a iterable object whose elements
            template (Template) : a jinja2.Template object

        Other Parameters:
            styles (dict) : a kwargs dictionary (context) whose keys and values are
            the template variable and their respective values

        Example:
        ::

            {
                "font_family": "Calibri",
                "font_size": "10px",
                "hyphenate": True,
            }

        **NOTE** that this assumes that "font_family", "font_size", "hyphenate" are valid
        variables declared in the loaded template. There will be **NO SIDE-EFFECT**
        providing an variable undefined in the template.

        You can also provide these key-value pairs via Python keyword arguments:
        ::

            Document(content, template, font_family="Calibri, font_size="10px", hyphenate=True)
        """
        self.content = content
        self.template = template
        self.styles = DEFAULT_DOCUMENT_STYLE.copy()
        # This is a rendered document ready to be painted on a cairo surface
        self._document = None  # weasyprint.document.Document object
        self.compiled_html = None
        # Update the default styles and initialize self._document object
        self.update_style(**styles)

    def render_html(self):
        """Wrapper function for Jinjia2.Template.render(). Each template
        declare its template variables. This method assigns each variable to
        its respective value and compiles the template.

        This method will be used mostly for testing purpose.

        Returns:
            str : compiled Html template in unicode string
        """
        return self.template.render(content=self.content, **self.styles)

    def render_pdf(self, target=None, zoom=1):
        """Wrapper function for WeasyPrint.Document.write_pdf

        Arguments:
            target -- a filename, file-like object, or None
            split_pages (bool) : true if saving each document page as a separate file.
            zoom (int) : the zoom factor in PDF units per CSS units.

            split_pages (bool) : true if save each document page as a separate file.

        Returns:
            The PDF as bytes if target is not provided or None, otherwise None (the PDF is written to target)
        """
        return self._document.write_pdf(target=target, zoom=zoom)

    def render_png(self, target=None, split_pages=False, resolution=300):
        """Wrapper function for WeasyPrint.Document.write_png

        Arguments:
            target -- a filename, file-like object, or None
            split_pages (bool) : true if save each document page as a separate file.
            resolution (int) : the output resolution in PNG pixels per CSS inch. At 300 dpi (the default),
                                PNG pixels match the CSS px unit.

        Returns:
            The image as bytes if target is not provided or None, otherwise None (the PDF is written to target)
        """
        if target is not None and split_pages:
            # get destination filename and extension
            filename, ext = os.path.splitext(target)
            for page_num, page in enumerate(self._document.pages):
                page_name = filename + f"_pg_{page_num}" + ext
                self._document.copy([page]).write_png(
                    target=page_name, resolution=resolution
                )
            return None
        elif target is None:
            # return image bytes string if no target is specified
            png_bytes, png_width, png_height = self._document.write_png(
                target=target, resolution=resolution
            )
            return png_bytes
        else:
            return self._document.write_png(target=target, resolution=resolution)

    def render_array(self, resolution=300, channel="GRAYSCALE"):
        """Render document as a numpy.ndarray.

        Arguments:
            resolution (int, optional) : in units dpi. Defaults to 300.
            channel (str, optional): abbreviation for color channels. Available
                values are: ``"GRAYSCALE", "RGB", "RGBA", "BGRA", "BGR"``
                Defaults to ``"GRAYSCALE"``.

                **NOTE**: that ``"RGB"`` is 3-channel, ``"RGBA"`` is 4-channel and ``"GRAYSCALE"`` is single channel

        Returns:
            numpy.ndarray: representation of the document.
        """
        # Method below returns a cairocffi.ImageSurface object
        # https://cairocffi.readthedocs.io/en/latest/api.html#cairocffi.ImageSurface
        surface, width, height = self._document.write_image_surface(
            resolution=resolution
        )
        img_format = surface.get_format()

        # This is BGRA channel in little endian (reverse)
        if img_format != FORMAT_ARGB32:
            raise RuntimeError(
                f"Expect surface format to be 'cairocffi.FORMAT_ARGB32', but got {img_format}." +
                "Please check the underlining implementation of 'weasyprint.document.Document.write_image_surface()'"
            )

        img_buffer = surface.get_data()
        # Returns image array in "BGRA" channel
        img_array = np.ndarray(
            shape=(height, width, 4), dtype=np.uint8, buffer=img_buffer
        )
        if channel == "GRAYSCALE":
            return cv2.cvtColor(img_array, cv2.COLOR_BGRA2GRAY)
        elif channel == "RGBA":
            return cv2.cvtColor(img_array, cv2.COLOR_BGRA2RGBA)
        elif channel == "RGB":
            return cv2.cvtColor(img_array, cv2.COLOR_BGRA2RGB)
        elif channel == "BGRA":
            return np.copy(img_array)
        elif channel == "BGR":
            return cv2.cvtColor(img_array, cv2.COLOR_BGRA2BGR)
        else:
            valid_channels = ["GRAYSCALE", "RGB", "RGBA", "BGR", "BGRA"]
            raise ValueError(
                f"Invalid channel code {channel}. Valid values are: {valid_channels}."
            )

    def update_style(self, **style):
        """Update template variables that controls the document style and re-compile the document to reflect the style change.

        Other Parameters:
            style (dict) : a kwargs dictionary whose keys and values are
            the template variable and their respective values

        Example:
        ::

            {
                "font_family": "Calibri",
                "font_size": "10px",
                "hyphenate": True
            }

        """
        self.styles.update(style)
        # Recompile the html template and the document obj
        self.compiled_html = self.render_html()
        self._document = HTML(
            string=self.compiled_html
        ).render()  # weasyprinter.document.Document object


class DocumentGenerator:
    """ Document generator class """

    def __init__(self, template_path=None):
        """Initialize a DocumentGenerator class

        Arguments:
            template_path (str, optionsl) : filepath of custom templates. Defaults to None.

                **NOTE**: if not set, will use the default templates from the
                package "genalog.generation.templates".
        """
        if template_path:
            self.template_env = Environment(
                loader=FileSystemLoader(template_path),
                autoescape=select_autoescape(["html", "xml"]),
            )
            self.template_list = self.template_env.list_templates()
        else:
            # Loading built-in templates from the genalog package
            self.template_env = Environment(
                loader=PackageLoader("genalog.generation", "templates"),
                autoescape=select_autoescape(["html", "xml"]),
            )
            # Remove macros and css templates from rendering
            self.template_list = self.template_env.list_templates(
                filter_func=DocumentGenerator._keep_template
            )

        self.set_styles_to_generate(DEFAULT_STYLE_COMBINATION)

    @staticmethod
    def _keep_template(template_name):
        """Auxiliary function for Jinja2.Environment.list_templates().
        This function filters out non-html templates and base templates

        Arguments:
            template_name (str) : target of the template

        Returns:
            bool : True if keeping the template in the list. False otherwise.
        """
        TEMPLATES_TO_REMOVE = [".css", "base.html.jinja", "macro"]
        if any(name in template_name for name in TEMPLATES_TO_REMOVE):
            return False
        return True

    def set_styles_to_generate(self, style_combinations):
        """
        Set new styles to generate.

        Arguments:
            style_combination (dict) : a dictionary {str: list} enlisting the combinations
            of values to generate per style property. Defaults to None.

        Example:
        ::

            {
                "font_family": ["Calibri", "Times"],
                "font_size": ["10px", "12px"],
                "hyphenate": [True],
            }

        will produce documents with the following combinations of styles:
        ::

            ("Calibri", "10px", True)
            ("Times"  , "10px", True)
            ("Calibri", "12px", True)
            ("Times"  , "12px", True)

        **NOTE** that this assumes that ``font_family``, ``font_size``, ``hyphenate`` are valid
        variables declared in the loaded template. There will be NO side-effect providing
        an variable UNDEFINED in the template.

        If this parameter is not provided, generator will use default document
        styles: ``DEFAULT_STYLE_COMBINATION``.
        """
        self.styles_to_generate = DocumentGenerator.expand_style_combinations(
            style_combinations
        )

    def create_generator(self, content, templates_to_render):
        """Create a Document generator

        Arguments:
            content (list) : a list [str] of string to populate the template
            templates_to_render (list) : a list [str] or templates to render
                These templates must be located in the self.template_env

        Yields:
            Document : a Document Object
        """
        for template_name in templates_to_render:
            if template_name not in self.template_list:
                raise FileNotFoundError(
                    f"File '{template_name}' not found. Available templates are {self.template_list}"
                )
            template = self.template_env.get_template(template_name)
            for style in self.styles_to_generate:
                yield Document(content, template, **style)

    @staticmethod
    def expand_style_combinations(styles):
        """Expand the list of style values into all possible style combinations

        Arguments:
            styles (dict) : a dictionary {str: list} enlisting the combinations of values
            to generate per style property

        Return:
            list : a list of dictionaries

        Example:
        ::

            styles =
            {
                "font_family": ["Calibri", "Times"],
                "font_size": ["10px", "12px"],
                "hyphenate": [True],
            }

        This method will return:
        ::

            [
                {"font_family": "Calibri", "font_size": "10px", "hyphenate":True }
                {"font_family": "Times",   "font_size": "10px", "hyphenate":True }
                {"font_family": "Calibri", "font_size": "12px", "hyphenate":True }
                {"font_family": "Times",   "font_size": "12px", "hyphenate":True }
            ]

        The result dictionaries are intended to be used as a kwargs to initialize a
        ``Document`` object:
        ::

            Document(template, content, **{"font_family": "Calibri", "font_size": ...})

        """
        # return empty list if input is empty
        if not styles:
            return []
        # Python 2.x+ guarantees that the order in keys() and values() is preserved
        style_properties = (
            styles.keys()
        )  # ex) ["font_family", "font_size", "hyphenate"]
        property_values = (
            styles.values()
        )  # ex) [["Calibri", "Times"], ["10px", "12px"], [True]]

        # Generate all possible combinations:
        # [("Calibri", "10px", True), ("Calibri", "12px", True), ...]
        property_value_combinations = itertools.product(*property_values)

        # Map the property values back to the the property name
        # [
        #   {"font_family": "Calibri", "font_size": "10px", "hypenate": True },
        #   {"font_family": "Times",   "font_size": "10px", "hypenate": True },
        #   ....
        # ]
        style_combinations = []
        for combination in property_value_combinations:
            style_dict = {}
            for style_property, property_value in zip(style_properties, combination):
                style_dict[style_property] = property_value
            style_combinations.append(style_dict)

        return style_combinations
