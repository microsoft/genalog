#%% 
from genalog.pipeline import AnalogDocumentGeneration
from genalog.degradation.degrader import ImageState

sample_text = "sample/generation/example.txt"

# Common CSS properties
STYLE_COMBINATIONS = {
    "font_family"   : ["Times"], # sans-serif, Times, monospace, etc
    "font_size"     : ["12px"],
    "text_align"    : ["justify"], # left, right, center, justify
    "language"      : ["en_US"],  # controls how words are hyphenated
    "hyphenate"     : [True],
}
# <columns|letter|text_block>.html.jinja
HTML_TEMPLATE = "columns.html.jinja" 
# Degration effects applied in sequence
DEGRADATIONS = [
    ("blur", {"radius": 5}),    # needs to be an odd number
    ("bleed_through", {
        "src": ImageState.CURRENT_STATE, "background": ImageState.ORIGINAL_STATE,
        "alpha": 0.8,
        "offset_y": 9, "offset_x": 12
    }),
    ("morphology", {"operation": "open", "kernel_shape":(5,5)}),
    ("pepper", {"amount": 0.05}),
    ("salt", {"amount": 0.2}),
]

doc_generation = AnalogDocumentGeneration(styles=STYLE_COMBINATIONS, degradations=DEGRADATIONS)
img_array = doc_generation.generate_img(sample_text, HTML_TEMPLATE, target_folder=None)

import cv2
from IPython.core.display import Image, display

_, encoded_image = cv2.imencode('.png', img_array)
display(Image(data=encoded_image, width=600))

