import base64
from os import environ
from typing import Awaitable

from cryptography.fernet import Fernet

TOKEN_ENCRYPT_KEY = environ.get('TOKEN_ENCRYPT_KEY')
TOKEN_ENCRYPT_KEY = base64.urlsafe_b64encode(TOKEN_ENCRYPT_KEY.encode()[:32])

fernet = Fernet(TOKEN_ENCRYPT_KEY)


def encrypt_token(token: str) -> str:
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(encoded_token: str) -> str:
    return fernet.decrypt(encoded_token.encode()).decode()


def decrypt(fn: Awaitable) -> Awaitable:
    async def wrapper(*args, **kwargs) -> Awaitable:
        res = await fn(*args, **kwargs)
        return decrypt_token(res)

    return wrapper
