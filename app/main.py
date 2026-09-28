"""Small HTTP API for storing JSON values in MongoDB."""

import os
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, JsonValue
from pymongo import MongoClient
from pymongo.errors import PyMongoError


class ValuePayload(BaseModel):
    value: JsonValue


class MongoStore:
    def __init__(self, uri: str, database: str, collection: str) -> None:
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.database = self.client[database]
        self.collection = self.database[collection]

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
