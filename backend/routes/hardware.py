from bson import ObjectId
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from db import get_db

hardware_bp = Blueprint("hardware", __name__)


def _get_allocated_total(db, hardware_set_id):
    pipeline = [
        {"$match": {"hardware_set_id": hardware_set_id}},
        {"$group": {"_id": None, "total": {"$sum": "$quantity"}}},
    ]
    result = list(db.allocations.aggregate(pipeline))
    return result[0]["total"] if result else 0


def _get_allocation_quantity(db, hardware_set_id, project_id):
    allocation = db.allocations.find_one({"hardware_set_id": hardware_set_id, "project_id": project_id})
    return allocation["quantity"] if allocation else 0


def serialize_hardware_set(db, hw):
    hw_id = str(hw["_id"])
    allocated = _get_allocated_total(db, hw_id)
    return {
        "id": hw_id,
        "name": hw["name"],
        "total_units": hw["total_units"],
        "allocated_units": allocated,
        "available_units": hw["total_units"] - allocated,
    }


def _get_hardware_set_or_none(db, hardware_set_id):
    if not ObjectId.is_valid(hardware_set_id):
        return None
    return db.hardware_sets.find_one({"_id": ObjectId(hardware_set_id)})


@hardware_bp.get("")
def list_hardware_sets():
    db = get_db()
    sets = list(db.hardware_sets.find())
    return jsonify([serialize_hardware_set(db, hw) for hw in sets])


@hardware_bp.post("")
@jwt_required()
def create_hardware_set():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    total_units = data.get("total_units")

    if not name or not isinstance(total_units, int) or total_units < 0:
        return jsonify({"error": "name and a non-negative integer total_units are required"}), 400

    db = get_db()
    result = db.hardware_sets.insert_one({"name": name, "total_units": total_units})
    hw = db.hardware_sets.find_one({"_id": result.inserted_id})
    return jsonify(serialize_hardware_set(db, hw)), 201


@hardware_bp.get("/<hardware_set_id>/allocations")
def list_allocations(hardware_set_id):
    db = get_db()
    hw = _get_hardware_set_or_none(db, hardware_set_id)
    if not hw:
        return jsonify({"error": "hardware set not found"}), 404

    allocations = list(db.allocations.find({"hardware_set_id": hardware_set_id, "quantity": {"$gt": 0}}))
    output = []
    for a in allocations:
        project = db.projects.find_one({"_id": ObjectId(a["project_id"])}) if ObjectId.is_valid(a["project_id"]) else None
        output.append(
            {
                "project_id": a["project_id"],
                "project_name": project["name"] if project else "Unknown project",
                "quantity": a["quantity"],
            }
        )
    return jsonify(output)


def _require_membership(db, project_id, user_id):
    if not ObjectId.is_valid(project_id):
        return None, (jsonify({"error": "project not found"}), 404)
    project = db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        return None, (jsonify({"error": "project not found"}), 404)
    if user_id not in project["member_ids"]:
        return None, (jsonify({"error": "you must be a member of this project"}), 403)
    return project, None


@hardware_bp.post("/<hardware_set_id>/checkout")
@jwt_required()
def checkout(hardware_set_id):
    user_id = get_jwt_identity()
    data = request.get_json(force=True) or {}
    project_id = data.get("project_id")
    quantity = data.get("quantity")

    if not project_id or not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"error": "project_id and a positive integer quantity are required"}), 400

    db = get_db()
    hw = _get_hardware_set_or_none(db, hardware_set_id)
    if not hw:
        return jsonify({"error": "hardware set not found"}), 404

    _, error = _require_membership(db, project_id, user_id)
    if error:
        return error

    allocated = _get_allocated_total(db, hardware_set_id)
    available = hw["total_units"] - allocated
    if quantity > available:
        return jsonify({"error": f"only {available} unit(s) available"}), 409

    db.allocations.update_one(
        {"hardware_set_id": hardware_set_id, "project_id": project_id},
        {"$inc": {"quantity": quantity}},
        upsert=True,
    )
    hw = db.hardware_sets.find_one({"_id": hw["_id"]})
    return jsonify(serialize_hardware_set(db, hw))


@hardware_bp.post("/<hardware_set_id>/checkin")
@jwt_required()
def checkin(hardware_set_id):
    user_id = get_jwt_identity()
    data = request.get_json(force=True) or {}
    project_id = data.get("project_id")
    quantity = data.get("quantity")

    if not project_id or not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"error": "project_id and a positive integer quantity are required"}), 400

    db = get_db()
    hw = _get_hardware_set_or_none(db, hardware_set_id)
    if not hw:
        return jsonify({"error": "hardware set not found"}), 404

    _, error = _require_membership(db, project_id, user_id)
    if error:
        return error

    allocated_to_project = _get_allocation_quantity(db, hardware_set_id, project_id)
    if quantity > allocated_to_project:
        return jsonify({"error": f"this project only holds {allocated_to_project} unit(s)"}), 409

    db.allocations.update_one(
        {"hardware_set_id": hardware_set_id, "project_id": project_id},
        {"$inc": {"quantity": -quantity}},
    )
    hw = db.hardware_sets.find_one({"_id": hw["_id"]})
    return jsonify(serialize_hardware_set(db, hw))
