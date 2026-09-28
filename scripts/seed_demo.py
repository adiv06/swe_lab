"""Insert a few repeatable demo records into the configured MongoDB collection."""

from app.main import get_store


DEMO_USERS = {
    "demo-user-001": {"name": "Ada Lovelace", "role": "analyst", "active": True},
    "demo-user-002": {"name": "Grace Hopper", "role": "engineer", "active": True},
    "demo-user-003": {"name": "Alan Turing", "role": "researcher", "active": False},
    "demo-user-004": {"name": "Katherine Johnson", "role": "analyst", "active": True},
    "demo-user-005": {"name": "Margaret Hamilton", "role": "engineer", "active": True},
}


def main() -> None:
    store = get_store()
    for key, value in DEMO_USERS.items():
        store.set(key, value)
    print(f"Seeded {len(DEMO_USERS)} demo records")


if __name__ == "__main__":
    main()
