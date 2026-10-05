"""Small HTTP API for storing JSON values in MongoDB."""

import os
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field, JsonValue, field_validator
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.auth import AuthStore


class ValuePayload(BaseModel):
    value: JsonValue


class RegisterPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    username: str = Field(pattern=r"^[a-zA-Z0-9_]{3,32}$")
    password: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name is required")
        return value

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.lower()


class LoginPayload(BaseModel):
    username: str
    password: str


class PublicUser(BaseModel):
    id: str
    name: str
    username: str


class AuthResponse(BaseModel):
    user: PublicUser


def public_user(user: dict) -> PublicUser:
    return PublicUser(id=user["_id"], name=user["name"], username=user["_id"])


class MongoStore:
    def __init__(self, uri: str, database: str, collection: str) -> None:
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.database = self.client[database]
        self.collection = self.database[collection]
        self.auth = AuthStore(self.database)

    def get(self, key: str) -> dict | None:
        return self.collection.find_one({"_id": key}, {"value": 1})

    def set(self, key: str, value: JsonValue) -> None:
        self.collection.replace_one(
            {"_id": key}, {"_id": key, "value": value}, upsert=True
        )

    def ping(self) -> None:
        self.client.admin.command("ping")


@lru_cache
def get_store() -> MongoStore:
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MONGODB_URI is not configured",
        )
    try:
        return MongoStore(
            uri,
            os.getenv("MONGODB_DATABASE", "swe_lab"),
            os.getenv("MONGODB_COLLECTION", "items"),
        )
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="MongoDB unavailable") from exc


app = FastAPI(title="MongoDB key-value service")


def require_database(store: MongoStore) -> None:
    try:
        store.ping()
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="MongoDB unavailable") from exc


@app.get("/api/status")
def api_status(store: MongoStore = Depends(get_store)) -> dict[str, str]:
    require_database(store)
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=AuthResponse, status_code=201)
def register(
    payload: RegisterPayload, store: MongoStore = Depends(get_store)
) -> AuthResponse:
    require_database(store)
    try:
        user = store.auth.register(payload.username, payload.name, payload.password)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Username already exists") from exc
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="MongoDB unavailable") from exc
    return AuthResponse(user=public_user(user))


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginPayload, store: MongoStore = Depends(get_store)) -> AuthResponse:
    require_database(store)
    try:
        user = store.auth.login(payload.username.strip().lower(), payload.password)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid username or password")
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="MongoDB unavailable") from exc
    return AuthResponse(user=public_user(user))


@app.get("/health")
def health(store: MongoStore = Depends(get_store)) -> dict[str, str]:
    require_database(store)
    return {"status": "ok"}


@app.get("/items/{key}", response_model=ValuePayload)
def get_item(key: str, store: MongoStore = Depends(get_store)) -> ValuePayload:
    try:
        document = store.get(key)
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="MongoDB unavailable") from exc
    if document is None:
        raise HTTPException(status_code=404, detail="Key not found")
    return ValuePayload(value=document["value"])


@app.put("/items/{key}", response_model=ValuePayload)
def set_item(
    key: str, payload: ValuePayload, store: MongoStore = Depends(get_store)
) -> ValuePayload:
    try:
        store.set(key, payload.value)
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="MongoDB unavailable") from exc
    return payload
