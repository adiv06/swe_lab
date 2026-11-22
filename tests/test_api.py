import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pymongo.errors import ServerSelectionTimeoutError

from app.auth import AuthStore, verify_password
from app.hardware_sets import HardwareSetStore
from app.main import MongoStore, app, get_store
from app.projects import ProjectStore
from tests.fakes import FakeDatabase


class FakeStore:
    def __init__(self):
        self.values = {}
        self.available = True
        self.database = FakeDatabase()
        self.auth = AuthStore(self.database)
        self.projects = ProjectStore(self.database)
        self.hardware = HardwareSetStore(self.database)

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
        self.assertEqual(self.client.get("/api/status").status_code, 503)
        self.assertEqual(self.client.get("/items/example").status_code, 503)
        self.assertEqual(
            self.client.put("/items/example", json={"value": 1}).status_code,
            503,
        )

    def test_register_and_login_store_only_password_hash(self):
        account = {"name": "Ada", "username": "Ada_123", "password": "secret123"}
        registered = self.client.post("/api/auth/register", json=account)
        self.assertEqual(registered.status_code, 201)
        self.assertEqual(registered.json()["user"]["username"], "ada_123")
        stored = self.store.auth.users.documents["ada_123"]
        self.assertNotIn("password", stored)
        self.assertTrue(verify_password("secret123", stored["password_hash"]))
        self.assertEqual(self.client.post("/api/auth/register", json=account).status_code, 409)
        self.assertEqual(
            self.client.post(
                "/api/auth/login", json={"username": "ADA_123", "password": "wrong123"}
            ).status_code,
            401,
        )
        logged_in = self.client.post(
            "/api/auth/login", json={"username": "ADA_123", "password": "secret123"}
        )
        self.assertEqual(logged_in.status_code, 200)
        self.assertEqual(logged_in.json()["user"]["id"], "ada_123")
        self.assertEqual(self.client.get("/api/auth/me").json()["user"]["id"], "ada_123")
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 204)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_auth_requires_live_database(self):
        self.assertEqual(self.client.get("/api/status").json(), {"status": "ok"})
        self.store.available = False
        account = {"name": "Ada", "username": "ada_123", "password": "secret123"}
        self.assertEqual(self.client.post("/api/auth/register", json=account).status_code, 503)
        self.assertEqual(
            self.client.post(
                "/api/auth/login", json={"username": "ada_123", "password": "secret123"}
            ).status_code,
            503,
        )
        self.assertEqual(self.store.auth.users.documents, {})

    def test_empty_database_starts_with_two_hardware_sets(self):
        self.assertEqual(self.client.get("/api/hardware").status_code, 401)
        self.client.post("/api/auth/register", json={"name": "Ada", "username": "ada", "password": "secret123"})
        sets = self.client.get("/api/hardware").json()
        self.assertEqual(
            sets,
            [
                {"id": "HWSet1", "name": "Hardware Set 1", "capacity": 100, "available": 100},
                {"id": "HWSet2", "name": "Hardware Set 2", "capacity": 100, "available": 100},
            ],
        )


