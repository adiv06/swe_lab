"""MongoDB-backed username and password storage."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone


SESSION_DAYS = 30


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt_hex, digest_hex = stored.split("$")
        if algorithm != "scrypt":
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt_hex), n=16384, r=8, p=1
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


class AuthStore:
    def __init__(self, database) -> None:
        self.users = database["users"]
        self.sessions = database["sessions"]
        self.sessions.create_index("expires_at", expireAfterSeconds=0)

    def register(self, username: str, name: str, password: str) -> dict:
        user = {"_id": username, "name": name, "password_hash": hash_password(password)}
        self.users.insert_one(user)
        return user

    def login(self, username: str, password: str) -> dict | None:
        user = self.users.find_one({"_id": username})
        if not user or not verify_password(password, user["password_hash"]):
            return None
        return user

    def create_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        self.sessions.insert_one({
            "_id": hashlib.sha256(token.encode()).hexdigest(),
            "user_id": user_id,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS),
        })
        return token

    def session_user(self, token: str) -> dict | None:
        key = hashlib.sha256(token.encode()).hexdigest()
        session = self.sessions.find_one({"_id": key})
        if session is None:
            return None
        expires_at = session["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            self.sessions.delete_one({"_id": key})
            return None
        return self.users.find_one({"_id": session["user_id"]})

    def delete_session(self, token: str) -> None:
        self.sessions.delete_one({"_id": hashlib.sha256(token.encode()).hexdigest()})
