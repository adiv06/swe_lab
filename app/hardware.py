"""MongoDB-backed hardware pool: users check units out and return them.

Each hardware set stores its total ``capacity``, the units still ``available``
in the pool, and ``max_per_user``, the most units one user may hold at once.
Each allocation document links one user ID to one hardware set and the number
of units that user holds. Updates are conditional so concurrent requests cannot
take the pool below zero or a user above the per-user cap.
"""

import uuid

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError


class HardwareError(Exception):
    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(HardwareError):
    status_code = 404


class ConflictError(HardwareError):
    status_code = 409


def allocation_id(hardware_id: str, user_id: str) -> str:
    return f"{hardware_id}:{user_id}"


class HardwareStore:
    def __init__(self, database) -> None:
        self.sets = database["hardware_sets"]
        self.allocations = database["allocations"]
        self.users = database["users"]

    def _get_set(self, hardware_id: str) -> dict:
        hardware = self.sets.find_one({"_id": hardware_id})
        if hardware is None:
            raise NotFoundError("Hardware set not found")
        return hardware

    def _require_user(self, user_id: str) -> None:
        if self.users.find_one({"_id": user_id}) is None:
            raise NotFoundError("User not found")

    def held_by(self, user_id: str) -> dict[str, int]:
        return {
            a["hardware_id"]: a["quantity"]
            for a in self.allocations.find({"user_id": user_id})
            if a["quantity"] > 0
        }

    def list_sets(self) -> list[dict]:
        return list(self.sets.find({}))

    def create_set(self, name: str, capacity: int, max_per_user: int) -> dict:
        hardware = {
            "_id": uuid.uuid4().hex,
            "name": name,
            "capacity": capacity,
            "available": capacity,
            "max_per_user": max_per_user,
        }
        self.sets.insert_one(hardware)
        return hardware

    def allocations_for_set(self, hardware_id: str) -> list[dict]:
        self._get_set(hardware_id)
        return [
            a
            for a in self.allocations.find({"hardware_id": hardware_id})
            if a["quantity"] > 0
        ]

    def checkout(self, hardware_id: str, user_id: str, quantity: int) -> dict:
        hardware = self._get_set(hardware_id)
        self._require_user(user_id)
        cap = hardware["max_per_user"]
        if quantity > cap:
            raise ConflictError(f"Each user can hold at most {cap} unit(s)")

        # Reserve against the user's cap first. When the user already holds too
        # many, the filter misses and the upsert collides with the existing _id.
        key = allocation_id(hardware_id, user_id)
        try:
            self.allocations.update_one(
                {"_id": key, "quantity": {"$lte": cap - quantity}},
                {
                    "$inc": {"quantity": quantity},
                    "$setOnInsert": {"hardware_id": hardware_id, "user_id": user_id},
                },
                upsert=True,
            )
        except DuplicateKeyError as exc:
            held = self.held_by(user_id).get(hardware_id, 0)
            raise ConflictError(
                f"Each user can hold at most {cap} unit(s); you hold {held}"
            ) from exc

        # Then take the units from the pool, undoing the reservation on failure.
        updated = self.sets.find_one_and_update(
            {"_id": hardware_id, "available": {"$gte": quantity}},
            {"$inc": {"available": -quantity}},
            return_document=ReturnDocument.AFTER,
        )
        if updated is None:
            self.allocations.update_one({"_id": key}, {"$inc": {"quantity": -quantity}})
            available = self._get_set(hardware_id)["available"]
            raise ConflictError(f"Only {available} unit(s) available")
        return updated

    def checkin(self, hardware_id: str, user_id: str, quantity: int) -> dict:
        self._get_set(hardware_id)
        key = allocation_id(hardware_id, user_id)
        released = self.allocations.find_one_and_update(
            {"_id": key, "quantity": {"$gte": quantity}},
            {"$inc": {"quantity": -quantity}},
            return_document=ReturnDocument.AFTER,
        )
        if released is None:
            held = self.held_by(user_id).get(hardware_id, 0)
            raise ConflictError(f"You only hold {held} unit(s)")
        if released["quantity"] == 0:
            self.allocations.delete_one({"_id": key, "quantity": 0})
        return self.sets.find_one_and_update(
            {"_id": hardware_id},
            {"$inc": {"available": quantity}},
            return_document=ReturnDocument.AFTER,
        )
