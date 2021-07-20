# Synthetic Document Generator

[![Build Status](https://dev.azure.com/genalog-dev/genalog/_apis/build/status/Nightly-Build?branchName=main)](https://dev.azure.com/genalog-dev/genalog/_build/latest?definitionId=4&branchName=main) ![Azure DevOps tests (compact)](https://img.shields.io/azure-devops/tests/genalog-dev/genalog/4?compact_message) ![Azure DevOps coverage (main)](https://img.shields.io/azure-devops/coverage/genalog-dev/genalog/4/main) ![Python Versions](https://img.shields.io/badge/py-3.6%20%7C%203.7%20%7C%203.8%20-blue) ![Supported OSs](https://img.shields.io/badge/platform-%20linux--64%20-red) ![MIT license](https://img.shields.io/badge/License-MIT-blue.svg) [![docs link](https://img.shields.io/badge/docs-jupyter--book-brightgreen)](https://microsoft.github.io/genalog/)

````{margin}
```sh
pip install genalog
```
````

`genalog` is an open source, cross-platform python package for **gen**erating document images with synthetic noise that mimics scanned an**alog** documents (thus the name `genalog`). You can also add various text degradations to these images. The purpose of this tool is to provide a fast and efficient way to generate synthetic documents from text data by leveraging layout from templates that you can create in simple HTML format.

`genalog` provides several document templates as a start. You can alter the document layout using standard CSS properties like `font-family`, `font-size`, `text-align`, etc. Here are some of the example generated documents:

````{tab} Multi-Column
```{figure} static/columns_Times_11px.png
:width: 60%
:name: two-columns-index
Document template with 2 columns 
```
````
````{tab} Letter-like
```{figure} static/letter_Times_11px.png
:width: 60%
:name: letter-like-index
Letter-like document template
```
````
````{tab} Simple Text Block
```{figure} static/text_block_Times_11px.png
:width: 60%
:name: text-block-index
Simple text block template
```
````

Once a document is generated, you can combine various image degradation effects and apply onto the synthetic documents. Here are some of the degradation effects:

````{tab} Bleed-through
```{figure} static/bleed_through.png
:name: bleed-through-index
:width: 80%
Mimics a document printed on two sides
```
````
````{tab} Blur
```{figure} static/blur.png
:name: blur-index
:width: 80%
Lowers image quality
```
````
````{tab} Salt/Pepper
```{figure} static/salt_pepper.png
:name: salt/pepper-index
:width: 50%
Mimics ink degradation
```
````
`````{tab} Close/Dilate
```{figure} static/close_dilate.png
:name: close-dilate-index
:width: 90%
Degrades printing quality
```
````{margin}
```{note}
For more details on this degradation, see [Morphilogical Operations](https://homepages.inf.ed.ac.uk/rbf/HIPR2/morops.htm)
```
````
`````
`````{tab} Open/Erode
```{figure} static/open_erode.png
:name: open-erode-index
:width: 90%
Ink overflows
```
````{margin}
```{note}
For more details on this degradation, see [Morphilogical Operations](https://homepages.inf.ed.ac.uk/rbf/HIPR2/morops.htm)
```
````
`````
````{tab} Combined Effects
```{figure} static/degrader.png
:width: 40%
:name: combined-effects-index
Combining various degradation effects: blur, salt, open, and bleed-through
```
````

In addition to the document generation and degradation, `genalog` also provide efficient implementation for [text alignment](text-alignment-page) between the source and noise text.

