from src.api.healthcheck import healthcheck_router
from src.api.reports import auth_router

__all__ = (
    'healthcheck_router',
    'auth_router',
)
