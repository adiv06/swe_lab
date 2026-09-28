from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from db import get_db

projects_bp = Blueprint("projects", __name__)


def serialize_project(project, user_id=None):
    return {
        "id": str(project["_id"]),
        "name": project["name"],
        "creator_id": project["creator_id"],
        "member_ids": project["member_ids"],
        "is_member": user_id in project["member_ids"] if user_id else False,
    }


def _get_project_or_none(db, project_id):
    if not ObjectId.is_valid(project_id):
        return None
    return db.projects.find_one({"_id": ObjectId(project_id)})


@projects_bp.get("")
def list_projects():
    db = get_db()
    projects = list(db.projects.find())
    return jsonify([serialize_project(p) for p in projects])


@projects_bp.post("")
@jwt_required()
def create_project():
    user_id = get_jwt_identity()
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    db = get_db()
    project_doc = {"name": name, "creator_id": user_id, "member_ids": [user_id]}
    result = db.projects.insert_one(project_doc)
    project_doc["_id"] = result.inserted_id
    return jsonify(serialize_project(project_doc, user_id)), 201


@projects_bp.get("/mine")
@jwt_required()
def my_projects():
    user_id = get_jwt_identity()
    db = get_db()
    projects = list(db.projects.find({"member_ids": user_id}))
    return jsonify([serialize_project(p, user_id) for p in projects])


@projects_bp.get("/<project_id>")
def get_project(project_id):
    db = get_db()
    project = _get_project_or_none(db, project_id)
    if not project:
        return jsonify({"error": "project not found"}), 404
    return jsonify(serialize_project(project))


@projects_bp.post("/<project_id>/join")
@jwt_required()
def join_project(project_id):
    user_id = get_jwt_identity()
    db = get_db()
    project = _get_project_or_none(db, project_id)
    if not project:
        return jsonify({"error": "project not found"}), 404

    db.projects.update_one({"_id": project["_id"]}, {"$addToSet": {"member_ids": user_id}})
    project = db.projects.find_one({"_id": project["_id"]})
    return jsonify(serialize_project(project, user_id))
