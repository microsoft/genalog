# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# ---------------------------------------------------------

"""Uses the python sdk to make operation on Azure Blob storage.
see: https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python
"""
import asyncio
import base64
import hashlib
import json
import os
import random

import aiofiles
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient
from azure.storage.blob.aio import BlobServiceClient as asyncBlobServiceClient
from tqdm import tqdm

from .common import DEFAULT_PROJECTIONS_CONTAINER_NAME

# maximum number of simultaneous requests
REQUEST_SEMAPHORE = asyncio.Semaphore(50)

# maximum number of simultaneous open files
FILE_SEMAPHORE = asyncio.Semaphore(500)

MAX_RETRIES = 5


class GrokBlobClient:
    """This class is a client that is used to upload and delete files from Azure Blob storage
    https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python
    """

    def __init__(
        self,
        datasource_container_name,
        blob_account_name,
        blob_key,
        projections_container_name=DEFAULT_PROJECTIONS_CONTAINER_NAME,
    ):
        """Creates the blob storage client given the key and storage account name

        Args:
            datasource_container_name (str): container name. This container does not need to be existing
            projections_container_name (str): projections container to store ocr projections.
                This container does not need to be existing
            blob_account_name (str): storage account name
            blob_key (str): storage account key
        """
        self.DATASOURCE_CONTAINER_NAME = datasource_container_name
        self.PROJECTIONS_CONTAINER_NAME = projections_container_name
        self.BLOB_NAME = blob_account_name
        self.BLOB_KEY = blob_key
        self.BLOB_CONNECTION_STRING = (
            f"DefaultEndpointsProtocol=https;AccountName={self.BLOB_NAME};"
            f"AccountKey={self.BLOB_KEY};EndpointSuffix=core.windows.net"
        )

    @staticmethod
    def create_from_env_var():
        """Created the blob client using values in the environment variables

        Returns:
            GrokBlobClient: the new blob client
        """
        DATASOURCE_CONTAINER_NAME = os.environ["DATASOURCE_CONTAINER_NAME"]
        BLOB_NAME = os.environ["BLOB_NAME"]
        BLOB_KEY = os.environ["BLOB_KEY"]
        PROJECTIONS_CONTAINER_NAME = os.environ.get(
            "PROJECTIONS_CONTAINER_NAME", DEFAULT_PROJECTIONS_CONTAINER_NAME
        )
        client = GrokBlobClient(
            DATASOURCE_CONTAINER_NAME,
            BLOB_NAME,
            BLOB_KEY,
            projections_container_name=PROJECTIONS_CONTAINER_NAME,
        )
        return client

    def upload_images_to_blob(
        self,
        src_folder_path,
        dest_folder_name=None,
        check_existing_cache=True,
        use_async=True,
    ):
        """Uploads images from the src_folder_path to blob storage at the destination folder.
        The destination folder is created if it doesn't exist. If a destination folder is not
        given a folder is created named by the md5 hash of the files.

        Args:
            src_folder_path (src): path to local folder that has images
            dest_folder_name (str, optional): destination folder name. Defaults to None.

        Returns:
            str: the destination folder name
        """
        self._create_container()
        blob_service_client = BlobServiceClient.from_connection_string(
            self.BLOB_CONNECTION_STRING
        )

        if dest_folder_name is None:
            dest_folder_name = self.get_folder_hash(src_folder_path)

        files_to_upload = []
        blob_names = []

        for folder, _, files in os.walk(src_folder_path):
            for f in files:
                upload_file_path = os.path.join(folder, f)
                subfolder = folder.replace(src_folder_path, "")
                # Replace any "double //" to avoid creating an empty folder in the blob
                blob_name = f"{dest_folder_name}/{subfolder}/{f}".replace("//", "/")
                files_to_upload.append(upload_file_path)
                blob_names.append(blob_name)

        def get_job_args(upload_file_path, blob_name):
            return (upload_file_path, blob_name)

        if check_existing_cache:
            existing_blobs, _ = self.list_blobs(dest_folder_name or "")
            existing_blobs = list(map(lambda blob: blob["name"], existing_blobs))
            file_blob_names = filter(
                lambda file_blob_names: not file_blob_names[1] in existing_blobs,
                zip(files_to_upload, blob_names),
            )
            job_args = [
                get_job_args(file_path, blob_name)
                for file_path, blob_name in file_blob_names
            ]
        else:
            job_args = [
                get_job_args(file_path, blob_name)
                for file_path, blob_name in zip(files_to_upload, blob_names)
            ]

        print("uploading ", len(job_args), "files")
        if not use_async:
            blob_service_client = BlobServiceClient.from_connection_string(
                self.BLOB_CONNECTION_STRING
            )
            blob_container_client = blob_service_client.get_container_client(
                self.DATASOURCE_CONTAINER_NAME
            )
            jobs = [(blob_container_client,) + x for x in job_args]
            for _ in tqdm(map(_upload_worker_sync, jobs), total=len(jobs)):
                pass
        else:
            async_blob_service_client = asyncBlobServiceClient.from_connection_string(
                self.BLOB_CONNECTION_STRING
            )

            async def async_upload():
                async with async_blob_service_client:
                    async_blob_container_client = (
                        async_blob_service_client.get_container_client(
                            self.DATASOURCE_CONTAINER_NAME
                        )
                    )
                    jobs = [(async_blob_container_client,) + x for x in job_args]
                    for f in tqdm(
                        asyncio.as_completed(map(_upload_worker_async, jobs)),
                        total=len(jobs),
                    ):
                        await f

            loop = asyncio.get_event_loop()
            if loop.is_running():
                result = loop.create_task(async_upload())
            else:
                result = loop.run_until_complete(async_upload())
            return dest_folder_name, result

        return dest_folder_name, None

    def get_folder_hash(self, folder_name):
        """Create an Md5 hash for all files in a folder.
        This hash can be used for blob folders.

        Args:
            folder_name (str): path to folder

        Returns:
            str: md5 hash of all filenames in the folder
        """
        hasher = hashlib.md5()
        for root, _, files in os.walk(folder_name):
            for f in files:
                fname = os.path.join(root, f)
                hasher.update(fname.encode())

        folder_hash = hasher.hexdigest()
        return folder_hash

    def delete_blobs_folder(self, folder_name):
        """Deletes all blobs in a folder

        Args:
            folder_name (str): folder to delete
        """

        blobs_list, blob_service_client = self.list_blobs(folder_name)
        for blob in blobs_list:
            blob_client = blob_service_client.get_blob_client(
                container=self.DATASOURCE_CONTAINER_NAME, blob=blob
            )
            blob_client.delete_blob()

    def list_blobs(self, folder_name):
        blob_service_client = BlobServiceClient.from_connection_string(
            self.BLOB_CONNECTION_STRING
        )
        container_client = blob_service_client.get_container_client(
            self.DATASOURCE_CONTAINER_NAME
        )
        return (
            container_client.list_blobs(name_starts_with=folder_name),
            blob_service_client,
        )

    def _create_container(self):
        """Creates the container named {self.DATASOURCE_CONTAINER_NAME} if it doesn't exist."""
        # Create the BlobServiceClient object which will be used to create a container client
        blob_service_client = BlobServiceClient.from_connection_string(
            self.BLOB_CONNECTION_STRING
        )

        try:
            blob_service_client.create_container(self.DATASOURCE_CONTAINER_NAME)
        except ResourceExistsError:
            print("container already exists:", self.DATASOURCE_CONTAINER_NAME)

        # create the container for storing ocr projections
        try:
            print(
                "creating projections storage container:",
                self.PROJECTIONS_CONTAINER_NAME,
            )
            blob_service_client.create_container(self.PROJECTIONS_CONTAINER_NAME)
        except ResourceExistsError:
            print("container already exists:", self.PROJECTIONS_CONTAINER_NAME)

    def get_ocr_json(self, remote_path, output_folder, use_async=True):
        blob_service_client = BlobServiceClient.from_connection_string(
            self.BLOB_CONNECTION_STRING
        )
        container_client = blob_service_client.get_container_client(
            self.DATASOURCE_CONTAINER_NAME
        )
        blobs_list = list(container_client.list_blobs(name_starts_with=remote_path))
        container_uri = f"https://{self.BLOB_NAME}.blob.core.windows.net/{self.DATASOURCE_CONTAINER_NAME}"

        if use_async:
            async_blob_service_client = asyncBlobServiceClient.from_connection_string(
                self.BLOB_CONNECTION_STRING
            )

            async def async_download():
                async with async_blob_service_client:
                    async_projection_container_client = (
                        async_blob_service_client.get_container_client(
                            self.PROJECTIONS_CONTAINER_NAME
                        )
                    )
                    jobs = list(
                        map(
                            lambda blob: (
                                blob,
                                async_projection_container_client,
                                container_uri,
                                output_folder,
                            ),
                            blobs_list,
                        )
                    )
                    for f in tqdm(
                        asyncio.as_completed(map(_download_worker_async, jobs)),
                        total=len(jobs),
                    ):
                        await f

            loop = asyncio.get_event_loop()
            if loop.is_running():
                result = loop.create_task(async_download())
            else:
                result = loop.run_until_complete(async_download())
            return result
        else:
            projection_container_client = blob_service_client.get_container_client(
                self.PROJECTIONS_CONTAINER_NAME
            )
            jobs = list(
                map(
                    lambda blob: (
                        blob,
                        projection_container_client,
                        container_uri,
                        output_folder,
                    ),
                    blobs_list,
                )
            )
            print("downloading", len(jobs), "files")
            for _ in tqdm(map(_download_worker_sync, jobs), total=len(jobs)):
                pass


