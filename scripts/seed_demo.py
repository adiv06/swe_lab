"""Insert repeatable demo records into the configured MongoDB database.

Re-running the script resets the demo hardware pool and its allocations.
"""

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

DEMO_HARDWARE = [
    {"_id": "hwset-arduino", "name": "Arduino Kits", "capacity": 10, "max_per_user": 4},
    {"_id": "hwset-raspberry-pi", "name": "Raspberry Pi Boards", "capacity": 6, "max_per_user": 2},
    {"_id": "hwset-vr", "name": "VR Headsets", "capacity": 4, "max_per_user": 1},
    {"_id": "hwset-oscilloscope", "name": "Oscilloscopes", "capacity": 3, "max_per_user": 1},
]

# (user, hardware set, quantity) checked out after the pool is reset.
DEMO_ALLOCATIONS = [
    ("ada", "hwset-arduino", 3),
    ("grace", "hwset-arduino", 2),
    ("grace", "hwset-raspberry-pi", 2),
    ("alan", "hwset-vr", 1),
]


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

    hardware = store.hardware
    hardware_ids = [item["_id"] for item in DEMO_HARDWARE]
    hardware.allocations.delete_many({"hardware_id": {"$in": hardware_ids}})
    for item in DEMO_HARDWARE:
        hardware.sets.replace_one(
            {"_id": item["_id"]},
            {**item, "available": item["capacity"]},
            upsert=True,
        )
    for username, hardware_id, quantity in DEMO_ALLOCATIONS:
        hardware.checkout(hardware_id, username, quantity)

    print(
        f"Seeded {len(DEMO_USERS)} demo records, {len(DEMO_ACCOUNTS)} accounts "
        f"(password '{DEMO_PASSWORD}'), {len(DEMO_HARDWARE)} hardware sets and "
        f"{len(DEMO_ALLOCATIONS)} allocations"
    )


if __name__ == "__main__":
    main()
