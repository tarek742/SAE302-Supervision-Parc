from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

_ph = PasswordHasher()


def hash_secret(plain: str) -> str:
    return _ph.hash(plain)


def verify_secret(stored_hash: str, plain: str) -> bool:
    try:
        _ph.verify(stored_hash, plain)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False