def _get_projection_path(container_uri, blob):
    blob_uri = f"{container_uri}/{blob.name}"

    # projections use a base64 doc id as a key to store results in folders
    # see File Projection in https://docs.microsoft.com/en-us/azure/search/knowledge-store-projection-overview
    # hopefully this doesn't change soon otherwise we will have to do linear search over all docs to find
    # the projections we want
    projection_path = base64.b64encode(blob_uri.encode()).decode()
    projection_path = projection_path.replace("=", "") + str(projection_path.count("="))
    return projection_path


def _download_worker_sync(args):
    blob, projection_container_client, container_uri, output_folder = args
    projection_path = _get_projection_path(container_uri, blob)
    blob_client = projection_container_client.get_blob_client(
        blob=f"{projection_path}/document.json"
    )
    doc = json.loads(blob_client.download_blob().readall())
    file_name = os.path.basename(blob.name)
    base_name, ext = os.path.splitext(file_name)
    output_file = f"{output_folder}/{base_name}.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    text = doc["ocrLayoutText"]
    json.dump(text, open(output_file, "w", encoding="utf-8"), ensure_ascii=False)
    return output_file


async def _download_worker_async(args):
    blob, async_projection_container_client, container_uri, output_folder = args
    projection_path = _get_projection_path(container_uri, blob)
    async_blob_client = async_projection_container_client.get_blob_client(
        blob=f"{projection_path}/document.json"
    )
    file_name = os.path.basename(blob.name)
    base_name, ext = os.path.splitext(file_name)
    for retry in range(MAX_RETRIES):
        async with REQUEST_SEMAPHORE:
            try:
                blob_task = await async_blob_client.download_blob()
                doc = json.loads(await blob_task.readall())
                output_file = f"{output_folder}/{base_name}.json".replace("//", "/")
                async with FILE_SEMAPHORE:
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    text = doc["ocrLayoutText"]
                    json.dump(text, open(output_file, "w"))
                    return output_file
            except ResourceNotFoundError:
                print(f"Blob '{blob.name}'' doesn't exist in OCR projection. try rerunning OCR")
                return
            except Exception as e:
                print("error getting blob OCR projection", blob.name, e)

        # sleep for a bit then retry
        asyncio.sleep(2 * random.random())


async def _upload_worker_async(args):
    async_blob_container_client, upload_file_path, blob_name = args
    async with FILE_SEMAPHORE:
        async with aiofiles.open(upload_file_path, "rb") as f:
            data = await f.read()
            for retry in range(MAX_RETRIES):
                async with REQUEST_SEMAPHORE:
                    try:
                        await async_blob_container_client.upload_blob(
                            name=blob_name, max_concurrency=8, data=data
                        )
                        return blob_name
                    except ResourceExistsError:
                        print("blob already exists:", blob_name)
                        return
                    except Exception as e:
                        print(
                            f"blob upload error. retry count: {retry}/{MAX_RETRIES} :",
                            blob_name,
                            e,
                        )
                # sleep for a bit then retry
                asyncio.sleep(2 * random.random())
        return blob_name


def _upload_worker_sync(args):
    blob_container_client, upload_file_path, blob_name = args
    with open(upload_file_path, "rb") as data:
        try:
            blob_container_client.upload_blob(
                name=blob_name, max_concurrency=8, data=data
            )
        except ResourceExistsError:
            print("blob already exists:", blob_name)
        except Exception as e:
            print("blob upload error:", blob_name, e)
    return blob_name
