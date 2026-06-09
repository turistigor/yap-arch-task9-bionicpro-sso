import json
import uuid
from enum import IntEnum
from datetime import datetime
from os import environ

import redis.asyncio as aioredis

from src.tools import get_redis_url, decrypt, encrypt_token

REDIS_PASSWORD = environ.get('REDIS_PASSWORD', None)
REDIS_URL = get_redis_url()

TTL_FIELD = 'expires_in'
CREATED_AT_FIELD = 'created_at'
ACCESS_TOKEN_FIELD = 'access_token'
REFRESH_TOKEN_FIELD = 'refresh_token'

REDIS_TTL_ADD = 5*60  # Храним сессию после её логической инвалидации

redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)


class SessionException(Exception):
    """Ошибки при работе ссессиями."""


async def create_session(tokens_data: dict) -> str:
    new_session_id = str(uuid.uuid4())
    tokens_data[CREATED_AT_FIELD] = datetime.now().timestamp()
    ttl = tokens_data[TTL_FIELD]

    tokens_data[ACCESS_TOKEN_FIELD] = encrypt_token(tokens_data[ACCESS_TOKEN_FIELD])
    tokens_data[REFRESH_TOKEN_FIELD] = encrypt_token(tokens_data[REFRESH_TOKEN_FIELD])

    try:
        await redis_client.set(
            new_session_id, json.dumps(tokens_data), ex=ttl + REDIS_TTL_ADD,
        )
    except Exception as ex:
        raise SessionException('Session creation error') from ex

    return new_session_id


async def refresh_session(tokens_data: dict, old_session: str) -> str:
    try:
        return await create_session(tokens_data)
    finally:
        await delete_session(old_session)


async def delete_session(session_id: str):
    try:
        await redis_client.delete(session_id)
    except Exception as ex:
        raise SessionException('Session deletion error') from ex


class SessionStatus(IntEnum):
    VALID: int = 1
    EXPIRED: int = 2
    NOT_EXISTS: int = 3


async def check_session(session_id: str) -> SessionStatus:
    session_data = await _get_session_data(session_id)
    if not session_data:
        return SessionStatus.NOT_EXISTS

    ttl = session_data[TTL_FIELD]
    created_at = datetime.fromtimestamp(session_data[CREATED_AT_FIELD])
    if _check_session_ttl(ttl, created_at) is True:
        return SessionStatus.VALID

    return SessionStatus.EXPIRED


@decrypt
async def get_refresh_token(session_id: str) -> str:
    session_data = await _get_session_data(session_id)
    return session_data[REFRESH_TOKEN_FIELD]

@decrypt
async def get_access_token(session_id: str) -> str:
    session_data = await _get_session_data(session_id)
    return session_data[ACCESS_TOKEN_FIELD]


async def _get_session_data(session_id: str) -> str:
    try:
        session_str = await redis_client.get(session_id)
    except Exception as ex:
        raise SessionException('Session getting from cache error') from ex

    return json.loads(session_str) if session_str else ''


def _check_session_ttl(ttl: int, created_at: datetime) -> bool:
    elapsed_sec = (datetime.now() - created_at).total_seconds()
    return elapsed_sec < ttl
