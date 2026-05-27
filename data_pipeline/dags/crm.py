from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


CRM_DATA_QUERY = '''
    SELECT 
        u.id AS user_id, 
        u.user_name, 
        u.email, 
        s.id AS sensor_id,
        s.type AS sensor_type, 
        s.serial AS sensor_serial, 
        s.unit AS sensor_unit
    FROM Users u
    LEFT JOIN Sensors s ON s.id = ANY(u.sensors);
'''


async def get_users_data(crm_db_conn_str: str) -> dict:
    db_engine = create_async_engine(crm_db_conn_str)

    async with db_engine.connect() as db_conn:
        result = await db_conn.execute(text(CRM_DATA_QUERY))

    return [dict(row) for row in result.mappings()]
