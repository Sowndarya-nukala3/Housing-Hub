"""Sprint 1 password and session primitives."""
import hashlib
import hmac
import time
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError

_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
def hash_password(value: str) -> str:
    return _hasher.hash(value)

def verify_password(value: str, stored: str) -> bool:
    try:
        if stored.startswith("$argon2id$"):
            return _hasher.verify(stored, value)
        salt, digest = stored.split(":")
        candidate = hashlib.pbkdf2_hmac("sha256", value.encode(), bytes.fromhex(salt), 200000).hex()
        return hmac.compare_digest(candidate, digest)
    except (VerificationError, InvalidHashError, ValueError):
        return False

def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def now_epoch() -> int:
    return int(time.time())

def expiry() -> int:
    return now_epoch() + 3600
