"""Small HTTP API for storing JSON values in MongoDB."""

import os
import uuid
from functools import lru_cache

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, JsonValue, field_validator
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.auth import AuthStore, SESSION_DAYS
from app.hardware import HardwareError
from app.projects import ProjectStore
from app.units import UnitStore


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


class ProjectPayload(BaseModel):
    id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{3,64}$")
    name: str = Field(min_length=1, max_length=100)
    hardware_unit_id: str | None = None


class Project(BaseModel):
    id: str
    name: str
    creatorId: str
    memberIds: list[str]
    isMember: bool
    hardwareUnitId: str | None = None
    hardwareUnitName: str | None = None
    allocationId: str | None = None


class AvailableUnit(BaseModel):
    id: str
    name: str


class UnitStatus(AvailableUnit):
    status: str
    projectId: str | None = None


def unit_status(document: dict) -> UnitStatus:
    return UnitStatus(
        id=document["_id"],
        name=document["name"],
        status=document.get("status", "unknown"),
        projectId=document.get("allocated_project_id"),
    )


class InventoryUnit(BaseModel):
    id: str
    name: str
    status: str
    holder: str | None = None
    projectId: str | None = None
    projectName: str | None = None


class Inventory(BaseModel):
    units: list[InventoryUnit]


def public_user(user: dict) -> PublicUser:
    return PublicUser(id=user["_id"], name=user["name"], username=user["_id"])


def public_project(document: dict, user_id: str) -> Project:
    return Project(
        id=document["_id"],
        name=document["name"],
        creatorId=document["creator_id"],
        memberIds=document["member_ids"],
        isMember=user_id in document["member_ids"],
        hardwareUnitId=document.get("hardware_unit_id"),
        hardwareUnitName=document.get("hardware_unit_name"),
        allocationId=document.get("allocation_id"),
    )


class MongoStore:
    def __init__(self, uri: str, database: str, collection: str) -> None:
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.database = self.client[database]
        self.collection = self.database[collection]
        self.auth = AuthStore(self.database)
        self.projects = ProjectStore(self.database)
        self.units = UnitStore(self.database)

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
if os.path.isdir("frontend/dist/assets"):
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")


@app.exception_handler(HardwareError)
def hardware_error(_request, exc: HardwareError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(PyMongoError)
def mongo_error(_request, _exc: PyMongoError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "MongoDB unavailable"})


def require_database(store: MongoStore) -> None:
    try:
        store.ping()
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="MongoDB unavailable") from exc


def current_user(
    session_token: str | None = Cookie(default=None, alias="hw_session"),
    store: MongoStore = Depends(get_store),
) -> dict:
    if not session_token:
        raise HTTPException(status_code=401, detail="Login required")
    user = store.auth.session_user(session_token)
    if user is None:
        raise HTTPException(status_code=401, detail="Login required")
    return user


def set_session(response: Response, store: MongoStore, user: dict) -> None:
    token = store.auth.create_session(user["_id"])
    response.set_cookie(
        "hw_session",
        token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
        path="/",
    )


@app.get("/api/status")
def api_status(store: MongoStore = Depends(get_store)) -> dict[str, str]:
    require_database(store)
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=AuthResponse, status_code=201)
def register(
    payload: RegisterPayload, response: Response, store: MongoStore = Depends(get_store)
) -> AuthResponse:
    require_database(store)
    try:
        user = store.auth.register(payload.username, payload.name, payload.password)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Username already exists") from exc
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="MongoDB unavailable") from exc
    set_session(response, store, user)
    return AuthResponse(user=public_user(user))


@app.post("/api/auth/login", response_model=AuthResponse)
def login(
    payload: LoginPayload, response: Response, store: MongoStore = Depends(get_store)
) -> AuthResponse:
    require_database(store)
    try:
        user = store.auth.login(payload.username.strip().lower(), payload.password)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid username or password")
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="MongoDB unavailable") from exc
    set_session(response, store, user)
    return AuthResponse(user=public_user(user))


@app.get("/api/auth/me", response_model=AuthResponse)
def me(user: dict = Depends(current_user)) -> AuthResponse:
    return AuthResponse(user=public_user(user))


@app.post("/api/auth/logout", status_code=204)
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias="hw_session"),
    store: MongoStore = Depends(get_store),
) -> None:
    if session_token:
        store.auth.delete_session(session_token)
    response.delete_cookie("hw_session", path="/")


@app.get("/api/projects", response_model=list[Project])
def list_projects(
    user: dict = Depends(current_user), store: MongoStore = Depends(get_store)
) -> list[Project]:
    return [public_project(project, user["_id"]) for project in store.projects.list()]


@app.post("/api/projects", response_model=Project, status_code=201)
def create_project(
    payload: ProjectPayload,
    user: dict = Depends(current_user),
    store: MongoStore = Depends(get_store),
) -> Project:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name is required")
    project_id = payload.id or uuid.uuid4().hex
    if store.projects.get(project_id) is not None:
        raise HTTPException(status_code=409, detail="Project ID already exists")
    unit = None
    if payload.hardware_unit_id:
        unit = store.units.reserve(payload.hardware_unit_id, user["_id"], project_id)
    try:
        project = store.projects.create(name, user["_id"], project_id, unit)
    except DuplicateKeyError as exc:
        if unit:
            store.units.release(unit["_id"], unit["allocation_id"])
        raise HTTPException(status_code=409, detail="Project ID already exists") from exc
    except Exception:
        if unit:
            store.units.release(unit["_id"], unit["allocation_id"])
        raise
    return public_project(project, user["_id"])


