import logging
from collections import defaultdict
from datetime import date, datetime, time
from typing import Iterable

import clickhouse_connect as clickhouse
from pandas import DataFrame, to_datetime

logger = logging.getLogger(__name__)


def transform_crm_data(crm_data: Iterable[dict]) -> dict:
    result = {}
    for row in crm_data:
        key = (row.pop('user_name'), row.pop('sensor_id'))
        result[key] = row
    return result


def transform_tm_data(tm_data: Iterable[dict]) -> dict:
    agg_data = {}
    for row in tm_data:
        key = (row.pop('user'), row.pop('sensor'))

        if row_measures := agg_data.get(key, {}):
            row_measures['values'].append(row['value'])
            row_measures['charges'].append(row['charge'])
            row_measures['states'].append(row['state'])
            row_measures['times'].append(row['time'])
        else:
            row_measures['values'] = [row['value'],]
            row_measures['charges'] = [row['charge'],]
            row_measures['states'] = [row['state'],]
            row_measures['times'] = [row['time'],]

            agg_data[key] = row_measures

    result = defaultdict(dict)
    for key in agg_data:
        df = DataFrame(agg_data[key])

        stat_names = ('min', 'max', 'mean',)
        stats = df.loc[df['states'] == 'ON', 'values'].agg(stat_names)
        result[key]['value_min'] = stats['min']
        result[key]['value_max'] = stats['max']
        result[key]['value_avg'] = stats['mean']

        df['times'] = to_datetime(df['times'])
        df['charges_diff'] = df.loc[df['states'] == 'ON', 'charges'].diff()
        df['times_diff_on'] = df.loc[df['states'] == 'ON', 'times'].diff()
        df['times_diff_off'] = df.loc[df['states'] == 'OFF', 'times'].diff()

        charge_total = df.loc[(df['charges_diff'] > 0) & (df['states'] == 'ON'), 'charges_diff'].sum()
        discharge_total = df.loc[(df['charges_diff'] <= 0) & (df['states'] == 'ON'), 'charges_diff'].sum()

        charge_secs = df.loc[(df['charges_diff'] > 0) & (df['states'] == 'ON'), 'times_diff_on'].sum().total_seconds()
        discharge_sec = df.loc[(df['charges_diff'] <= 0) & (df['states'] == 'ON'), 'times_diff_on'].sum().total_seconds()

        result[key]['charge_speed'] = charge_total / charge_secs
        result[key]['discharge_speed'] = discharge_total / discharge_sec

        result[key]['on_time'] = df.loc[df['states'] == 'ON', 'times_diff_on'].sum().total_seconds()
        result[key]['off_time'] = df.loc[df['states'] == 'OFF', 'times_diff_off'].sum().total_seconds()

    return result


COLUMN_NAMES = (
    'user_id', 
    'user_name', 
    'email', 
    'sensor_id', 
    'sensor_type', 
    'sensor_serial', 
    'sensor_unit',

    'value_min',
    'value_max',
    'value_avg',

    'charge_speed',
    'discharge_speed',
    'on_time',
    'off_time',
    'period',
)

async def load_report(
    tm_data: dict,
    crm_data: dict,
    olap_conn_str: str,
    olap_table_name: str,
    report_period: date,
):
    report_data = {
        key: tm_data[key] | crm_data[key]
        for key in tm_data.keys() & crm_data.keys()
    }

    report_period_serializable = datetime.combine(report_period, time.min)

    data_to_insert = []
    for (user_name, sensor_id), value in report_data.items():
        data_item = []

        for column_name in COLUMN_NAMES:
            try:
                data_item.append(value[column_name])
            except KeyError:
                if column_name == 'user_name':
                    data_item.append(user_name)
                elif column_name == 'sensor_id':
                    data_item.append(sensor_id)
                elif column_name == 'period':
                    data_item.append(report_period_serializable)
                else:
                    raise

        data_to_insert.append(data_item)

    async with await clickhouse.get_async_client(dsn=olap_conn_str) as olap_db:
        result = await olap_db.insert(
            table=olap_table_name, data=data_to_insert, column_names=COLUMN_NAMES,
        )

    logger.info(f'Rows written to the OLAP DB: {result.written_rows}')
