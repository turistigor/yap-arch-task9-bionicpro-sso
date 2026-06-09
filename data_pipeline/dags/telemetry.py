import json
import logging
from datetime import datetime, timedelta

import pyarrow.compute as pc
from influxdb_client_3 import InfluxDBClient3, InfluxDB3ClientQueryError

logger = logging.getLogger(__name__)


class TelemetryDBError(Exception):
    """Ошибки при работе с Telemetry DB"""


class Influxdb3ClientContext:
    def __init__(self, url: str, token_file: str, database: str):
        self._url = url
        self._token_file = token_file
        self._database = database
        
        self._client = None

    def __enter__(self) -> InfluxDBClient3:
        self._client = self._get_tm_db_client()
        return self._client

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            self._client.flush()
            self._client.close()

    def _get_tm_db_client(self) -> InfluxDBClient3:
        token = self._get_tm_db_token()
        return InfluxDBClient3(
            host=self._url, token=token, database=self._database,
        )
    
    def _get_tm_db_token(self) -> str:
        with open(self._token_file) as token_file:
            content = json.load(token_file)
            return content['token']


async def fill_telemetry_db(
    tm_db_client: InfluxDBClient3, tm_data_path: str, measure_name: str,
):
    if await _db_empty(tm_db_client, measure_name) is True:
        tm_db_client.write_file(
            file=tm_data_path,
            measurement_name=measure_name,
            tag_columns=('user', 'sensor'),
            timestamp_column='timestamp',
        )
        logger.info('Telemetry DB has been initialized by data')
    else:
        logger.info('Telemetry DB is not empty')


async def get_telemetry(
    tm_db_client: InfluxDBClient3,
    measure_name: str,
    end_dt: datetime,
    period: timedelta,
) -> list[dict]:
    end_period = int(end_dt.timestamp() * 1e9)
    start_period = int(end_period - period.total_seconds() * 1e9)

    try:
        response = await tm_db_client.query_async(
            f'SELECT * FROM {measure_name} '
            f'WHERE time>to_timestamp_nanos({start_period}) AND time<to_timestamp_nanos({end_period}) '
            f'ORDER BY time',
        )
    except InfluxDB3ClientQueryError as ex:
        raise TelemetryDBError(
            f'New telemetry reading error'
        ) from ex

    iso_time_column = pc.strftime(response['time'], format='%Y-%m-%dT%H:%M:%SZ')
    
    optimized_table = response.set_column(
        response.schema.get_field_index('time'), 
        'time', 
        iso_time_column,
    )

    return optimized_table.to_pylist()


async def _db_empty(tm_db_client: InfluxDBClient3, measure_name: str) -> bool:
    try:
        response = await tm_db_client.query_async(f'SELECT COUNT(*) FROM {measure_name}')
    except InfluxDB3ClientQueryError:
        return True

    rows_count = response.to_pydict()['count(*)'][0]
    return False if rows_count > 0 else True
