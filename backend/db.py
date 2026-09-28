import os

from pymongo import MongoClient

_client = None


def get_db():
    global _client
    if _client is None:
        uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
        _client = MongoClient(uri)
    return _client[os.environ.get("MONGO_DB_NAME", "hardware_allocator")]
