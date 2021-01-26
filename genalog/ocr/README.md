# GROK Client

Use the GROK client to make rest calls to the Azure Search Service to create and run the indexing pipeline. Blob client is used to transfer the images to blob and download the extracted OCR from blob.

Example usage:

1. Create an .env file with the environment variables that includes the names of you index, indexer, skillset, and datasource to create on the search service. Include keys to the blob that contains the documents you want to index, keys to the cognitive service and keys to you computer vision subscription and search service. In order to index more than 20 documents, you must have a computer services subscription. You can find the keys for the services in the Azure Portal. An example of the .env file content is given below:

    ```bash

    SEARCH_SERVICE_NAME = "ocr-ner-pipeline"
    SKILLSET_NAME = "ocrskillset"
    INDEX_NAME = "ocrindex"
    INDEXER_NAME = "ocrindexer"
    DATASOURCE_NAME = "syntheticimages"
    DATASOURCE_CONTAINER_NAME = "ocrimages"
    PROJECTIONS_CONTAINER_NAME = "ocrprojection"

    BLOB_NAME = "syntheticimages"
    BLOB_KEY = "<YOUR BLOB KEY>"
    SEARCH_SERVICE_KEY = "<YOUR SEARCH SERVICE KEY>"
    COGNITIVE_SERVICE_KEY = "<YOUR COGNITIVE SERVICE KEY>"
    ```

2. Source this .env file to load the variables then you can create and use the Grok class , REST client or blob client.

3. First, we need to upload our image files to azure blob. To do this, we use the blob client and call the `upload_images_to_blob` function. This function takes in the local and remote path and an optional parameter to specify whether to use asyncio asynchronous uploads [https://docs.python.org/3/library/asyncio.html]. Asynchronous uploads are faster, however, some setups of python may not support them. In such cases, sychronous uploads can be made using `use_async=False`.

    ```python
    from genalog.ocr.blob_client import GrokBlobClient
    from dotenv import load_dotenv
    load_dotenv(".env")
    destination_folder_name, upload_task = blob_client.upload_images_to_blob(local_path, remote_path, use_async=True)
    await upload_task
    ```

4. Once files are uploaded, use the rest client to create an indexing pipeline to extract the text from the images on blob. The results are stored as json blobs in a projection blob container where the names of these json blobs are the base64 encoded paths of the source blob images. The name of this projection container is specified in the env file. The `poll_indexer_till_complete` will block and continuosly poll the indexer until it completly processes all docs.

    ```python
    from genalog.ocr.rest_client import GrokRestClient
    from dotenv import load_dotenv
    load_dotenv(".env")

    grok_rest_client = GrokRestClient.
    grok_rest_client.create_indexing_pipeline()
    grok_rest_client.run_indexer()
    indexer_status = grok_rest_client.poll_indexer_till_complete()

    ```

5. Once the indexer completes, use the blob client to download the results from the projections blob.

    ```python
    from genalog.ocr.blob_client import GrokBlobClient
    from dotenv import load_dotenv
    load_dotenv(".env")
    
    output_folder = "./ocr"
    async_download_task = blob_client.get_ocr_json( remote_path, output_folder, use_async=True)
    await async_download_task
    ```

6. Alternatively, steps 3, 4 and 5 can be skipped by using the Grok class. This class is wrapper of the rest and blob clients. It upload images from src_folder_path to blob, runs the indexer, then donwloads the ocr projections to dest_folder_path


    ```python
    from genalog.ocr.grok import Grok
    from dotenv import load_dotenv
    load_dotenv("tests/unit/ocr/.env")

    grok = Grok.create_from_env_var()
    grok.run_grok(src_folder_path = "tests/unit/ocr/data/img", dest_folder_path = "tests/unit/ocr/data/json")
    ```
    
