from enum import Enum
from itertools import chain


class RequiredSecrets(Enum):
    BLOB_KEY = 'BLOB_KEY'
    SEARCH_SERVICE_KEY = 'SEARCH_SERVICE_KEY'
    COGNITIVE_SERVICE_KEY = 'COGNITIVE_SERVICE_KEY'


class RequiredConstants(Enum):
    COMPUTER_VISION_ENDPOINT = 'COMPUTER_VISION_ENDPOINT'
    SEARCH_SERVICE_NAME = 'SEARCH_SERVICE_NAME'
    SKILLSET_NAME = 'SKILLSET_NAME'
    INDEX_NAME = "INDEX_NAME"
    INDEXER_NAME = "INDEXER_NAME"
    DATASOURCE_NAME = "DATASOURCE_NAME"
    DATASOURCE_CONTAINER_NAME = "DATASOURCE_CONTAINER_NAME"
    BLOB_NAME = "BLOB_NAME"


RequiredEnvVar = Enum("RequiredEnvVar", [
    (i.name, i.value) for i in chain(RequiredSecrets, RequiredConstants)
])
