"""Individual hardware units stored in the Atlas HW Allocation collection."""

from __future__ import annotations

import uuid

from pymongo import ReturnDocument

from app.hardware import ConflictError, NotFoundError


class UnitStore:
    def __init__(self, database) -> None:
        self.units = database["HW Allocation"]

    def ensure_defaults(self) -> None:
        if self.units.find_one({}) is not None:
            return
        for unit_id, name in (
            ("hw-unit-001", "Arduino Kit 1"),
            ("hw-unit-002", "Raspberry Pi Kit 1"),
        ):
            self.units.update_one(
                {"_id": unit_id},
                {"$setOnInsert": {"name": name, "status": "available"}},
                upsert=True,
            )

    def available(self) -> list[dict]:
        self.ensure_defaults()
        return list(self.units.find({"status": "available"}))

    def list(self) -> list[dict]:
        self.ensure_defaults()
        return list(self.units.find({}))

    def get(self, unit_id: str) -> dict | None:
        self.ensure_defaults()
        return self.units.find_one({"_id": unit_id})

    def allocated_to_project(self, project_id: str) -> list[dict]:
        return list(self.units.find({"allocated_project_id": project_id, "status": "allocated"}))

    def reserve(self, unit_id: str, user_id: str, project_id: str) -> dict:
        self.ensure_defaults()
        allocation_id = uuid.uuid4().hex
        unit = self.units.find_one_and_update(
            {"_id": unit_id, "status": "available"},
            {"$set": {
                "status": "allocated",
                "allocated_user_id": user_id,
                "allocated_project_id": project_id,
                "allocation_id": allocation_id,
            }},
            return_document=ReturnDocument.AFTER,
        )
        if unit is not None:
            return unit
        if self.units.find_one({"_id": unit_id}) is None:
            raise NotFoundError("Hardware unit not found")
        raise ConflictError("Hardware unit is already allocated")

    def release(self, unit_id: str, allocation_id: str, project_id: str | None = None) -> bool:
        query = {"_id": unit_id, "allocation_id": allocation_id}
        if project_id is not None:
            query["allocated_project_id"] = project_id
        released = self.units.find_one_and_update(
            query,
            {
                "$set": {"status": "available"},
                "$unset": {
                    "allocated_user_id": "",
                    "allocated_project_id": "",
                    "allocation_id": "",
                },
            },
            return_document=ReturnDocument.AFTER,
        )
        return released is not None
