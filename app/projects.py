"""MongoDB-backed projects, membership, and per-project hardware counts."""

from pymongo import ReturnDocument


def checked_out(project: dict) -> dict[str, int]:
    """Units of each hardware set the project currently holds (zeros dropped)."""
    return {set_id: qty for set_id, qty in (project.get("hardware") or {}).items() if qty}


class ProjectStore:
    def __init__(self, database) -> None:
        self.projects = database["projects"]

    def list(self) -> list[dict]:
        return list(self.projects.find({}))

    def get(self, project_id: str) -> dict | None:
        return self.projects.find_one({"_id": project_id})

    def create(self, name: str, user_id: str, project_id: str, description: str = "") -> dict:
        project = {
            "_id": project_id,
            "name": name,
            "description": description,
            "creator_id": user_id,
            "member_ids": [user_id],
            "hardware": {},
        }
        self.projects.insert_one(project)
        return project

    def join(self, project_id: str, user_id: str) -> dict | None:
        return self.projects.find_one_and_update(
            {"_id": project_id},
            {"$addToSet": {"member_ids": user_id}},
            return_document=ReturnDocument.AFTER,
        )

    def add_hardware(self, project_id: str, user_id: str, set_id: str, quantity: int) -> dict | None:
        """Record units checked out by a member. Returns None if not a member."""
        return self.projects.find_one_and_update(
            {"_id": project_id, "member_ids": user_id},
            {"$inc": {f"hardware.{set_id}": quantity}},
            return_document=ReturnDocument.AFTER,
        )

    def remove_hardware(self, project_id: str, user_id: str, set_id: str, quantity: int) -> dict | None:
        """Record units checked in. Returns None if the project holds fewer units."""
        return self.projects.find_one_and_update(
            {
                "_id": project_id,
                "member_ids": user_id,
                f"hardware.{set_id}": {"$gte": quantity},
            },
            {"$inc": {f"hardware.{set_id}": -quantity}},
            return_document=ReturnDocument.AFTER,
        )

    def delete_by_creator(self, project_id: str, creator_id: str) -> bool:
        return self.projects.find_one_and_delete(
            {"_id": project_id, "creator_id": creator_id}
        ) is not None
