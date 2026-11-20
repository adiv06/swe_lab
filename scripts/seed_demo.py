"""Insert repeatable demo records into the configured MongoDB database."""

from app.auth import hash_password
from app.main import get_store


DEMO_PASSWORD = "password123"

DEMO_USERS = {
    "demo-user-001": {"name": "Ada Lovelace", "role": "analyst", "active": True},
    "demo-user-002": {"name": "Grace Hopper", "role": "engineer", "active": True},
    "demo-user-003": {"name": "Alan Turing", "role": "researcher", "active": False},
    "demo-user-004": {"name": "Katherine Johnson", "role": "analyst", "active": True},
    "demo-user-005": {"name": "Margaret Hamilton", "role": "engineer", "active": True},
}

DEMO_ACCOUNTS = {"ada": "Ada Lovelace", "grace": "Grace Hopper", "alan": "Alan Turing"}

def main() -> None:
    store = get_store()
    for key, value in DEMO_USERS.items():
        store.set(key, value)

    users = store.database["users"]
    for username, name in DEMO_ACCOUNTS.items():
        users.update_one(
            {"_id": username},
            {"$setOnInsert": {"name": name, "password_hash": hash_password(DEMO_PASSWORD)}},
            upsert=True,
        )

    store.units.list()

    print(
        f"Seeded {len(DEMO_USERS)} demo records, {len(DEMO_ACCOUNTS)} accounts "
        f"(password '{DEMO_PASSWORD}'), and two hardware units"
    )


if __name__ == "__main__":
    main()
