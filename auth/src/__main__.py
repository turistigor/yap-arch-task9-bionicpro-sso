import asyncio as aio
import logging
from contextlib import asynccontextmanager
from os import environ
from typing import AsyncGenerator

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

import src.api.urls as urls
from src.api import auth_router, healthcheck_router
from src.auth import create_keycloak_oid_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv('../.env')

SESSION_SECRET_KEY = environ.get('SESSION_SECRET_KEY')


async def main():
    app = FastAPI(lifespan=lifespan)

    _setup_middleware(app)
    _setup_routers(app)
    server = _create_server(app)

    await server.serve()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.state.keycloak_oid = create_keycloak_oid_client()

    yield


def _setup_middleware(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=(urls.FRONTEND_URL,),
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    app.add_middleware(
        SessionMiddleware, secret_key=SESSION_SECRET_KEY,
    )


def _setup_routers(app: FastAPI):
    app.include_router(prefix='/api/v1', router=auth_router)
    app.include_router(prefix='/api/v1', router=healthcheck_router)


def _create_server(app: FastAPI) -> uvicorn.Server:
    port = int(environ.get('AUTH_PORT', 8000))

    config = uvicorn.Config(app, host='0.0.0.0', port=port, log_level='info')
    return uvicorn.Server(config)


if __name__ == '__main__':
    aio.run(main())
