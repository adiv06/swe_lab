"""Small HTTP API for storing JSON values in MongoDB."""

import os
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, JsonValue, field_validator
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.auth import AuthStore
from app.hardware import HardwareError, HardwareStore


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


class HardwareSetPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    capacity: int = Field(ge=0)
    max_per_user: int = Field(ge=1)


class QuantityPayload(BaseModel):
    user_id: str = Field(min_length=1)
    quantity: int = Field(ge=1)


class HardwareSet(BaseModel):
    id: str
    name: str
    capacity: int
    available: int
    max_per_user: int
    held: int = 0


class Allocation(BaseModel):
    user_id: str
    quantity: int


def hardware_set(document: dict, held: int = 0) -> HardwareSet:
    return HardwareSet(
        id=document["_id"],
        name=document["name"],
        capacity=document["capacity"],
        available=document["available"],
        max_per_user=document["max_per_user"],
        held=held,
    )


def public_user(user: dict) -> PublicUser:
    return PublicUser(id=user["_id"], name=user["name"], username=user["_id"])


class MongoStore:
    def __init__(self, uri: str, database: str, collection: str) -> None:
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.database = self.client[database]
        self.collection = self.database[collection]
        self.auth = AuthStore(self.database)
        self.hardware = HardwareStore(self.database)

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


@app.exception_handler(HardwareError)
def hardware_error(_request, exc: HardwareError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(PyMongoError)
def mongo_error(_request, _exc: PyMongoError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "MongoDB unavailable"})


@app.post("/api/auth/register", response_model=AuthResponse, status_code=201)
def register(
    payload: RegisterPayload, store: MongoStore = Depends(get_store)
) -> AuthResponse:
    try:
        user = store.auth.register(payload.username, payload.name, payload.password)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Username already exists") from exc
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="MongoDB unavailable") from exc
    return AuthResponse(user=public_user(user))


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginPayload, store: MongoStore = Depends(get_store)) -> AuthResponse:
    try:
        user = store.auth.login(payload.username.strip().lower(), payload.password)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid username or password")
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="MongoDB unavailable") from exc
    return AuthResponse(user=public_user(user))


@app.get("/api/hardware", response_model=list[HardwareSet])
def list_hardware(
    user_id: str | None = None, store: MongoStore = Depends(get_store)
) -> list[HardwareSet]:
    held = store.hardware.held_by(user_id) if user_id else {}
    return [
        hardware_set(document, held.get(document["_id"], 0))
        for document in store.hardware.list_sets()
    ]


@app.post("/api/hardware", response_model=HardwareSet, status_code=201)
def create_hardware(
    payload: HardwareSetPayload, store: MongoStore = Depends(get_store)
) -> HardwareSet:
    document = store.hardware.create_set(
        payload.name.strip(), payload.capacity, payload.max_per_user
    )
    return hardware_set(document)


@app.get("/api/hardware/{hardware_id}/allocations", response_model=list[Allocation])
def list_allocations(
    hardware_id: str, store: MongoStore = Depends(get_store)
) -> list[Allocation]:
    return [
        Allocation(user_id=a["user_id"], quantity=a["quantity"])
        for a in store.hardware.allocations_for_set(hardware_id)
    ]


@app.post("/api/hardware/{hardware_id}/checkout", response_model=HardwareSet)
def checkout(
    hardware_id: str, payload: QuantityPayload, store: MongoStore = Depends(get_store)
) -> HardwareSet:
    document = store.hardware.checkout(hardware_id, payload.user_id, payload.quantity)
    held = store.hardware.held_by(payload.user_id).get(hardware_id, 0)
    return hardware_set(document, held)


@app.post("/api/hardware/{hardware_id}/checkin", response_model=HardwareSet)
def checkin(
    hardware_id: str, payload: QuantityPayload, store: MongoStore = Depends(get_store)
) -> HardwareSet:
    document = store.hardware.checkin(hardware_id, payload.user_id, payload.quantity)
    held = store.hardware.held_by(payload.user_id).get(hardware_id, 0)
    return hardware_set(document, held)


@app.get("/health")
def health(store: MongoStore = Depends(get_store)) -> dict[str, str]:
    try:
        store.ping()
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="MongoDB unavailable") from exc
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
