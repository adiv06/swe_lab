import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pymongo.errors import ServerSelectionTimeoutError

from app.main import MongoStore, app, get_store


class FakeStore:
    def __init__(self):
        self.values = {}
        self.available = True

    def ping(self):
        if not self.available:
            raise ServerSelectionTimeoutError("unavailable")

    def get(self, key):
        if not self.available:
            raise ServerSelectionTimeoutError("unavailable")
        if key in self.values:
            return {"_id": key, "value": self.values[key]}
        return None

    def set(self, key, value):
        if not self.available:
            raise ServerSelectionTimeoutError("unavailable")
        self.values[key] = value


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.store = FakeStore()
        app.dependency_overrides[get_store] = lambda: self.store
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def test_put_get_replace_and_null(self):
        self.assertEqual(self.client.get("/items/example").status_code, 404)
        first = {"value": {"name": "Ada", "active": True}}
        self.assertEqual(self.client.put("/items/example", json=first).json(), first)
        self.assertEqual(self.client.get("/items/example").json(), first)
        self.assertEqual(
            self.client.put("/items/example", json={"value": None}).status_code,
            200,
        )
        self.assertEqual(self.client.get("/items/example").json(), {"value": None})

    def test_invalid_body_and_unavailable_database(self):
        self.assertEqual(self.client.put("/items/example", json={}).status_code, 422)
        self.store.available = False
        self.assertEqual(self.client.get("/health").status_code, 503)
        self.assertEqual(self.client.get("/items/example").status_code, 503)
        self.assertEqual(
            self.client.put("/items/example", json={"value": 1}).status_code,
            503,
        )


class MongoStoreTests(unittest.TestCase):
    def test_invalid_uri_returns_service_unavailable(self):
        get_store.cache_clear()
        app.dependency_overrides.clear()
        with patch.dict("os.environ", {"MONGODB_URI": "invalid-uri"}):
            with TestClient(app) as client:
                response = client.get("/health")
        self.assertEqual(response.status_code, 503)
        get_store.cache_clear()

    def test_set_uses_upsert_and_get_queries_key(self):
        class Collection:
            def replace_one(self, query, replacement, upsert):
                self.write = (query, replacement, upsert)

            def find_one(self, query, projection):
                self.read = (query, projection)
                return {"_id": "example", "value": None}

        collection = Collection()
        store = MongoStore.__new__(MongoStore)
        store.collection = collection
        store.set("example", None)
        self.assertEqual(
            collection.write,
            ({"_id": "example"}, {"_id": "example", "value": None}, True),
        )
        self.assertEqual(store.get("example")["value"], None)
        self.assertEqual(collection.read, ({"_id": "example"}, {"value": 1}))


if __name__ == "__main__":
    unittest.main()
