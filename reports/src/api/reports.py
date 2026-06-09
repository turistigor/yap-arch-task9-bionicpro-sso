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
from src.s3 import check_s3_exists, get_s3_key, save_to_s3

logger = logging.getLogger(__name__)

auth_router = APIRouter()

COOKIE_SESSION = 'session_id'
COOKIE_USER = 'user'
BROWSER_SESSION_TTL = 10*60

OLAP_CONNECTION_STR = environ.get('OLAP_CONNECTION_STR')
OLAP_TABLE_NAME = 'reports'

S3_URL = environ.get('S3_URL')
S3_ACCES_KEY = environ.get('S3_ACCESS_KEY')
S3_SECRET_KEY = environ.get('S3_SEKRET_KEY')
S3_BUCKET = 'reports'

CDN_URL = environ.get('CDN_URL')


@auth_router.api_route(path='/reports')
async def reports(
    response: Response,
    period: Optional[date]=Query(date.today()),
    session_id: Optional[str]=Cookie(None),
):
    if not session_id:
        return Response(status_code=sc.HTTP_401_UNAUTHORIZED)

    user_claims = await _get_user_claims(response, session_id)
    if user_claims is None:
        return
    
    s3_key = get_s3_key(user_claims['user_id'], period)
    report_exists = await check_s3_exists(s3_key, S3_URL, S3_ACCES_KEY, S3_SECRET_KEY, S3_BUCKET)
    if report_exists is True:
        return {
            'cdn_url': _get_cdn_url(s3_key, S3_BUCKET)
        }

    report = await _create_user_report(user_claims, period)

    await save_to_s3(s3_key, S3_URL, S3_ACCES_KEY, S3_SECRET_KEY, S3_BUCKET, report)

    return {
        'cdn_url': _get_cdn_url(s3_key, S3_BUCKET)
    }


def _get_cdn_url(s3_key: str, bucket: str) -> str:
    return f'{CDN_URL}/{bucket}/{s3_key}'


async def _get_user_claims(response: Response, session_id: str) -> dict | None:
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

    return json.loads(auth_response.text)


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
