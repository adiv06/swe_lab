import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError, ServerSelectionTimeoutError

from app.auth import AuthStore, verify_password
from app.hardware import HardwareStore
from app.projects import ProjectStore
from app.units import UnitStore
from app.main import MongoStore, app, get_store


class FakeStore:
    def __init__(self):
        self.values = {}
        self.available = True
        self.database = FakeDatabase()
        self.auth = AuthStore(self.database)
        self.hardware = HardwareStore(self.database)
        self.projects = ProjectStore(self.database)
        self.units = UnitStore(self.database)

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


def matches(document, query):
    for field, condition in query.items():
        value = document.get(field)
        if isinstance(condition, dict):
            for op, operand in condition.items():
                if value is None:
                    return False
                if op == "$gte" and not value >= operand:
                    return False
                if op == "$lte" and not value <= operand:
                    return False
                if op == "$in" and value not in operand:
                    return False
        elif value != condition:
            return False
    return True


class FakeCollection:
    """In-memory stand-in for the pymongo collection methods the app uses."""

    def __init__(self):
        self.documents = {}

    def create_index(self, *_args, **_kwargs):
        return None

    def insert_one(self, document):
        if document["_id"] in self.documents:
            raise DuplicateKeyError("duplicate key")
        self.documents[document["_id"]] = dict(document)

    def find_one(self, query, projection=None):
        return next(self.find(query), None)

    def find(self, query):
        return (dict(d) for d in list(self.documents.values()) if matches(d, query))

    def replace_one(self, query, replacement, upsert=False):
        self.documents[replacement["_id"]] = dict(replacement)

    def delete_one(self, query):
        found = self.find_one(query)
        if found:
            del self.documents[found["_id"]]

    def delete_many(self, query):
        for document in list(self.find(query)):
            del self.documents[document["_id"]]

    def _apply(self, document, update):
        for field, amount in update.get("$inc", {}).items():
            document[field] = document.get(field, 0) + amount
        document.update(update.get("$set", {}))
        for field in update.get("$unset", {}):
            document.pop(field, None)
        for field, value in update.get("$addToSet", {}).items():
            if value not in document.setdefault(field, []):
                document[field].append(value)

    def update_one(self, query, update, upsert=False):
        current = self.find_one(query)
        if current is None:
            if not upsert:
                return
            document = {k: v for k, v in query.items() if not isinstance(v, dict)}
            document.update(update.get("$setOnInsert", {}))
            self._apply(document, update)
            self.insert_one(document)
            return
        self._apply(self.documents[current["_id"]], update)

    def find_one_and_update(self, query, update, return_document=None):
        current = self.find_one(query)
        if current is None:
            return None
        self._apply(self.documents[current["_id"]], update)
        return dict(self.documents[current["_id"]])


class FakeDatabase:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        return self.collections.setdefault(name, FakeCollection())


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


