# Genalog Core

This is the core of the package and contains all core components necessary to generate new docs, degrade the documents and get text out of degraded images using OCR Capabilities of Azure.

## Image Generation

This directory contains the class implementations for image generation. The image generation leverages [Jinja templates](https://jinja.palletsprojects.com/en/2.11.x/templates/) for image generation. You can create a Jinja HTML template for any image layout and specify content variables to add content into images. This allows you the flexibility to be as declarative as possible.

[Here is our guide to Image Generation](generation/README.md)

## Image Degradation

This directory contains the class implementations for degrading your images such that they simulate real world Document degradations.

[Here is our guide to Image Degradation](degradation/README.md)

## Extract Text from Images

This directory contains the class implementations for Extract Text from Images using Azure OCR Process.

[Here is our guide to Extract Text from Images](ocr/README.md)

## Text Alignment

This directory contains the class implementations for text alignment. We expect that these capabilities will be required when you need to align text with its incorrect versions when you  degrade documents and then have errors in OCR. We use [Biopython's](https://biopython.org/) implementation of the Needleman-Wunsch algorithm for text alignment as the method `genalog.text.alignment.align()`. This algorithm is an exhaustive search for all possible candidates with dynamic programming. It produces weighted score for each candidate and returns those having the highest score. Note this is an algorithm with quadratic time and space complexity, and is not so efficient on aligning longer strings.

For more efficient alignment on longer documents, we also include an implementation of the RETAS method from the paper ["A Fast Alignment Scheme for Automatic OCR Evaluation of Books"](https://ieeexplore.ieee.org/document/6065412) in `genalog.text.anchor.align_w_anchor()`. We would recommend using this method for input longer than 200 characters.

[Here is our guide to Text Alignment](text/README.md)
