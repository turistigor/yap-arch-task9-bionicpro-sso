from datetime import datetime, timedelta, timezone
from os import environ

from airflow.sdk import dag, task, get_current_context

from crm import get_users_data
from report import load_report, transform_crm_data, transform_tm_data
from telemetry import Influxdb3ClientContext, fill_telemetry_db, get_telemetry

TM_DB_URL = environ.get('TM_DB_URL')
TM_DB_TOKEN_FILE = environ.get('TM_DB_TOKEN_FILE')
TM_DB_ROW_DATA = environ.get('TM_DB_DATA')
TM_DB_NAME = 'bionicpro'
TM_DB_MEASURE_NAME = 'prosthetics'

CRM_CONNECTION_STR = environ.get('CRM_CONNECTION_STR')

OLAP_CONNECTION_STR = environ.get('OLAP_CONNECTION_STR')
OLAP_TABLE_NAME = 'reports'

tz = timezone(timedelta(hours=3))
start_dt = datetime(2026, 6, 3, 0, 0, 0, tzinfo=tz)
DAG_RUN_PERIOD = timedelta(days=1)


@task
async def create_telemetry_db():
    with Influxdb3ClientContext(
        TM_DB_URL, TM_DB_TOKEN_FILE, TM_DB_NAME,
    ) as tm_db_client:

        await fill_telemetry_db(tm_db_client, TM_DB_ROW_DATA, TM_DB_MEASURE_NAME)

@task
async def extract_tm_data():
    end_dt = get_current_context()['data_interval_start']

    with Influxdb3ClientContext(
        TM_DB_URL, TM_DB_TOKEN_FILE, TM_DB_NAME,
    ) as tm_db_client:

        return await get_telemetry(tm_db_client, TM_DB_MEASURE_NAME, end_dt, DAG_RUN_PERIOD)

@task
async def extract_crm_data():
    return await get_users_data(CRM_CONNECTION_STR)


@task
async def create_report(
    tm_data: list[dict],
    crm_data: dict,
    olap_conn_str: str,
    olap_table_name: str,
):
    crm_data_map = transform_crm_data(crm_data)
    telemetry_data_map = transform_tm_data(tm_data)
    start_dt = get_current_context()['data_interval_start'].date()

    await load_report(
        tm_data=telemetry_data_map,
        crm_data=crm_data_map,
        olap_conn_str=olap_conn_str,
        olap_table_name=olap_table_name,
        report_period=start_dt,
    )


@dag(
    schedule=DAG_RUN_PERIOD,
    start_date=start_dt,
    catchup=True,
    is_paused_upon_creation=False,
)
def prosthetic_report_dag():
    tm_db_creation = create_telemetry_db()
    tm_data = extract_tm_data()
    crm_data = extract_crm_data()

    tm_db_creation >> [tm_data, crm_data]

    create_report(
        tm_data=tm_data,
        crm_data=crm_data,
        olap_conn_str=OLAP_CONNECTION_STR,
        olap_table_name=OLAP_TABLE_NAME,
    )


report_dag = prosthetic_report_dag()


if __name__ == '__main__':
    report_dag.test()
