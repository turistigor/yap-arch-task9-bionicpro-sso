from typing import Iterable

import clickhouse_connect as clickhouse


async def get_users_data(olap_conn_str: str, olap_db_name: str, users_olap_table: str) -> Iterable[dict]:
    USERS_QUERY = (
        f'SELECT user_id, user_name, email, sensor_id, sensor_type, sensor_serial, sensor_unit '
        f'FROM {olap_db_name}.{users_olap_table};'
    )

    async with await clickhouse.get_async_client(dsn=olap_conn_str) as olap_db:
        result = await olap_db.query(USERS_QUERY)

    return tuple(result.named_results())
