from os import environ

AUTH_PORT = environ.get('AUTH_PORT')
AUTH_HOST = environ.get('AUTH_HOST')
AUTH_CALLBACK_URL = f'http://{AUTH_HOST}:{AUTH_PORT}/api/v1/auth/callback'
AUTH_LOGIN_URL = f'http://{AUTH_HOST}:{AUTH_PORT}/api/v1/auth/login'
FRONTEND_URL = environ.get('FRONTEND_URL', 'http://localhost:3000')