class HardwareApiTests(unittest.TestCase):
    def setUp(self):
        self.store = FakeStore()
        app.dependency_overrides[get_store] = lambda: self.store
        self.client = TestClient(app)
        for username in ("ada", "grace"):
            self.client.post(
                "/api/auth/register",
                json={"name": username, "username": username, "password": "secret123"},
            )
        created = self.client.post(
            "/api/hardware", json={"name": "Arduino Kits", "capacity": 5, "max_per_user": 3}
        )
        self.assertEqual(created.status_code, 201)
        self.hw_id = created.json()["id"]

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def checkout(self, user, quantity):
        login = self.client.post(
            "/api/auth/login", json={"username": user, "password": "secret123"}
        )
        if login.status_code != 200:
            return login
        return self.client.post(
            f"/api/hardware/{self.hw_id}/checkout",
            json={"quantity": quantity},
        )

    def checkin(self, user, quantity):
        login = self.client.post(
            "/api/auth/login", json={"username": user, "password": "secret123"}
        )
        if login.status_code != 200:
            return login
        return self.client.post(
            f"/api/hardware/{self.hw_id}/checkin",
            json={"quantity": quantity},
        )

    def test_checkout_links_user_and_reduces_pool(self):
        response = self.checkout("ada", 2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["available"], 3)
        self.assertEqual(response.json()["held"], 2)
        allocations = self.client.get(f"/api/hardware/{self.hw_id}/allocations").json()
        self.assertEqual(allocations, [{"user_id": "ada", "quantity": 2}])
        listed = self.client.get("/api/hardware").json()
        self.assertEqual(listed[0]["held"], 2)

    def test_per_user_cap_and_pool_capacity(self):
        self.assertEqual(self.checkout("ada", 4).status_code, 409)
        self.assertEqual(self.checkout("ada", 3).status_code, 200)
        capped = self.checkout("ada", 1)
        self.assertEqual(capped.status_code, 409)
        self.assertIn("at most 3", capped.json()["detail"])
        short = self.checkout("grace", 3)
        self.assertEqual(short.status_code, 409)
        self.assertIn("Only 2", short.json()["detail"])
        # A rejected checkout must not leave a partial reservation behind.
        listed = self.client.get("/api/hardware").json()
        self.assertEqual(listed[0]["held"], 0)
        self.assertEqual(listed[0]["available"], 2)
        self.assertNotIn(
            f"{self.hw_id}:grace", self.store.database["allocations"].documents
        )

    def test_checkin_returns_units_to_pool(self):
        self.checkout("ada", 3)
        self.assertEqual(self.checkin("ada", 4).status_code, 409)
        self.assertEqual(self.checkin("grace", 1).status_code, 409)
        partial = self.checkin("ada", 1)
        self.assertEqual(partial.json()["available"], 3)
        self.assertEqual(partial.json()["held"], 2)
        done = self.checkin("ada", 2)
        self.assertEqual(done.json()["available"], 5)
        self.assertEqual(self.client.get(f"/api/hardware/{self.hw_id}/allocations").json(), [])

    def test_unknown_user_and_hardware(self):
        self.assertEqual(self.checkout("nobody", 1).status_code, 401)
        response = self.client.post(
            "/api/hardware/missing/checkout", json={"quantity": 1}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.checkout("ada", 0).status_code, 422)
        self.assertEqual(
            self.client.post(
                f"/api/hardware/{self.hw_id}/checkout",
                json={"user_id": "grace", "quantity": 1},
            ).status_code,
            422,
        )


class ProjectApiTests(unittest.TestCase):
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
        for unit_id, name in (("hw-unit-001", "Arduino Kit 1"), ("hw-unit-002", "Pi Kit 1")):
            self.store.database["HW Allocation"].insert_one(
                {"_id": unit_id, "name": name, "status": "available"}
            )

    def tearDown(self):
        self.ada.close()
        self.grace.close()
        self.guest.close()
        app.dependency_overrides.clear()

    def test_unit_request_links_user_project_and_allocation(self):
        self.assertEqual(self.guest.get("/api/projects").status_code, 401)
        self.assertEqual(len(self.ada.get("/api/units/available").json()), 2)
        response = self.ada.post(
            "/api/projects",
            json={"name": "Flight controls", "hardware_unit_id": "hw-unit-001"},
        )
        self.assertEqual(response.status_code, 201)
        project = response.json()
        self.assertEqual(project["memberIds"], ["ada"])
        self.assertEqual(project["hardwareUnitId"], "hw-unit-001")
        self.assertTrue(project["allocationId"])
        unit = self.store.database["HW Allocation"].documents["hw-unit-001"]
        self.assertEqual(unit["allocated_user_id"], "ada")
        self.assertEqual(unit["allocated_project_id"], project["id"])
        self.assertEqual(unit["allocation_id"], project["allocationId"])
        self.assertEqual(len(self.grace.get("/api/units/available").json()), 1)
        self.assertEqual(
            self.grace.post(
                "/api/projects",
                json={"name": "Competing", "hardware_unit_id": "hw-unit-001"},
            ).status_code,
            409,
        )
        self.assertEqual(len(self.store.database["projects"].documents), 1)
        self.assertFalse(self.grace.get(f"/api/projects/{project['id']}").json()["isMember"])
        joined = self.grace.post(f"/api/projects/{project['id']}/join")
        self.assertEqual(joined.status_code, 200)
        self.assertEqual(joined.json()["memberIds"], ["ada", "grace"])
        self.assertEqual(self.ada.post("/api/auth/logout").status_code, 204)
        self.assertEqual(self.ada.get("/api/projects").status_code, 401)

    def test_missing_unit_does_not_create_project(self):
        response = self.ada.post(
            "/api/projects", json={"name": "Missing", "hardware_unit_id": "unknown"}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.store.database["projects"].documents, {})


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
