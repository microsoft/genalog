import json
import os

import pytest
import requests

from genalog.ocr.rest_client import GrokRestClient


@pytest.fixture(scope="module", autouse=True)
def set_azure_dummy_secrets(load_azure_resources):
    os.environ['BLOB_KEY'] = "<YOUR BLOB KEY>"
    os.environ['SEARCH_SERVICE_KEY'] = "<YOUR SEARCH SERVICE KEY>"
    os.environ['COGNITIVE_SERVICE_KEY'] = "<YOUR COGNITIVE SERVICE KEY>"


@pytest.fixture(autouse=True)
def setup_monkeypatch(monkeypatch):
    def mock_http(*args, **kwargs):
        return MockedResponse(args, kwargs)

    # apply the monkeypatch for requests.get to mock_get
    monkeypatch.setattr(requests, "put", mock_http)
    monkeypatch.setattr(requests, "post", mock_http)
    monkeypatch.setattr(requests, "get", mock_http)
    monkeypatch.setattr(requests, "delete", mock_http)


class MockedResponse:
    def __init__(self, args, kwargs):
        self.url = args[0]
        self.text = "response"
        # self.data = args[1]
        self.headers = kwargs["headers"]

    def json(self):
        if "search.windows.net/skillsets/" in self.url:
            return {}

        if "search.windows.net/indexers/" in self.url:
            if "status" in self.url:
                return {"lastResult": {"status": "success"}, "status": "finished"}
            return {}

        if "search.windows.net/indexes/" in self.url:
            if "docs/search" in self.url:
                return {
                    "value": [
                        {
                            "metadata_storage_name": "521c38122f783673598856cd81d91c21_0.png",
                            "layoutText": json.load(
                                open(
                                    "tests/unit/ocr/data/json/521c38122f783673598856cd81d91c21_0.png.json",
                                    "r",
                                )
                            ),
                        },
                        {
                            "metadata_storage_name": "521c38122f783673598856cd81d91c21_1.png",
                            "layoutText": json.load(
                                open(
                                    "tests/unit/ocr/data/json/521c38122f783673598856cd81d91c21_1.png.json",
                                    "r",
                                )
                            ),
                        },
                        {
                            "metadata_storage_name": "521c38122f783673598856cd81d91c21_11.png",
                            "layoutText": json.load(
                                open(
                                    "tests/unit/ocr/data/json/521c38122f783673598856cd81d91c21_11.png.json",
                                    "r",
                                )
                            ),
                        },
                    ]
                }
            return json.dumps({})
        if "search.windows.net/datasources/" in self.url:
            return {}

        raise ValueError(f"{self.url} not valid")

    def raise_for_status(self):
        pass


class TestGROK:
    def test_creating_indexing_pipeline(self):
        grok_rest_client = GrokRestClient.create_from_env_var()
        grok_rest_client.create_indexing_pipeline()
        grok_rest_client.delete_indexer_pipeline()

    def test_running_indexer(self):
        grok_rest_client = GrokRestClient.create_from_env_var()
        grok_rest_client.create_indexing_pipeline()

        indexer_status = grok_rest_client.get_indexer_status()
        if indexer_status["status"] == "error":
            raise RuntimeError(f"indexer error: {indexer_status}")

        # if not already running start the indexer
        if indexer_status["lastResult"]["status"] != "inProgress":
            grok_rest_client.run_indexer()

        grok_rest_client.run_indexer()
        indexer_status = grok_rest_client.poll_indexer_till_complete()
        assert indexer_status["lastResult"]["status"] == "success"
        grok_rest_client.delete_indexer_pipeline()
