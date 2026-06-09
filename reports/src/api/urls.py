from os import environ

AUTH_HOST = environ.get('AUTH_HOST')
AUTH_PORT = environ.get('AUTH_PORT')
AUTH_URL = f'http://{AUTH_HOST}:{AUTH_PORT}'
USER_INFO_URL = f'{AUTH_URL}/api/v1/auth/me'

FRONTEND_URL = environ.get('FRONTEND_URL', 'http://localhost:3000')