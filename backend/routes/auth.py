from bson import ObjectId
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or not password:
        return jsonify({"error": "name, email, and password are required"}), 400

    db = get_db()
    if db.users.find_one({"email": email}):
        return jsonify({"error": "an account with this email already exists"}), 409

    user_doc = {
        "name": name,
        "email": email,
        "password_hash": generate_password_hash(password),
    }
    result = db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    token = create_access_token(identity=user_id)
    return jsonify({"token": token, "user": {"id": user_id, "name": name, "email": email}}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    db = get_db()
    user = db.users.find_one({"email": email})
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "invalid email or password"}), 401

    user_id = str(user["_id"])
    token = create_access_token(identity=user_id)
    return jsonify({"token": token, "user": {"id": user_id, "name": user["name"], "email": user["email"]}})


@auth_bp.get("/me")
@jwt_required()
def me():
    db = get_db()
    user = db.users.find_one({"_id": ObjectId(get_jwt_identity())})
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify({"id": str(user["_id"]), "name": user["name"], "email": user["email"]})
