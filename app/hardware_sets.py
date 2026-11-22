"""Hardware sets with a fixed capacity and a shared available count.

Each hardware set is one document in the ``hardware_sets`` collection::

    {"_id": "HWSet1", "name": "Hardware Set 1", "capacity": 100, "available": 100}

How many units each project holds is stored on the project document under
``hardware.<set id>`` (see ``app.projects``). Checkout and check-in update the
two documents with conditional, atomic ``$inc`` operations so two users can
never take more units than are available or return more than a project holds.
"""

from __future__ import annotations

from pymongo import ReturnDocument

from app.hardware import ConflictError, NotFoundError

DEFAULT_SETS = (
    ("HWSet1", "Hardware Set 1", 100),
    ("HWSet2", "Hardware Set 2", 100),
)


class HardwareSetStore:
    def __init__(self, database) -> None:
        self.sets = database["hardware_sets"]

    def ensure_defaults(self) -> None:
        """Create the two hardware sets on a fresh database (idempotent)."""
        for set_id, name, capacity in DEFAULT_SETS:
            if self.sets.find_one({"_id": set_id}) is None:
                self.sets.update_one(
                    {"_id": set_id},
                    {"$setOnInsert": {"name": name, "capacity": capacity, "available": capacity}},
                    upsert=True,
                )

    def list(self) -> list[dict]:
        self.ensure_defaults()
        return sorted(self.sets.find({}), key=lambda document: document["_id"])

    def get(self, set_id: str) -> dict | None:
        self.ensure_defaults()
        return self.sets.find_one({"_id": set_id})

    def take(self, set_id: str, quantity: int) -> dict:
        """Remove ``quantity`` units from the available pool, or raise."""
        self.ensure_defaults()
        updated = self.sets.find_one_and_update(
            {"_id": set_id, "available": {"$gte": quantity}},
            {"$inc": {"available": -quantity}},
            return_document=ReturnDocument.AFTER,
        )
        if updated is not None:
            return updated
        current = self.sets.find_one({"_id": set_id})
        if current is None:
            raise NotFoundError("Hardware set not found")
        raise ConflictError(
            f"Cannot check out {quantity} units of {current['name']}: "
            f"only {current['available']} available"
        )

    def give_back(self, set_id: str, quantity: int) -> dict | None:
        """Return ``quantity`` units to the available pool."""
        return self.sets.find_one_and_update(
            {"_id": set_id},
            {"$inc": {"available": quantity}},
            return_document=ReturnDocument.AFTER,
        )
