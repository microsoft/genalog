# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# ---------------------------------------------------------

import time

from .blob_client import GrokBlobClient
from .rest_client import GrokRestClient


class Grok:
    @staticmethod
    def create_from_env_var():
        """Initializes Grok based on keys in the environment variables.

        Returns:
            Grok: the Grok client
        """
        grok_rest_client = GrokRestClient.create_from_env_var()
        grok_blob_client = GrokBlobClient.create_from_env_var()
        return Grok(grok_rest_client, grok_blob_client)

    def __init__(
        self, grok_rest_client: GrokRestClient, grok_blob_client: GrokBlobClient
    ):
        self.grok_rest_client = grok_rest_client
        self.grok_blob_client = grok_blob_client

    def run_grok(
        self,
        src_folder_path,
        dest_folder_path,
        blob_dest_folder=None,
        cleanup=False,
        use_async=True,
    ):
        """Uploads images in the source folder to blob, sets up an indexing pipeline to run
        GROK OCR on this blob storage as a source, then dowloads the OCR output json to the destination
        folder. There resulting json files are of the same name as the original images except prefixed
        with the name of their folder on the blob storages and suffixed with the .json extension.

        Args:
            src_folder_path (str): Path to folder holding the images. This folder must only contain png or jpg files
            dest_folder_path (str): Path to folder where OCR json files will be placed
            blob_dest_folder (str, optional): Folder tag to use on the blob storage. If set to None, a hash is generated
                based on the names of files in the src folder. Defaults to None.
            cleanup (bool, optional): If set to True, the indexing pipeline is deleted, and the files uploaded to the blob are
                deleted from blob after running. Defaults to True.
            use_multiprocessing (boo, optional): If set to True, this will use multiprocessing to increase blob transfers speed.

        Returns:
            indexer_status json, blob folder name
        """
        print("uploading images to blob")
        blob_folder_name, _ = self.grok_blob_client.upload_images_to_blob(
            src_folder_path, dest_folder_name=blob_dest_folder, use_async=use_async
        )
        print(f"images upload under folder {blob_folder_name}")
        try:
            print("creating and running indexer")
            self.grok_rest_client.create_indexing_pipeline()
            time.sleep(2)

            indexer_status = self.grok_rest_client.get_indexer_status()
            if indexer_status["status"] == "error":
                raise RuntimeError(f"indexer error: {indexer_status}")

            # if not already running start the indexer
            print("indexer_status", indexer_status)
            if (
                indexer_status["lastResult"] is None
                or indexer_status["lastResult"]["status"] != "inProgress"
            ):
                self.grok_rest_client.run_indexer()

            time.sleep(1)
            print("\nrunning indexer")
            indexer_status = self.grok_rest_client.poll_indexer_till_complete()
            if indexer_status["lastResult"]["status"] == "success":
                time.sleep(30)
                print("fetching ocr json results.")
                self.grok_blob_client.get_ocr_json(
                    blob_folder_name, dest_folder_path, use_async=use_async
                )
                print(f"indexer status {indexer_status}")
                print(
                    f"finished running indexer. json files saved to {dest_folder_path}"
                )
            else:
                print("GROK failed", indexer_status["status"])
                raise RuntimeError("GROK failed", indexer_status["status"])
            return indexer_status, blob_folder_name
        finally:
            if cleanup:
                print("cleaning up indexer pipeline and blob store")
                self.cleanup(blob_folder_name)

    def cleanup(self, folder_name):
        """Deletes the indexing pipeline (index, indexer, datasource, skillset) from the search service.
        Deletes uploaded files from the blob

        Args:
            folder_name (str): blob folder name tag to remove
        """
        self.grok_blob_client.delete_blobs_folder(folder_name)
        self.grok_rest_client.delete_indexer_pipeline()
