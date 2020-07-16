# Genalog - Synthetic Data Generator

![Build Status](https://dev.azure.com/msazure/Cognitive%20Services/_apis/build/status/Tools-Synthetic-Data-Generator?branchName=master)

Genalog is an open source, cross-platform python package allowing to generate synthetic document images with text data. Tool also allows you to add various text degradations to these images. The purpose of this tool is to provide a fast and efficient way to generate synthetic documents from text data by leveraging layout from templates that you create in simple HTML format. 

Overview
-------------------------------------
Genalog has various capabilities: 

1. Flexible format Image Generation
1. Custom image degradation
1. Extract Text from Images using Cognitive Search Pipeline
1. Get OCR Performance Metrics 

The aim of this project is to provide a complete solution for generating synthetic images from any text data rich in natural language and to imitate most of OCR noises founded in scanned text documents. 

## Getting Started
The following is a summary of the common applications scenarios of Genalog. Please refer the [Jupyter notebook examples](example) that make use of the core code base of Genalog and repository utilities.

||Steps|Indepth Jupyter Notebook Examples|Quick Start Guides|
|-|-------------------------|--------|--------|
|1|Create Template for Image Generation|[Demo Notebook](example/document_generation.ipynb)|[Here is our guide to Document Generation](genalog/generation/README.md)|
|2|Degrade Prebuilt Images|[Demo Notebook](example/document_degradation.ipynb)|[Here is our guide to Image Degradation](genalog/degradation/README.md)|
|3|Get Text From Images Using OCR|[Demo Notebook](example/ocr_extraction.ipynb)|[Here is our guide to Extracting Text](genalog/ocr/README.md)|
|4|Align Text Produced from OCR with Ground Truth Text|[Demo Notebook](example/text_alignment.ipynb)|[Here is our guide to Text Alignment](genalog/text/README.md)|
|5|NER Label Propagation from Ground Truth to OCR Tokens|[Demo Notebook](example/ocr_label_propagation.ipynb)|[Here is our guide to Label Propagation](genalog/text/README.md)|

We also provide notebooks for the complete end-to-end scenario of generating a synthetic dataset connecting all the components of genalog:

||Scenario|Indepth Jupyter Notebook|
|-|-------------------------|--------|
|1|Synthetic Dataset Generation with LABELED NER Dataset|[Demo Notebook](example/dataset_generation.ipynb)|
|2|Synthetic Dataset Batch Generation with Varying Degradation|[Demo Notebook](example/batch_dataset_generation.ipynb)|

Installation
-----------------------------

### Basic Requirements:

1. `>= Python3.6`
1. See [requirements.txt](requirements.txt)
1. If you want to use the OCR Capabilties of Azure to Extract Text from the Images You'll require the following resources: 
    1. Azure Cognitive Search Service [Quickstart Guide Here](https://docs.microsoft.com/en-us/azure/search/search-create-service-portal)
    1. Azure Blob Storage [Quickstart Guide Here](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-blob-create-account-block-blob?tabs=azure-portal)
    
    See [Azure Docs](https://docs.microsoft.com/en-us/azure/search/search-what-is-azure-search) for more information on Azure Cognitive Search.

### Installation from Source:

1. `git clone https://msazure.visualstudio.com/DefaultCollection/Cognitive%20Services/_git/Tools-Synthetic-Data-Generator`
1. `cd Tools-Synthetic-Data-Generator`
1. `python -m venv .env`
1. `source .env/bin/activate` or on Windows `.env/Scripts/activate.bat`
1. `pip install -r requirements.txt`
1. `pip install -e .`


Build and Test
----------------------
ToDo: Describe and show how to build your code and run the tests. 

Repo Structure
-------------------
    Tools-Synthetic-Data-Generator
    ├────genalog
    │       ├─── generation                      # generate text images
    │       ├──── degradation                    # methods for image degradation
    │       ├──── ocr                            # running the Azure Search Pipeline
    │       └──── text                           # methods to Align OCR Output Text with Input Text 
    ├────examples                                # Example Jupyter Notebooks for Various Synthetic Data Generation Scenarios
    ├────tests                                   # PyTest files
    ├────README.md                               # Main Readme file   
    └────LICENSE.txt                             # License file

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
