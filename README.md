# Genalog - Synthetic Data Generator

[![Build Status](https://dev.azure.com/genalog-dev/genalog/_apis/build/status/Nightly-Build?branchName=main)](https://dev.azure.com/genalog-dev/genalog/_build/latest?definitionId=4&branchName=main) ![Azure DevOps tests (compact)](https://img.shields.io/azure-devops/tests/genalog-dev/genalog/4?compact_message) ![Azure DevOps coverage (main)](https://img.shields.io/azure-devops/coverage/genalog-dev/genalog/4/main) ![Python Versions](https://img.shields.io/badge/py-3.6%20%7C%203.7%20%7C%203.8%20-blue) ![Supported OSs](https://img.shields.io/badge/platform-%20linux--64%20-red) ![MIT license](https://img.shields.io/badge/License-MIT-blue.svg) [![docs link](https://img.shields.io/badge/docs-jupyter--book-brightgreen)](https://microsoft.github.io/genalog/)

Genalog is an open source, cross-platform python package for **gen**erating document images with synthetic noise that mimics scanned an**alog** documents (thus the name `genalog`). You can also add various text degradations to these images. The purpose of this tool is to provide a fast and efficient way to generate synthetic documents from text data by leveraging layout from templates that you create in simple HTML format.

Overview
-------------------------------------
Genalog has various capabilities: 

1. Flexible format Image Generation
1. Custom image degradation
1. Extract Text from Images using Cognitive Search Pipeline
1. Get OCR Performance Metrics 

The aim of this project is to provide a complete solution for generating synthetic images from any text data rich in natural language and to imitate most of OCR noises founded in scanned text documents. 

Please refer to our [Genalog documentation](https://microsoft.github.io/genalog) for more tutorials.

## Installation
See the [Genalog install guide](https://microsoft.github.io/genalog/installation.html) for more details.

To install the latest release:

`pip install genalog`

### Extra Installation Steps in MacOs and Windows
We have a dependency on [`Weasyprint`](https://weasyprint.readthedocs.io/en/stable/install.html), which in turn has non-python dependencies including `Pango`, `cairo` and `GDK-PixBuf` that need to be installed separately.

So far, `Pango`, `cairo` and `GDK-PixBuf` libraries are available in `Ubuntu-18.04` and later by default.

If you are running on Windows, MacOS, or other Linux distributions, please see [installation instructions from WeasyPrint](https://weasyprint.readthedocs.io/en/stable/install.html).

**NOTE**: If you encounter the errors like `no library called "libcairo-2" was found`, this is probably due to the three extra dependencies missing.

## Getting Started

The following is a summary of the common applications scenarios of Genalog. Please refer the [Jupyter notebook examples](https://github.com/microsoft/genalog/blob/master/example) that make use of the core code base of Genalog and repository utilities.

### TLDR
If you are interested in a full document generation and degration pipeline, please see the following notebook:

||Description|Indepth Jupyter Notebook Examples|
|-|-------------------------|--------|
|1|Analog Document Generation Pipeline|[Demo Notebook](https://github.com/microsoft/genalog/blob/master/example/generation_pipeline.ipynb)|[Here is guide to the core components](https://github.com/microsoft/genalog/blob/master/genalog/README.md)|


Else we have in-depth walkthroughs of each of the module in Genalog.

<p float="left">
  <img src="https://github.com/microsoft/genalog/blob/main/example/static/genalog_components.png?raw=true" width="900" />
</p>

||Steps|Indepth Jupyter Notebook Examples|Quick Start Guides|
|-|-------------------------|--------|--------|
|1|Create Template for Image Generation|[Demo Notebook](https://github.com/microsoft/genalog/blob/master/example/document_generation.ipynb)|[Here is our guide to Document Generation](https://github.com/microsoft/genalog/blob/master/genalog/generation/README.md)|
|2|Degrade Prebuilt Images|[Demo Notebook](https://github.com/microsoft/genalog/blob/master/example/document_degradation.ipynb)|[Here is our guide to Image Degradation](https://github.com/microsoft/genalog/blob/master/genalog/degradation/README.md)|
|3|Get Text From Images Using OCR|[Demo Notebook](https://github.com/microsoft/genalog/blob/master/example/ocr_extraction.ipynb)|[Here is our guide to Extracting Text](https://github.com/microsoft/genalog/blob/master/genalog/ocr/README.md)|
|4|Align Text Produced from OCR with Ground Truth Text|[Demo Notebook](https://github.com/microsoft/genalog/blob/master/example/text_alignment.ipynb)|[Here is our guide to Text Alignment](https://github.com/microsoft/genalog/blob/master/genalog/text/README.md)|
|5|NER Label Propagation from Ground Truth to OCR Tokens|[Demo Notebook](https://github.com/microsoft/genalog/blob/master/example/ocr_label_propagation.ipynb)|[Here is our guide to Label Propagation](https://github.com/microsoft/genalog/blob/master/genalog/text/README.md)|

We also provide notebooks for the complete end-to-end scenario of generating a synthetic dataset connecting all the components of genalog:

<p float="left">
  <img src="https://github.com/microsoft/genalog/blob/main/example/static/labeled_synthetic_pipeline.png?raw=true" width="900" />
</p>

||Scenario|Indepth Jupyter Notebook|
|-|-------------------------|--------|
|1|Synthetic Dataset Generation with LABELED NER Dataset|[Demo Notebook](https://github.com/microsoft/genalog/blob/master/example/dataset_generation.ipynb)|


### Other Requirements:

1. If you want to use the OCR Capabilities of Azure to Extract Text from the Images You'll require the following resources: 
    1. Azure Cognitive Search Service [Quickstart Guide Here](https://docs.microsoft.com/en-us/azure/search/search-create-service-portal)
    1. Azure Blob Storage [Quickstart Guide Here](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-blob-create-account-block-blob?tabs=azure-portal)
    
    See [Azure Docs](https://docs.microsoft.com/en-us/azure/search/search-what-is-azure-search) for more information on Azure Cognitive Search.


Package Release
-------------------
Please see [RELEASE.md](https://github.com/microsoft/genalog/blob/main/RELEASE.md) for more details on the release process.


Repo Structure
-------------------
    genalog
    ├────genalog
    │       ├─── generation                      # generate text images
    │       ├──── degradation                    # methods for image degradation
    │       ├──── ocr                            # running the Azure Search Pipeline
    │       └──── text                           # methods to Align OCR Output Text with 
    ├────devops                                  # CI/CD pipelines
    ├────docs                                    # containing online documentaions
    ├────examples                                # example Jupyter Notebooks for Various 
    ├────tests                                   # tests
    ├────tox.ini                                 # CI orchestration and configurations
    ├────README.md
    └────LICENSE

Trademark Notice
--------------------
This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow Microsoft’s Trademark & Brand Guidelines. Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or logos are subject to those third-party’s policies.

Microsoft Open Source Code of Conduct
-------------------------------------

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

Contribution Guidelines
-------------------------------------

This project welcomes contributions and suggestions. Most contributions require you to
agree to a Contributor License Agreement (CLA) declaring that you have the right to,
and actually do, grant us the rights to use your contribution. For details, visit
https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need
to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the
instructions provided by the bot. You will only need to do this once across all repositories using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/)
or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.


Collaborators
-------------------------------------
Genalog was originally developed by the [MAIDAP team at Microsoft Cambridge NERD](http://www.microsoftnewengland.com/nerd-ai/) in association with the Text Analytics Team in Redmond.