@app.get("/api/units/available", response_model=list[AvailableUnit])
def list_available_units(
    _user: dict = Depends(current_user), store: MongoStore = Depends(get_store)
) -> list[AvailableUnit]:
    return [AvailableUnit(id=unit["_id"], name=unit["name"]) for unit in store.units.available()]


@app.get("/api/units", response_model=list[UnitStatus])
def list_units(_user: dict = Depends(current_user), store: MongoStore = Depends(get_store)) -> list[UnitStatus]:
    return [unit_status(unit) for unit in store.units.list()]


@app.get("/api/inventory", response_model=Inventory)
def get_inventory(
    _user: dict = Depends(current_user), store: MongoStore = Depends(get_store)
) -> Inventory:
    units = store.units.list()
    user_ids = {unit.get("allocated_user_id") for unit in units}
    user_ids.discard(None)
    users = {
        user["_id"]: user["name"]
        for user in store.auth.users.find({"_id": {"$in": list(user_ids)}})
    }
    projects = {project["_id"]: project["name"] for project in store.projects.list()}
    return Inventory(
        units=[
            InventoryUnit(
                id=unit["_id"],
                name=unit["name"],
                status=unit.get("status", "unknown"),
                holder=users.get(unit["allocated_user_id"], unit["allocated_user_id"])
                if unit.get("allocated_user_id") else None,
                projectId=unit.get("allocated_project_id"),
                projectName=projects.get(unit.get("allocated_project_id")),
            )
            for unit in units
        ],
    )


@app.post("/api/projects/{project_id}/hardware/release", response_model=Project)
def release_project_hardware(
    project_id: str,
    user: dict = Depends(current_user),
    store: MongoStore = Depends(get_store),
) -> Project:
    project = store.projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if user["_id"] not in project["member_ids"]:
        raise HTTPException(status_code=403, detail="Only project members can release hardware")
    if not project.get("hardware_unit_id") or not project.get("allocation_id"):
        raise HTTPException(status_code=409, detail="No hardware is assigned to this project")

    unit = {
        "_id": project["hardware_unit_id"],
        "name": project["hardware_unit_name"],
        "allocation_id": project["allocation_id"],
    }
    cleared = store.projects.clear_hardware(project_id, unit["allocation_id"])
    if cleared is None:
        raise HTTPException(status_code=409, detail="Hardware assignment changed; refresh the project")
    try:
        released = store.units.release(unit["_id"], unit["allocation_id"], project_id)
    except Exception:
        store.projects.restore_hardware(project_id, unit)
        raise
    if not released:
        store.projects.restore_hardware(project_id, unit)
        raise HTTPException(status_code=409, detail="Hardware allocation changed; refresh the project")
    return public_project(cleared, user["_id"])


@app.get("/api/projects/{project_id}", response_model=Project)
def get_project(
    project_id: str,
    user: dict = Depends(current_user),
    store: MongoStore = Depends(get_store),
) -> Project:
    project = store.projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return public_project(project, user["_id"])


@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(
    project_id: str,
    user: dict = Depends(current_user),
    store: MongoStore = Depends(get_store),
) -> None:
    project = store.projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["creator_id"] != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the project creator can delete it")
    if store.units.allocated_to_project(project_id):
        raise HTTPException(status_code=409, detail="Check in all hardware units before deleting this project")
    if not store.projects.delete_by_creator(project_id, user["_id"]):
        raise HTTPException(status_code=409, detail="Project changed; refresh and try again")


@app.post("/api/projects/{project_id}/join", response_model=Project)
def join_project(
    project_id: str,
    user: dict = Depends(current_user),
    store: MongoStore = Depends(get_store),
) -> Project:
    project = store.projects.join(project_id, user["_id"])
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return public_project(project, user["_id"])


def require_project_member(project_id: str, user: dict, store: MongoStore) -> dict:
    project = store.projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if user["_id"] not in project["member_ids"]:
        raise HTTPException(status_code=403, detail="Join the project before managing its hardware")
    return project


@app.post("/api/projects/{project_id}/units/{unit_id}/checkout", response_model=UnitStatus)
def checkout_unit(
    project_id: str, unit_id: str,
    user: dict = Depends(current_user), store: MongoStore = Depends(get_store),
) -> UnitStatus:
    require_project_member(project_id, user, store)
    return unit_status(store.units.reserve(unit_id, user["_id"], project_id))


@app.post("/api/projects/{project_id}/units/{unit_id}/checkin", response_model=UnitStatus)
def checkin_unit(
    project_id: str, unit_id: str,
    user: dict = Depends(current_user), store: MongoStore = Depends(get_store),
) -> UnitStatus:
    project = require_project_member(project_id, user, store)
    unit = store.units.get(unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Hardware unit not found")
    if unit.get("allocated_project_id") != project_id or unit.get("status") != "allocated":
        raise HTTPException(status_code=409, detail="This project does not hold that hardware unit")
    if project.get("hardware_unit_id") == unit_id and project.get("allocation_id") == unit.get("allocation_id"):
        release_project_hardware(project_id, user, store)
    elif not store.units.release(unit_id, unit["allocation_id"], project_id):
        raise HTTPException(status_code=409, detail="Hardware allocation changed; refresh and try again")
    return unit_status(store.units.get(unit_id))


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


@app.get("/{path:path}", include_in_schema=False)
def frontend_page(path: str):
    if path.startswith(("api/", "items/", "assets/")) or path == "health":
        raise HTTPException(status_code=404, detail="Not found")
    index = "frontend/dist/index.html"
    if not os.path.isfile(index):
        raise HTTPException(status_code=404, detail="Frontend is not built")
    return FileResponse(index)
