from genalog.degradation.degrader import Degrader
from genalog.generation.content import CompositeContent, ContentType
from genalog.generation.document import DocumentGenerator


TEST_OUTPUT_DIR = "test_out/"
SAMPLE_TXT = """Everton 's Duncan Ferguson , who scored twice against Manchester United on Wednesday ,
                 was picked on Thursday for the Scottish squad after a 20-month exile ."""
DEFAULT_TEMPLATE = "text_block.html.jinja"
DEGRADATION_EFFECTS = [
    ("blur", {"radius": 5}),
    ("bleed_through", {"alpha": 0.8}),
    (
        "morphology",
        {"operation": "open", "kernel_shape": (3, 3), "kernel_type": "plus"},
    ),
    ("morphology", {"operation": "close"}),
    ("morphology", {"operation": "dilate"}),
    ("morphology", {"operation": "erode"}),
]


def test_generation_and_degradation():
    # Initiate content
    content = CompositeContent([SAMPLE_TXT], [ContentType.PARAGRAPH])
    doc_gen = DocumentGenerator()
    assert DEFAULT_TEMPLATE in doc_gen.template_list
    # Initate template generator
    generator = doc_gen.create_generator(content, [DEFAULT_TEMPLATE])
    # Initiate degrader
    degrader = Degrader(DEGRADATION_EFFECTS)

    for doc in generator:
        # get the image in bytes in RGBA channels
        src = doc.render_array(resolution=100, channel="GRAYSCALE")
        # run each degradation effect
        degrader.apply_effects(src)
