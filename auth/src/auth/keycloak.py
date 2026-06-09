from os import environ

from keycloak import KeycloakOpenID
from keycloak.pkce_utils import generate_code_challenge, generate_code_verifier

KEYCLOAK_URL = environ.get('KEYCLOAK_URL', 'http://localhost:8080/')
REALM_NAME = 'reports-realm'
CLIENT_ID = 'reports-frontend'

PKCE_METHOD = 'S256'


def create_keycloak_oid_client() -> KeycloakOpenID:
    return KeycloakOpenID(
        server_url=KEYCLOAK_URL,
        realm_name=REALM_NAME,
        client_id=CLIENT_ID,
    )


def generate_pkce_code_verifier() -> str:
    return generate_code_verifier()


def generate_pkce_code_challenge(code_verifier: str) -> tuple[str, str]:
    return generate_code_challenge(code_verifier, PKCE_METHOD)
