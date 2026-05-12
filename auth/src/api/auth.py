import json
import logging 
from typing import Optional

from keycloak import KeycloakError, KeycloakOpenID
import starlette.status as sc
import urllib
from fastapi import APIRouter, Cookie, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse

import src.auth as auth
import src.api.urls as urls

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix='/auth')

COOKIE_STATE = 'state'
COOKIE_CODE_VERIFIER = 'code_verifier'
COOKIE_USER = 'user'
COOKIE_SESSION = 'session_id'

BROWSER_SESSION_TTL = 10*60

# HTTP endpoints

@auth_router.api_route(path='/login')
async def login(request: Request):
    state = auth.generate_state()
    request.session[COOKIE_STATE] = state

    code_verifier = auth.generate_pkce_code_verifier()
    request.session[COOKIE_CODE_VERIFIER] = code_verifier

    keycloak_oid = request.app.state.keycloak_oid
    auth_url = await keycloak_oid.a_auth_url(
        redirect_uri=urls.AUTH_CALLBACK_URL,
        scope='openid profile email',
        state=state,
    )

    code_challenge, pkce_method = auth.generate_pkce_code_challenge(code_verifier)
    auth_url += (
        f'&code_challenge={code_challenge}'
        f'&code_challenge_method={pkce_method}'
    )

    return RedirectResponse(url=auth_url)


@auth_router.api_route(path='/callback')
async def callback(
    request: Request,
    state: Optional[str] = Query(default=None),
    code: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    code_verifier: Optional[str] = Cookie(default=None),
):
    _check_callback_args(state, code, error)
    _check_state(request.session.get(COOKIE_STATE), state)
    code_verifier = request.session.get(COOKIE_CODE_VERIFIER)
    _check_code_verifier(code_verifier)

    keycloak_oid = request.app.state.keycloak_oid

    try:
        token_data = await keycloak_oid.a_token(
            grant_type='authorization_code',
            code=code,
            code_verifier=code_verifier,
            redirect_uri=urls.AUTH_CALLBACK_URL,
        )
    except Exception as e:
        raise HTTPException(
            status_code=sc.HTTP_307_TEMPORARY_REDIRECT,
            detail=f'Token exchange failed: {str(e)}',
        )

    request.session.pop(COOKIE_STATE, None)
    request.session.pop(COOKIE_CODE_VERIFIER, None)
    request.cookies.pop(COOKIE_USER, None)

    access_token = token_data[auth.ACCESS_TOKEN_FIELD]
    session_id = await auth.create_session(token_data)
    user_info = await _get_user_info(access_token, keycloak_oid)

    return _create_callback_response(user_info, session_id)


@auth_router.api_route(path='/status')
async def status(
    request: Request,
    response: Response,
    session_id: Optional[str] = Cookie(None),
):
    if not session_id:
        response.status_code = sc.HTTP_401_UNAUTHORIZED
        return

    keycloak_oid = request.app.state.keycloak_oid
    valid_session_id = await _get_valid_session(session_id, keycloak_oid)
    if valid_session_id == session_id:
        response.status_code = sc.HTTP_200_OK
        return

    await auth.delete_session(session_id)

    if not valid_session_id:
        _create_session_refresh_failed_response(response)
        return

    _create_session_refresh_success_response(
        request, response, valid_session_id,
    )


@auth_router.api_route('/me')
async def user_info(
    request: Request, response: Response, session_id: Optional[str]=Query(None),
):
    if not session_id:
        response.status_code=sc.HTTP_401_UNAUTHORIZED
        return
    
    keycloak_oid = request.app.state.keycloak_oid
    valid_session_id = await _get_valid_session(session_id, keycloak_oid)
    if valid_session_id != session_id:
        _set_session_cookie(response, valid_session_id)
        await auth.delete_session(session_id)

    access_token = await auth.get_access_token(valid_session_id)
    if not access_token:
        raise HTTPException(
            status_code=sc.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='There are no access_token in the session',
        )

    keycloak_oid = request.app.state.keycloak_oid
    user_claims = await _get_user_claims(access_token, keycloak_oid)

    return user_claims


@auth_router.api_route('/logout')
async def logout(
    request: Request, response: Response, session_id: Optional[str]=Cookie(None),
):
    if not session_id:
        response.status_code=sc.HTTP_401_UNAUTHORIZED
        return

    keycloak_oid = request.app.state.keycloak_oid
    await _logout(session_id, keycloak_oid)

    await auth.delete_session(session_id)

    response.delete_cookie(COOKIE_USER)
    response.delete_cookie(COOKIE_SESSION)

# Private functions

