import json
import logging
from datetime import datetime
from typing import Optional

import starlette.status as sc
from fastapi import Cookie, HTTPException
from fastapi.routing import APIRouter, Response
from httpx import AsyncClient

import src.api.urls as urls

logger = logging.getLogger(__name__)

auth_router = APIRouter()

COOKIE_SESSION = 'session_id'
COOKIE_USER = 'user'
BROWSER_SESSION_TTL = 10*60


@auth_router.api_route(path='/reports')
async def reports(
    response: Response, session_id: Optional[str]=Cookie(None),
):
    if not session_id:
        return Response(status_code=sc.HTTP_401_UNAUTHORIZED)

    async with AsyncClient() as http:
        url = f'{urls.USER_INFO_URL}?session_id={session_id}'
        auth_response = await http.get(url)

    if valid_session_id := auth_response.cookies.get(COOKIE_SESSION, None):
        response.set_cookie(
            key=COOKIE_SESSION,
            value=valid_session_id,
            httponly=True,
            secure=True,
            samesite='lax',
            max_age=BROWSER_SESSION_TTL,
        )

    if auth_response.status_code != sc.HTTP_200_OK:
        response.delete_cookie(COOKIE_SESSION)
        response.delete_cookie(COOKIE_USER)
        response.status_code=sc.HTTP_401_UNAUTHORIZED
        return

    user_claims = json.loads(auth_response.text)
    return await _create_user_report(user_claims)


async def _create_user_report(user_claims: dict):
    dt = datetime.now()
    return (
        f'*** Report for the {user_claims["name"]} ***\n'
        f'Created at: {dt}\n'
        f'Creator: {user_claims["user_id"]}\n'
        f'\n -------------------------- \n'
        f'<report content>'
    )
