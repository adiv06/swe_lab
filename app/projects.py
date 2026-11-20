"""MongoDB-backed projects and membership."""

from pymongo import ReturnDocument


class ProjectStore:
    def __init__(self, database) -> None:
        self.projects = database["projects"]

    def list(self) -> list[dict]:
        return list(self.projects.find({}))

    def get(self, project_id: str) -> dict | None:
        return self.projects.find_one({"_id": project_id})

    def create(
        self,
        name: str,
        user_id: str,
        project_id: str,
        unit: dict | None = None,
    ) -> dict:
        project = {
            "_id": project_id,
            "name": name,
            "creator_id": user_id,
            "member_ids": [user_id],
            "hardware_unit_id": unit["_id"] if unit else None,
            "hardware_unit_name": unit["name"] if unit else None,
            "allocation_id": unit["allocation_id"] if unit else None,
        }
        self.projects.insert_one(project)
        return project

    def delete_by_creator(self, project_id: str, creator_id: str) -> bool:
        return self.projects.find_one_and_delete({
            "_id": project_id,
            "creator_id": creator_id,
            "hardware_unit_id": None,
        }) is not None

    def clear_hardware(self, project_id: str, allocation_id: str) -> dict | None:
        return self.projects.find_one_and_update(
            {"_id": project_id, "allocation_id": allocation_id},
            {"$set": {
                "hardware_unit_id": None,
                "hardware_unit_name": None,
                "allocation_id": None,
            }},
            return_document=ReturnDocument.AFTER,
        )

    def restore_hardware(self, project_id: str, unit: dict) -> None:
        self.projects.update_one(
            {"_id": project_id, "allocation_id": None},
            {"$set": {
                "hardware_unit_id": unit["_id"],
                "hardware_unit_name": unit["name"],
                "allocation_id": unit["allocation_id"],
            }},
        )

    def join(self, project_id: str, user_id: str) -> dict | None:
        return self.projects.find_one_and_update(
            {"_id": project_id},
            {"$addToSet": {"member_ids": user_id}},
            return_document=ReturnDocument.AFTER,
        )