async def _logout(session_id: str, keycloak_oid: KeycloakOpenID):
    refresh_token = await auth.get_refresh_token(session_id)

    try:
        response = await keycloak_oid.a_logout(refresh_token)
    except KeycloakError as ex:
        logger.error(f'Logout error: {ex}')
    
    logger.info(response) 


async def _get_valid_session(session_id: str, keycloak_oid: KeycloakOpenID) -> str | None:
    session_status = await auth.check_session(session_id)

    if session_status == auth.SessionStatus.VALID:
        return session_id
    elif session_status == auth.SessionStatus.EXPIRED:
        refresh_token = await auth.get_refresh_token(session_id)
        if token_data := await _refresh_token(refresh_token, keycloak_oid):
            return await auth.refresh_session(token_data, session_id)
    elif session_status == auth.SessionStatus.NOT_EXISTS:
        return None
    else:
        raise ValueError(f'Unexpected session status {session_status}')

    return None


async def _get_user_claims(
    access_token: str, keycloak_oid: KeycloakOpenID,
) -> Optional[str]:
    try:
        token_data = await keycloak_oid.a_decode_token(access_token)
    except KeycloakError as ex:
        logger.error(f'User info getting error: {ex}')

    return {
        'roles'             : token_data['realm_access']['roles'],
        'user_id'           : token_data['sub'],
        'name'              : token_data['name'],
        'preferred_username': token_data['preferred_username'],
        'given_name'        : token_data['given_name'],
        'family_name'       : token_data['family_name'],
        'email'             : token_data['email'],
    }


async def _get_user_info(
    access_token: str, keycloak_oid: KeycloakOpenID,
) -> Optional[str]:
    try:
        return await keycloak_oid.a_userinfo(access_token)
    except KeycloakError as ex:
        logger.error(f'User info getting error: {ex}')


async def _refresh_token(refresh_token: str, keycloak_oid: KeycloakOpenID) -> Optional[str]:
    try:
        return await keycloak_oid.a_refresh_token(refresh_token)
    except KeycloakError as ex:
        logger.error(f'Refreshing token error: {ex}')


def _create_session_refresh_success_response(
    request: Request, response: Response, session_id: str,
):
    response.status_code = sc.HTTP_200_OK
    _set_session_cookie(response, session_id)
    _set_user_cookie(response, request.cookies[COOKIE_USER])


def _create_session_refresh_failed_response(response: Response):
    response.status_code = sc.HTTP_500_INTERNAL_SERVER_ERROR
    response.delete_cookie(COOKIE_USER)
    response.delete_cookie(COOKIE_SESSION)


def _create_callback_response(user_info: dict, session_id: str) -> RedirectResponse:
    response = RedirectResponse(url=urls.FRONTEND_URL)
    _set_user_cookie(response, _serialize_user_info(user_info))
    _set_session_cookie(response, session_id)
    return response


def _set_user_cookie(response: Response, user_cookie: str):
    response.set_cookie(
        key=COOKIE_USER,
        value=user_cookie,
        httponly=False,
        secure=True,
        samesite='lax',
        max_age=BROWSER_SESSION_TTL,
    )


def _set_session_cookie(response: Response, session_id: str):
    response.set_cookie(
        key=COOKIE_SESSION,
        value=session_id,
        httponly=True,
        secure=True,
        samesite='lax',
        max_age=BROWSER_SESSION_TTL,
    )


def _serialize_user_info(user_info: dict) -> str:
    """Представляем информацию о пользователе в готовый для передачи и чтения на фронте вид:
    
    1. сериализация в json-строку;
    2. кодирование специальных символов;
    3. вставка префикса 'j:' для парсинга react-cookies в объект.
    """

    json_str = json.dumps(user_info)
    json_str = urllib.parse.quote(json_str)
    return f'j:{json_str}'


def _check_code_verifier(code_verifier: str):
    if not code_verifier:
        raise HTTPException(
            status_code=sc.HTTP_400_BAD_REQUEST,
            detail='Authentication failed: missing code verifier'
        )


def _check_callback_args(
    state: Optional[str], code: Optional[str], error: Optional[str],
):
    if error or (not state or not code):
        raise HTTPException(
            status_code=sc.HTTP_400_BAD_REQUEST,
            detail=f'Authentication failed: {error}',
        )


def _check_state(init_state: str | None, client_state: str):
    if init_state:
        if init_state != client_state:
            raise HTTPException(
                status_code=sc.HTTP_403_FORBIDDEN,
                detail=f'Authentication failed: wrong state',
            )
    else:
        raise HTTPException(
            status_code=sc.HTTP_403_FORBIDDEN,
            detail=f'Authentication failed: there are no state cookie',
        )
