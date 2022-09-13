(document-generation)=
# Create a document

`genalog` allows you to generate synthetic documents from **any** given text. 

To generate the synthetic documents, there are two important concepts to be familiar with:

1. `Template` - controls the layout of the document (i.e. font, langauge, position of the content, etc)
2. `Content` - items to be used to fill the template (i.e. text, images, tables, lists, etc)

We are using a HTML templating engine [(Jinja2)](https://jinja.palletsprojects.com/en/3.0.x/) to build our html templates, and a html-pdf converter [(Weasyprint)](https://weasyprint.readthedocs.io/en/latest/) to print the html as a pdf or an image.

We provide **three** standard templates for with document layouts:

````{tab} columns.html.jinja
```{figure} static/columns_Times_11px.png
:width: 30%
```
````
````{tab} letter.html.jinja
```{figure} static/letter_Times_11px.png
:width: 30%
```
````
````{tab} text_block.html.jinja
```{figure} static/text_block_Times_11px.png
:width: 30%
```
````

You can find the source code of these templates in path [`genalog/generation/templates`](https://github.com/microsoft/genalog/tree/main/genalog/generation/templates).

## Document Content

The goal is to be able to generate synthetic documents on ANY text input. Here we are loading in an sample file from our repo. You may use any text as well.

```python
import requests

sample_text_url = "https://raw.githubusercontent.com/microsoft/genalog/main/example/sample/generation/example.txt"

r = requests.get(sample_text_url, allow_redirects=True)
text = r.content.decode("ascii")
```
### Initialize `CompositeContent`
To properly initiate the content populating a document template, we need to create the `CompositeContent` class.

```python
from genalog.generation.content import CompositeContent, ContentType

# Initialize CompositeContent Object
paragraphs = text.split('\n\n') # split paragraphs by `\n\n`
content_types = [ContentType.PARAGRAPH] * len(paragraphs)
content = CompositeContent(paragraphs, content_types)
```
The `CompositeContent` is a list of pairs of bodies of text and their `ContentType`. Here we can declaring a list of multiple `ContentType.PARAGRAPH`s.

```{note}
`ContentType` is an enumeration dictating the supported content type (ex. ContentType.PARAGRAPH, ContentType.TITLE, ContentType.COMPOSITE). This enumeration controls the collection of CSS styles to be apply onto the associated content. If you change to `ContentType.TITLE`, for example, the paragraph will inherit the style of a title section (bolded text, enlarged font-size, etc).
```

### Populate Content Into a Template

Once we initialized a `CompositeContent` object, we can populate the content into any standard template, via `DocumentGenerator` class.

```python
from genalog.generation.document import DocumentGenerator
default_generator = DocumentGenerator()

print(f"Available default templates: {default_generator.template_list}")
print(f"Default styles to generate: {default_generator.styles_to_generate}")
```

The `DocumentGenerator` has default styles. The above code snippet will show the default configurations and the names of the 3 standard templates. You will use the information to select the template you want to generate. The three templates are `["columns.html.jinja", "letter.html.jinja", "text_block.html.jinja"]`

```python
# Select specific template, content and create the generator
doc_gen = default_generator.create_generator(content, ["columns.html.jinja", "letter.html.jinja", "text_block.html.jinja"]) 
# we will use the `CompositeContent` object initialized from above cell

# python generator 
for doc in doc_gen:
    template_name = doc.template.name.replace(".html.jinja", "")
    doc.render_png(target=f"example_{template_name}.png", resolution=300) #in dots per inch
```
You can also retrieve the raw image byte information without specifying the `target`

```python
from genalog.generation.document import DocumentGenerator
from IPython.core.display import Image, display

doc_gen = default_generator.create_generator(content, ['text_block.html.jinja']) 

for doc in doc_gen:
    image_byte = doc.render_png(resolution=100)
    display(Image(image_byte))
```

Alternative, you can also save the document as a PDF file.

```python
# Select specific template, content and create the generator
doc_gen = default_generator.create_generator(content, ['text_block.html.jinja']) 
# we will use the `CompositeContent` object initialized from above cell

# python generator 
for doc in doc_gen:
    doc.render_pdf(target="example_text_block.png")
```

### Changing Document Styles

You can alter the document styles including font family, font size, enabling hyphenation, and text alignment. These are mock style properties of their CSS counterparts. You can find standard CSS values replace the following properties.

```python
from genalog.generation.document import DocumentGenerator
from IPython.core.display import Image, display

# You can add as many options as possible. A new document will be generated per combination of the styles
new_style_combinations = {
    "hyphenate": [True],
    "font_size": ["11px", "12px"], # most CSS units are supported `px`, `cm`, `em`, etc...
    "font_family": ["Times"],
    "text_align": ["justify"]
}

default_generator = DocumentGenerator()
default_generator.set_styles_to_generate(new_style_combinations)
# Example the list of all style combination to generate
print(f"Styles to generate: {default_generator.styles_to_generate}")

doc_gen = default_generator.create_generator(titled_content, ["columns.html.jinja", "letter.html.jinja"])

for doc in doc_gen:
    print(doc.styles)
    print(doc.template.name)
    image_byte = doc.render_png(resolution=300)
    display(Image(image_byte))
```
