from datetime import date

import aioboto3
import aiobotocore.config

S3_CONFIG = aiobotocore.config.AioConfig(
    s3={'addressing_style': 'path'}
)


def get_s3_key(user_id: str, report_period: date):
    return f'{user_id}/{report_period.isoformat()}.html'


async def check_s3_exists(
    s3_key: str, url: str, access_key: str, secret_key: str, bucket: str,
) -> bool:
    session = aioboto3.Session()
    async with session.client(
        's3',
        endpoint_url=url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        use_ssl=False,
        config=S3_CONFIG,
    ) as s3:
        try:
            response = await s3.head_object(Bucket=bucket, Key=s3_key)
        except Exception as ex:
            return False
        return True


async def save_to_s3(
    s3_key: str, url: str, access_key: str, secret_key: str, bucket: str, content: str,
):
    session = aioboto3.Session()

    async with session.client(
        's3',
        endpoint_url=url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        use_ssl=False,
        config=S3_CONFIG,
    ) as s3:
        await s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=content.encode('utf-8'),
            ContentType='text/html',
        )
