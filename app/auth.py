"""MongoDB-backed username and password storage."""

import hashlib
import hmac
import secrets


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

    def register(self, username: str, name: str, password: str) -> dict:
        user = {"_id": username, "name": name, "password_hash": hash_password(password)}
        self.users.insert_one(user)
        return user

    def login(self, username: str, password: str) -> dict | None:
        user = self.users.find_one({"_id": username})
        if not user or not verify_password(password, user["password_hash"]):
            return None
        return user
