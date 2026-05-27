from datetime import date
import json
import logging
from os import environ
from typing import Optional

import starlette.status as sc
from fastapi import Cookie, Query
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter, Response
from httpx import AsyncClient

import src.api.urls as urls
from src.olap import get_report_data
from src.report import create_html_report

logger = logging.getLogger(__name__)

auth_router = APIRouter()

COOKIE_SESSION = 'session_id'
COOKIE_USER = 'user'
BROWSER_SESSION_TTL = 10*60

OLAP_CONNECTION_STR = environ.get('OLAP_CONNECTION_STR')
OLAP_TABLE_NAME = 'reports'


@auth_router.api_route(path='/reports')
async def reports(
    response: Response,
    period: Optional[date]=Query(date.today()),
    session_id: Optional[str]=Cookie(None),
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

    report = await _create_user_report(user_claims, period)
    return HTMLResponse(content=report)


async def _create_user_report(user_claims: dict, period: date):
    report_data = await get_report_data(
        olap_conn_str=OLAP_CONNECTION_STR,
        olap_table_name=OLAP_TABLE_NAME,
        user_name=user_claims['preferred_username'],
        period=period,
    )

    return create_html_report(
        user_claims['name'], user_claims['user_id'], report_data, period,
    )
