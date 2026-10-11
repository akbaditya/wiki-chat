import hashlib
import hmac

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config import settings

_ph = PasswordHasher()  # argon2id, salted, slow by design
_DUMMY_HASH = _ph.hash("dummy-password-for-timing-equalisation")


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    try:
        return _ph.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def burn_verify(password: str) -> None:
    """Run a fake verify when the email doesn't exist, so response time
    doesn't reveal which emails are registered."""
    verify_password(_DUMMY_HASH, password)


def hmac_hash(value: str) -> str:
    """Keyed hash for IPs / emails in lockout and guest tables.
    We never store raw IPs."""
    return hmac.new(
        settings.hmac_secret.encode(), value.encode(), hashlib.sha256
    ).hexdigest()