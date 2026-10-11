"""Run: python scripts/hash_password.py  -> paste output into ADMIN_PASSWORD_HASH"""
from getpass import getpass

from argon2 import PasswordHasher

pw = getpass("Admin password: ")
if len(pw) < 12:
    raise SystemExit("Use at least 12 characters for the admin password.")
print(PasswordHasher().hash(pw))