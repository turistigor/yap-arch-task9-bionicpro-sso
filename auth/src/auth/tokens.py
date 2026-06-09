import base64
from dataclasses import dataclass
import hashlib
import secrets


def generate_state() -> str:
    return secrets.token_urlsafe(32)
