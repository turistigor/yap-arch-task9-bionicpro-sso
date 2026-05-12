from os import environ
from urllib.parse import urlparse


def get_redis_url() -> str:
    redis_url = environ.get('REDIS_URL', 'http://redis:6379')
    parse_result = urlparse(redis_url)

    password = environ['REDIS_PASSWORD']
    username = 'default'

    return (
        f'{parse_result.scheme}://'
        f'{username}:'
        f'{password}@'
        f'{parse_result.hostname}:'
        f'{parse_result.port}'
    )
