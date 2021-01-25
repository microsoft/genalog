from genalog.ocr.blob_client import GrokBlobClient
from genalog.ocr.grok import Grok
import pytest
import json
from dotenv import load_dotenv

load_dotenv("tests/ocr/.env")


class TestBlobClient:
    @pytest.mark.parametrize("use_async", [True, False])
    def test_upload_images(self, use_async):
        blob_client = GrokBlobClient.create_from_env_var()
        subfolder = "tests/ocr/data/img"
        subfolder.replace("/", "_")
        dst_folder, _ = blob_client.upload_images_to_blob(
            subfolder, use_async=use_async
        )
        uploaded_items, _ = blob_client.list_blobs(dst_folder)
        uploaded_items = sorted(list(uploaded_items), key=lambda x: x.name)
        assert uploaded_items[0].name == f"{dst_folder}/0.png"
        assert uploaded_items[1].name == f"{dst_folder}/1.png"
        assert uploaded_items[2].name == f"{dst_folder}/11.png"
        blob_client.delete_blobs_folder(dst_folder)
        assert (
            len(list(blob_client.list_blobs(dst_folder)[0])) == 0
        ), f"folder {dst_folder} was not deleted"

        dst_folder, _ = blob_client.upload_images_to_blob(
            subfolder, "test_images", use_async=use_async
        )
        assert dst_folder == "test_images"
        uploaded_items, _ = blob_client.list_blobs(dst_folder)
        uploaded_items = sorted(list(uploaded_items), key=lambda x: x.name)
        assert uploaded_items[0].name == f"{dst_folder}/0.png"
        assert uploaded_items[1].name == f"{dst_folder}/1.png"
        assert uploaded_items[2].name == f"{dst_folder}/11.png"
        blob_client.delete_blobs_folder(dst_folder)
        assert (
            len(list(blob_client.list_blobs(dst_folder)[0])) == 0
        ), f"folder {dst_folder} was not deleted"


class TestGROKe2e:
    @pytest.mark.parametrize("use_async", [False, True])
    def test_grok_e2e(self, tmpdir, use_async):
        grok = Grok.create_from_env_var()
        src_folder = "tests/ocr/data/img"
        grok.run_grok(
            src_folder,
            tmpdir,
            blob_dest_folder="testimages",
            use_async=use_async,
            cleanup=True,
        )
        assert json.load(open(f"{tmpdir}/0.json", "r"))[0]["text"]
        assert json.load(open(f"{tmpdir}/1.json", "r"))[0]["text"]
        assert json.load(open(f"{tmpdir}/11.json", "r"))[0]["text"]
