import itertools
import os

import numpy as np
from jinja2 import Environment, select_autoescape
from jinja2 import FileSystemLoader, PackageLoader
from weasyprint import HTML

import cv2

try:
    import pypdfium2
except ImportError as e:
    pypdfium2 = None

try:
    # NOTE fitz is AGPL
    import fitz
except ImportError as e:
    fitz = None

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


def pdf_to_pixels(
        pdf_bytes,
        resolution=300,
        image_mode='RGB',
        single_page=True,
        combine_pages=False,
        target=None,
        encode=None,
        page_suffix='-{:d}',
):
    """

    Args:
        pdf_bytes: Input pdf bytes.
        resolution: DPI (dots-per-inch) for image rendering.
        image_mode: Image output color mode (RGB, GRAYSCALE, etc).
        single_page: Output only the first page of a multi-page doc.
        combine_pages: Combine all pages into one large image for multi-page doc.
        target: Target output filename, return image(s) as array if None.
        encode: Encode format as extension, overrides target ext or returns encoded bytes if target is None.
        page_suffix: Filename suffix for per page filename (to use with .format(page_index)
            when single_page=False and combine_pages=False.

    Returns:
        Image array (target=None, encode=None), encode image bytes (target=None, encode=ext), None (target=filename)
    """
    image_mode = image_mode.upper()
    grayscale = image_mode == 'L' or image_mode.startswith("GRAY")
    if encode is not None:
        assert encode.startswith('.'), '`encode` argument must be specified as a file extension with `.` prefix.'
    filename = None
    ext = None
    if target:
        filename, ext = os.path.splitext(target)
        assert ext or encode, "`encode` must be specified if target filename has no extension."
        if encode:
            ext = encode  # encode overrides original ext

    def _write_or_encode(_img, _index=None):
        if filename is not None:
            if _index is not None:
                write_filename = f'{filename}{page_suffix.format(_index)}{ext}'
            else:
                write_filename = f'{filename}{ext}'
            cv2.imwrite(write_filename, _img)
            return
        elif encode is not None:
            _img = cv2.imencode(encode, _img)[-1]
        return _img

    if fitz is not None:
        fitz_cs = fitz.csGRAY if grayscale else fitz.csRGB
        alpha = image_mode in {'RGBA', 'BGRA'}
        doc = fitz.Document(stream=pdf_bytes)
        img_array = []
        for page_index, page in enumerate(doc):
            pix = page.get_pixmap(dpi=resolution, colorspace=fitz_cs, alpha=alpha)
            img = np.frombuffer(pix.samples, np.uint8).reshape((pix.height, pix.width, -1))
            if image_mode == "BGRA":
                assert img.shape[-1] == 4
                img = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGRA)
            elif image_mode == "BGR":
                assert img.shape[-1] == 3
                img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

            if single_page:
                return _write_or_encode(img)

            if combine_pages:
                img_array.append(img)
            else:
                out = _write_or_encode(img, _index=page_index)
                if out is not None:
                    img_array.append(out)

        if combine_pages:
            img_array = np.vstack(img_array)
            return _write_or_encode(img_array)

        return img_array

    assert pypdfium2 is not None, 'One of pypdfium2 or fitz (pymupdf) is required to encode pdf as image.'
    doc = pypdfium2.PdfDocument(pdf_bytes)
    img_array = []
    for page_index, page in enumerate(doc):
        img = page.render(scale=resolution/72, grayscale=grayscale, prefer_bgrx=True).to_numpy()

        if image_mode == "RGBA":
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
        elif image_mode == "RGB":
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
        elif image_mode == "BGR":
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        if single_page:
            return _write_or_encode(img)

        if combine_pages:
            img_array.append(img)
        else:
            out = _write_or_encode(img, _index=page_index)
            if out is not None:
                img_array.append(out)

    if combine_pages:
        img_array = np.vstack(img_array)
        return _write_or_encode(img_array)

    return img_array


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
            zoom (int) : the zoom factor in PDF units per CSS units.

        Returns:
            The PDF as bytes if target is not provided or None, otherwise None (the PDF is written to target)
        """
        return self._document.write_pdf(target=target, zoom=zoom)

    def render_png(self, target=None, split_pages=False, resolution=300, channel="GRAYSCALE"):
        """ Render document to PNG bytes.

        Arguments:
            target: A filename, file-like object, or None.
            split_pages (bool) : true if save each document page as a separate file.
            resolution (int) : the output resolution in PNG pixels per CSS inch. At 300 dpi (the default),
                                PNG pixels match the CSS px unit.

        Returns:
            The image as bytes if target is not provided or None, otherwise None (the PDF is written to target)
        """
        filename, ext = os.path.splitext(target)
        if target is not None and split_pages:
            # get destination filename and extension
            for page_num, page in enumerate(self._document.pages):
                page_name = filename + f"_pg_{page_num}" + ext
                pdf_bytes = self._document.copy([page]).write_pdf(resolution=resolution)
                pdf_to_pixels(pdf_bytes, resolution=resolution, image_mode=channel, target=page_name, encode='.png')

            return
        else:
            pdf_bytes = self._document.write_pdf(resolution=resolution)
            # return image bytes string if no target is specified
            return pdf_to_pixels(pdf_bytes, resolution=resolution, image_mode=channel, target=target, encode='.png')

    def render_img(self, target=None, encode=None, split_pages=False, resolution=300, channel="GRAYSCALE"):
        """ Render document to and encoded image format.

        Arguments:
            target: A filename, file-like object, or None
            encode: Encode format specified as an extensions (eg: '.jpg', '.png', etc)
            split_pages (bool) : true if save each document page as a separate file.
            resolution (int) : the output resolution in PNG pixels per CSS inch. At 300 dpi (the default),
                                PNG pixels match the CSS px unit.

        Returns:
            The image as bytes if target is not provided or None, otherwise None (the PDF is written to target)
        """
        assert target or encode, 'One of target or encode must be specified'
        filename, ext = os.path.splitext(target)
        if target is not None and split_pages:
            # get destination filename and extension
            for page_num, page in enumerate(self._document.pages):
                page_name = filename + f"_pg_{page_num}" + ext
                pdf_bytes = self._document.copy([page]).write_pdf(resolution=resolution)
                pdf_to_pixels(pdf_bytes, resolution=resolution, image_mode=channel, target=page_name, encode=encode)

            return
        else:
            pdf_bytes = self._document.write_pdf(resolution=resolution)
            # return image bytes string if no target is specified
            return pdf_to_pixels(pdf_bytes, resolution=resolution, image_mode=channel, target=target, encode=encode)

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
        img_array = pdf_to_pixels(
            self._document.write_pdf(resolution=resolution),
            image_mode=channel,
            resolution=resolution,
        )
        return img_array

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
