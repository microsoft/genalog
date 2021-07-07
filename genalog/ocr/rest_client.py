# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# ---------------------------------------------------------

"""Uses the REST api to perform operations on the search service.
see: https://docs.microsoft.com/en-us/rest/api/searchservice/
"""
import json
import os
import pkgutil
import sys
import time
from itertools import cycle

import requests

from .common import DEFAULT_PROJECTIONS_CONTAINER_NAME

API_VERSION = "?api-version=2019-05-06-Preview"

# 15 min schedule
SCHEDULE_INTERVAL = "PT15M"


class GrokRestClient:
    """This is a REST client. It is a wrapper around the REST api for the Azure Search Service
    see: https://docs.microsoft.com/en-us/rest/api/searchservice/

    This class can be used to create an indexing pipeline and can be used to run and monitor
    ongoing indexers. The indexing pipeline can allow you to run batch OCR enrichment of documents.
    """

    def __init__(
        self,
        cognitive_service_key,
        search_service_key,
        search_service_name,
        skillset_name,
        index_name,
        indexer_name,
        datasource_name,
        datasource_container_name,
        blob_account_name,
        blob_key,
        projections_container_name=DEFAULT_PROJECTIONS_CONTAINER_NAME,
    ):
        """Creates the REST client

        Args:
            cognitive_service_key (str): key to cognitive services account
            search_service_key (str): key to the search service account
            search_service_name (str): name of the search service account
            skillset_name (str): name of the skillset
            index_name (str): name of the index
            indexer_name (str): the name of indexer
            datasource_name (str): the name to give the the attached blob storage source
            datasource_container_name (str): the container in the blob storage that host the files
            blob_account_name (str): blob storage account name that will host the documents to push though the pipeline
            blob_key (str): key to blob storage account
        """

        # check arguments
        self._checkArg("COGNITIVE_SERVICE_KEY", cognitive_service_key)
        self._checkArg("SEARCH_SERVICE_KEY", search_service_key)
        self._checkArg("SEARCH_SERVICE_NAME", search_service_name)
        self._checkArg("SKILLSET_NAME", skillset_name)
        self._checkArg("INDEX_NAME", index_name)
        self._checkArg("INDEXER_NAME", indexer_name)
        self._checkArg("DATASOURCE_NAME", datasource_name)
        self._checkArg("DATASOURCE_CONTAINER_NAME", datasource_container_name)
        self._checkArg("PROJECTIONS_CONTAINER_NAME", projections_container_name)
        self._checkArg("BLOB_NAME", blob_account_name)
        self._checkArg("BLOB_KEY", blob_key)

        self.COGNITIVE_SERVICE_KEY = cognitive_service_key
        self.SEARCH_SERVICE_KEY = search_service_key
        self.SEARCH_SERVICE_NAME = search_service_name
        self.SKILLSET_NAME = skillset_name
        self.INDEX_NAME = index_name
        self.INDEXER_NAME = indexer_name
        self.DATASOURCE_NAME = datasource_name
        self.DATASOURCE_CONTAINER_NAME = datasource_container_name
        self.PROJECTIONS_CONTAINER_NAME = projections_container_name
        self.BLOB_NAME = blob_account_name
        self.BLOB_KEY = blob_key

        self.API_VERSION = API_VERSION

        self.BLOB_CONNECTION_STRING = (
            f"DefaultEndpointsProtocol=https;AccountName={self.BLOB_NAME};"
            f"AccountKey={self.BLOB_KEY};EndpointSuffix=core.windows.net"
        )

    @staticmethod
    def create_from_env_var():
        COGNITIVE_SERVICE_KEY = os.environ["COGNITIVE_SERVICE_KEY"]
        SEARCH_SERVICE_KEY = os.environ["SEARCH_SERVICE_KEY"]
        SEARCH_SERVICE_NAME = os.environ["SEARCH_SERVICE_NAME"]
        SKILLSET_NAME = os.environ["SKILLSET_NAME"]
        INDEX_NAME = os.environ["INDEX_NAME"]
        INDEXER_NAME = os.environ["INDEXER_NAME"]
        DATASOURCE_NAME = os.environ["DATASOURCE_NAME"]
        DATASOURCE_CONTAINER_NAME = os.environ["DATASOURCE_CONTAINER_NAME"]
        BLOB_NAME = os.environ["BLOB_NAME"]
        BLOB_KEY = os.environ["BLOB_KEY"]
        PROJECTIONS_CONTAINER_NAME = os.environ.get(
            "PROJECTIONS_CONTAINER_NAME", DEFAULT_PROJECTIONS_CONTAINER_NAME
        )

        client = GrokRestClient(
            COGNITIVE_SERVICE_KEY,
            SEARCH_SERVICE_KEY,
            SEARCH_SERVICE_NAME,
            SKILLSET_NAME,
            INDEX_NAME,
            INDEXER_NAME,
            DATASOURCE_NAME,
            DATASOURCE_CONTAINER_NAME,
            BLOB_NAME,
            BLOB_KEY,
            projections_container_name=PROJECTIONS_CONTAINER_NAME,
        )

        return client

    def create_skillset(self):
        """Adds a skillset that performs OCR on images"""
        headers = {
            "Content-Type": "application/json",
            "api-key": self.SEARCH_SERVICE_KEY,
        }
        skillset_json = json.loads(
            pkgutil.get_data(__name__, "templates/skillset.json")
        )

        skillset_json["name"] = self.SKILLSET_NAME
        skillset_json["cognitiveServices"]["key"] = self.COGNITIVE_SERVICE_KEY

        knowledge_store_json = json.loads(
            pkgutil.get_data(__name__, "templates/knowledge_store.json")
        )
        knowledge_store_json["storageConnectionString"] = self.BLOB_CONNECTION_STRING
        knowledge_store_json["projections"][0]["objects"][0][
            "storageContainer"
        ] = self.PROJECTIONS_CONTAINER_NAME
        skillset_json["knowledgeStore"] = knowledge_store_json
        print(skillset_json)

        endpoint = f"https://{self.SEARCH_SERVICE_NAME}.search.windows.net/skillsets/{self.SKILLSET_NAME}"

        r = requests.put(
            endpoint + self.API_VERSION, json.dumps(skillset_json), headers=headers
        )
        print("skillset response", r.text)
        r.raise_for_status()
        print("added skillset", self.SKILLSET_NAME, r)

    def create_datasource(self):
        """Attaches the blob data store to the search service as a source for image documents"""
        headers = {
            "Content-Type": "application/json",
            "api-key": self.SEARCH_SERVICE_KEY,
        }

        datasource_json = json.loads(
            pkgutil.get_data(__name__, "templates/datasource.json")
        )
        datasource_json["name"] = self.DATASOURCE_NAME
        datasource_json["credentials"]["connectionString"] = self.BLOB_CONNECTION_STRING
        datasource_json["type"] = "azureblob"
        datasource_json["container"]["name"] = self.DATASOURCE_CONTAINER_NAME

        endpoint = f"https://{self.SEARCH_SERVICE_NAME}.search.windows.net/datasources/{self.DATASOURCE_NAME}"

        r = requests.put(
            endpoint + self.API_VERSION, json.dumps(datasource_json), headers=headers
        )
        print("datasource response", r.text)
        r.raise_for_status()
        print("added datasource", self.DATASOURCE_NAME, r)

    def create_index(self):
        """Create an index with the layoutText column to store OCR output from the enrichment"""
        headers = {
            "Content-Type": "application/json",
            "api-key": self.SEARCH_SERVICE_KEY,
        }
        index_json = json.loads(pkgutil.get_data(__name__, "templates/index.json"))
        index_json["name"] = self.INDEX_NAME

        endpoint = f"https://{self.SEARCH_SERVICE_NAME}.search.windows.net/indexes/{self.INDEX_NAME}"

        r = requests.put(
            endpoint + self.API_VERSION, json.dumps(index_json), headers=headers
        )
        print("index response", r.text)
        r.raise_for_status()
        print("created index", self.INDEX_NAME, r)

    def create_indexer(self, extension_to_exclude=".txt, .json"):
        """Creates an indexer that runs the enrichment skillset of documents from the datatsource.
        The enriched results are pushed to the index.
        """
        headers = {
            "Content-Type": "application/json",
            "api-key": self.SEARCH_SERVICE_KEY,
        }

        indexer_json = json.loads(pkgutil.get_data(__name__, "templates/indexer.json"))

        indexer_json["name"] = self.INDEXER_NAME
        indexer_json["skillsetName"] = self.SKILLSET_NAME
        indexer_json["targetIndexName"] = self.INDEX_NAME
        indexer_json["dataSourceName"] = self.DATASOURCE_NAME
        indexer_json["schedule"] = {"interval": SCHEDULE_INTERVAL}
        indexer_json["parameters"]["configuration"][
            "excludedFileNameExtensions"
        ] = extension_to_exclude

        endpoint = f"https://{self.SEARCH_SERVICE_NAME}.search.windows.net/indexers/{self.INDEXER_NAME}"

        r = requests.put(
            endpoint + self.API_VERSION, json.dumps(indexer_json), headers=headers
        )
        print("indexer response", r.text)
        r.raise_for_status()
        print("created indexer", self.INDEXER_NAME, r)

    def create_indexing_pipeline(self):
        """Using REST calls, creates an index, indexer and skillset on the Cognitive service.
        The templates for json are in the templates folder.
        """
        self.create_skillset()
        self.create_index()
        self.create_datasource()
        self.create_indexer()

    def delete_indexer_pipeline(self):
        """Deletes all indexers, indexes, skillsets and datasources that had been previously
        created
        """
        headers = {
            "Content-Type": "application/json",
            "api-key": self.SEARCH_SERVICE_KEY,
        }
        endpoints = [
            f"https://{self.SEARCH_SERVICE_NAME}.search.windows.net/indexers/{self.INDEXER_NAME}",
            f"https://{self.SEARCH_SERVICE_NAME}.search.windows.net/indexes/{self.INDEX_NAME}",
            f"https://{self.SEARCH_SERVICE_NAME}.search.windows.net/datasources/{self.DATASOURCE_NAME}",
            f"https://{self.SEARCH_SERVICE_NAME}.search.windows.net/skillsets/{self.SKILLSET_NAME}",
        ]

        for endpoint in endpoints:
            r = requests.delete(endpoint + self.API_VERSION, headers=headers)
            print("delete response", r.text)
            r.raise_for_status()

    def run_indexer(self):
        headers = {
            "Content-Type": "application/json",
            "api-key": self.SEARCH_SERVICE_KEY,
        }

        endpoint = f"https://{self.SEARCH_SERVICE_NAME}.search.windows.net/indexers/{self.INDEXER_NAME}/run"
        r = requests.post(endpoint + self.API_VERSION, headers=headers)
        print("run indexer response", r.text)
        r.raise_for_status()
        print("running indexer", self.INDEXER_NAME, r)

    def poll_indexer_till_complete(self):
        progress = cycle("|\b/\b-\b\\\b")
        i = 0
        while True:
            # attempt a call every 100 steps
            if i % 100 == 0:
                request_json = self.get_indexer_status()
                if request_json["status"] == "error":
                    raise RuntimeError("Indexer failed")
                if (
                    request_json["lastResult"]
                    and not request_json["lastResult"]["status"] == "inProgress"
                ):
                    print(request_json["lastResult"]["status"], self.INDEXER_NAME)
                    return request_json

            sys.stdout.write(next(progress))
            sys.stdout.flush()
            time.sleep(0.05)
            i = (1 + i) % 1000  # to avoid overflow

    def get_indexer_status(self):
        headers = {
            "Content-Type": "application/json",
            "api-key": self.SEARCH_SERVICE_KEY,
        }
        endpoint = f"https://{self.SEARCH_SERVICE_NAME}.search.windows.net/indexers/{self.INDEXER_NAME}/status"
        response = requests.get(endpoint + self.API_VERSION, headers=headers)
        response.raise_for_status()
        return response.json()

    def _checkArg(self, name, value):
        if not (value):
            raise ValueError(f"argument {name} is not set")
