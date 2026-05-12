from datetime import datetime

import starlette.status as sc
from fastapi import APIRouter, Response


healthcheck_router = APIRouter()


@healthcheck_router.api_route(path='/healthcheck')
async def healthcheck():
    now = datetime.now()
    return Response(content=f'OK: {now}', status_code=sc.HTTP_200_OK)