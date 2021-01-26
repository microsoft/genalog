import logging
import os

import pytest
from dotenv import load_dotenv

from tests.required_env import RequiredEnvVar

ENV_FILEPATH = "tests/.env"


@pytest.fixture(scope="session")
def load_azure_resources():
    # Loading the non-secrets
    load_dotenv(ENV_FILEPATH)
    logging.info(f"Loading .env from {ENV_FILEPATH}")
    logging.debug("Printing environment vars: ")
    for env in RequiredEnvVar:
        logging.debug(f"\t{env.value}: {os.environ.get(env.value)}")