class ProjectApiTests(unittest.TestCase):
    """Walks through the checkpoint test cases with two users (ada and the TA, grace)."""

    def setUp(self):
        self.store = FakeStore()
        app.dependency_overrides[get_store] = lambda: self.store
        self.ada = TestClient(app)
        self.grace = TestClient(app)
        self.guest = TestClient(app)
        for client, username in ((self.ada, "ada"), (self.grace, "grace")):
            self.assertEqual(
                client.post(
                    "/api/auth/register",
                    json={"name": username, "username": username, "password": "secret123"},
                ).status_code,
                201,
            )

    def tearDown(self):
        self.ada.close()
        self.grace.close()
        self.guest.close()
        app.dependency_overrides.clear()

    def available(self, client):
        return {s["id"]: s["available"] for s in client.get("/api/hardware").json()}

    def checkout(self, client, project, set_id, quantity):
        return client.post(f"/api/projects/{project}/hardware/{set_id}/checkout", json={"quantity": quantity})

    def checkin(self, client, project, set_id, quantity):
        return client.post(f"/api/projects/{project}/hardware/{set_id}/checkin", json={"quantity": quantity})

    def test_create_project_requires_unique_id_and_login(self):
        self.assertEqual(self.guest.post("/api/projects", json={"id": "p100", "name": "X"}).status_code, 401)
        created = self.ada.post("/api/projects", json={"id": "p100", "name": "Robot", "description": "arm"})
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["memberIds"], ["ada"])
        self.assertEqual(created.json()["hardware"], {})
        duplicate = self.grace.post("/api/projects", json={"id": "p100", "name": "Other"})
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.json()["detail"], "Project ID already exists")
        self.assertEqual(self.ada.post("/api/projects", json={"id": "x", "name": "Too short"}).status_code, 422)
        self.assertEqual(self.ada.post("/api/projects/missing/join").status_code, 404)

    def test_full_checkpoint_walkthrough(self):
        # 4-6: create, duplicate id, join
        self.assertEqual(self.ada.post("/api/projects", json={"id": "p100", "name": "Robot"}).status_code, 201)
        self.assertEqual(self.grace.post("/api/projects", json={"id": "p200", "name": "TA"}).status_code, 201)
        self.assertEqual(self.ada.post("/api/projects/p200/join").status_code, 200)

        # 7-9: checkout both sets, availability drops
        out1 = self.checkout(self.ada, "p100", "HWSet1", 30)
        self.assertEqual(out1.status_code, 200)
        self.assertEqual(out1.json()["hardwareSet"]["available"], 70)
        self.assertEqual(out1.json()["project"]["hardware"], {"HWSet1": 30})
        self.assertEqual(self.checkout(self.ada, "p100", "HWSet2", 20).status_code, 200)
        self.assertEqual(self.available(self.ada), {"HWSet1": 70, "HWSet2": 80})

        # 10: more than available is refused and nothing changes
        too_many = self.checkout(self.ada, "p100", "HWSet1", 71)
        self.assertEqual(too_many.status_code, 409)
        self.assertIn("only 70 available", too_many.json()["detail"])
        self.assertEqual(self.checkout(self.ada, "p100", "HWSet1", 0).status_code, 422)
        self.assertEqual(self.checkout(self.ada, "p100", "HWSet9", 1).status_code, 404)
        self.assertEqual(self.available(self.ada), {"HWSet1": 70, "HWSet2": 80})

        # 11-12: check in increases availability; cannot return more than held
        self.assertEqual(self.checkin(self.ada, "p100", "HWSet1", 10).json()["hardwareSet"]["available"], 80)
        over = self.checkin(self.ada, "p100", "HWSet1", 21)
        self.assertEqual(over.status_code, 409)
        self.assertIn("only has 20 checked out", over.json()["detail"])

        # 13-14: logout, login, state persists
        self.assertEqual(self.ada.post("/api/auth/logout").status_code, 204)
        self.assertEqual(self.ada.get("/api/hardware").status_code, 401)
        self.assertEqual(self.ada.post("/api/auth/login", json={"username": "ada", "password": "secret123"}).status_code, 200)
        self.assertEqual(self.available(self.ada), {"HWSet1": 80, "HWSet2": 80})
        self.assertEqual(self.ada.get("/api/projects/p100").json()["hardware"], {"HWSet1": 20, "HWSet2": 20})

        # 16-17: TA cannot reuse the id; non-members are refused until they join
        self.assertEqual(self.grace.post("/api/projects", json={"id": "p100", "name": "Dup"}).status_code, 409)
        self.assertFalse(self.grace.get("/api/projects/p100").json()["isMember"])
        self.assertEqual(self.checkin(self.grace, "p100", "HWSet2", 5).status_code, 403)
        self.assertEqual(self.checkout(self.grace, "p100", "HWSet2", 5).status_code, 403)
        self.assertEqual(self.checkout(self.guest, "p100", "HWSet2", 5).status_code, 401)
        self.assertEqual(self.grace.post("/api/projects/p100/join").json()["memberIds"], ["ada", "grace"])

        # 18-19: TA checks in units the first user checked out
        self.assertEqual(self.checkin(self.grace, "p100", "HWSet2", 20).status_code, 200)
        self.assertEqual(self.available(self.grace), {"HWSet1": 80, "HWSet2": 100})

        # 20: TA checks out hardware
        self.assertEqual(self.checkout(self.grace, "p100", "HWSet2", 100).status_code, 200)
        self.assertEqual(self.available(self.ada)["HWSet2"], 0)
        self.assertEqual(self.checkout(self.ada, "p100", "HWSet2", 1).status_code, 409)

        inventory = self.ada.get("/api/inventory").json()["sets"]
        self.assertEqual(inventory[0]["holders"], [{"projectId": "p100", "projectName": "Robot", "quantity": 20}])
        self.assertEqual(inventory[1]["holders"], [{"projectId": "p100", "projectName": "Robot", "quantity": 100}])

    def test_creator_deletes_project_only_after_hardware_is_returned(self):
        self.ada.post("/api/projects", json={"id": "delete_me", "name": "Delete me"})
        self.grace.post("/api/projects/delete_me/join")
        self.checkout(self.ada, "delete_me", "HWSet1", 5)
        self.assertEqual(self.guest.delete("/api/projects/delete_me").status_code, 401)
        self.assertEqual(self.grace.delete("/api/projects/delete_me").status_code, 403)
        self.assertEqual(self.ada.delete("/api/projects/delete_me").status_code, 409)
        self.checkin(self.grace, "delete_me", "HWSet1", 5)
        self.assertEqual(self.ada.delete("/api/projects/delete_me").status_code, 204)
        self.assertEqual(self.ada.delete("/api/projects/delete_me").status_code, 404)
        self.assertEqual(self.available(self.ada)["HWSet1"], 100)


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
