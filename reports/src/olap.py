from datetime import date

import clickhouse_connect as clickhouse
from pandas import DataFrame

async def get_report_data(
    olap_conn_str: str, olap_table_name: str, user_name: str, period: date,
) -> DataFrame:
    USER_SENSORS_QUERY = (
        f"SELECT sensor_id,sensor_type,sensor_serial,value_min,value_max,value_avg,charge_speed,discharge_speed,on_time,off_time "
        f"FROM '{olap_table_name}' WHERE user_name='{user_name}' AND period='{str(period)}' LIMIT 100"
    )

    async with await clickhouse.get_async_client(dsn=olap_conn_str) as olap_db:
        user_data = await olap_db.query_df(USER_SENSORS_QUERY)

    return _transform_user_data(user_data)


def _transform_user_data(user_data: DataFrame) -> DataFrame:
    if user_data.empty:
        return user_data

    return user_data.groupby('sensor_id').agg({
        'sensor_type': 'first',
        'sensor_serial': 'first',
        'value_min': 'min',
        'value_max': 'max',
        'value_avg': 'mean',
        'charge_speed': 'mean',
        'discharge_speed': 'mean',
        'on_time': 'sum',
        'off_time': 'sum',
    })


    