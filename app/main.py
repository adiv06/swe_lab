"""Hardware Allocator API: accounts, projects and hardware sets in MongoDB."""

import os
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
from app.hardware_sets import HardwareSetStore
from app.projects import ProjectStore, checked_out


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
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{3,64}$")
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)


class QuantityPayload(BaseModel):
    quantity: int = Field(ge=1, le=1_000_000)


class Project(BaseModel):
    id: str
    name: str
    description: str = ""
    creatorId: str
    memberIds: list[str]
    isMember: bool
    hardware: dict[str, int] = {}


class HardwareSet(BaseModel):
    id: str
    name: str
    capacity: int
    available: int


class CheckoutResult(BaseModel):
    project: Project
    hardwareSet: HardwareSet


class InventoryHolder(BaseModel):
    projectId: str
    projectName: str
    quantity: int


class InventorySet(HardwareSet):
    holders: list[InventoryHolder]


class Inventory(BaseModel):
    sets: list[InventorySet]


def public_set(document: dict) -> HardwareSet:
    return HardwareSet(
        id=document["_id"],
        name=document["name"],
        capacity=document["capacity"],
        available=document["available"],
    )


def public_user(user: dict) -> PublicUser:
    return PublicUser(id=user["_id"], name=user["name"], username=user["_id"])


def public_project(document: dict, user_id: str) -> Project:
    return Project(
        id=document["_id"],
        name=document["name"],
        description=document.get("description", ""),
        creatorId=document["creator_id"],
        memberIds=document["member_ids"],
        isMember=user_id in document["member_ids"],
        hardware=checked_out(document),
    )


class MongoStore:
    def __init__(self, uri: str, database: str, collection: str) -> None:
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.database = self.client[database]
        self.collection = self.database[collection]
        self.auth = AuthStore(self.database)
        self.projects = ProjectStore(self.database)
        self.hardware = HardwareSetStore(self.database)

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


app = FastAPI(title="Hardware Allocator")
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
    try:
        project = store.projects.create(
            name, user["_id"], payload.id, payload.description.strip()
        )
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Project ID already exists") from exc
    return public_project(project, user["_id"])


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
    if checked_out(project):
        raise HTTPException(status_code=409, detail="Check in all hardware before deleting this project")
    if not store.projects.delete_by_creator(project_id, user["_id"]):
        raise HTTPException(status_code=409, detail="Project changed; refresh and try again")


def require_project_member(project_id: str, user: dict, store: MongoStore) -> dict:
    project = store.projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if user["_id"] not in project["member_ids"]:
        raise HTTPException(status_code=403, detail="Join this project before managing its hardware")
    return project


@app.get("/api/hardware", response_model=list[HardwareSet])
def list_hardware(
    _user: dict = Depends(current_user), store: MongoStore = Depends(get_store)
) -> list[HardwareSet]:
    return [public_set(document) for document in store.hardware.list()]


@app.post("/api/projects/{project_id}/hardware/{set_id}/checkout", response_model=CheckoutResult)
def checkout_hardware(
    project_id: str,
    set_id: str,
    payload: QuantityPayload,
    user: dict = Depends(current_user),
    store: MongoStore = Depends(get_store),
) -> CheckoutResult:
    require_project_member(project_id, user, store)
    hardware_set = store.hardware.take(set_id, payload.quantity)
    try:
        project = store.projects.add_hardware(project_id, user["_id"], set_id, payload.quantity)
    except Exception:
        store.hardware.give_back(set_id, payload.quantity)
        raise
    if project is None:
        store.hardware.give_back(set_id, payload.quantity)
        raise HTTPException(status_code=403, detail="Join this project before managing its hardware")
    return CheckoutResult(project=public_project(project, user["_id"]), hardwareSet=public_set(hardware_set))


@app.post("/api/projects/{project_id}/hardware/{set_id}/checkin", response_model=CheckoutResult)
def checkin_hardware(
    project_id: str,
    set_id: str,
    payload: QuantityPayload,
    user: dict = Depends(current_user),
    store: MongoStore = Depends(get_store),
) -> CheckoutResult:
    project = require_project_member(project_id, user, store)
    hardware_set = store.hardware.get(set_id)
    if hardware_set is None:
        raise HTTPException(status_code=404, detail="Hardware set not found")
    updated = store.projects.remove_hardware(project_id, user["_id"], set_id, payload.quantity)
    if updated is None:
        held = checked_out(store.projects.get(project_id) or project).get(set_id, 0)
        raise HTTPException(
            status_code=409,
            detail=f"Cannot check in {payload.quantity} units of {hardware_set['name']}: "
            f"this project only has {held} checked out",
        )
    hardware_set = store.hardware.give_back(set_id, payload.quantity)
    return CheckoutResult(project=public_project(updated, user["_id"]), hardwareSet=public_set(hardware_set))


@app.get("/api/inventory", response_model=Inventory)
def get_inventory(
    _user: dict = Depends(current_user), store: MongoStore = Depends(get_store)
) -> Inventory:
    projects = store.projects.list()
    return Inventory(
        sets=[
            InventorySet(
                **public_set(document).model_dump(),
                holders=[
                    InventoryHolder(
                        projectId=project["_id"],
                        projectName=project["name"],
                        quantity=checked_out(project)[document["_id"]],
                    )
                    for project in projects
                    if checked_out(project).get(document["_id"])
                ],
            )
            for document in store.hardware.list()
        ]
    )


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
