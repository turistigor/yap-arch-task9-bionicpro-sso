CREATE DATABASE IF NOT EXISTS bionicpro;

/* Таблица для отчетов */

CREATE TABLE IF NOT EXISTS bionicpro.reports (
    id UUID DEFAULT generateUUIDv4(),
    user_id UUID,
    user_name String,
    email String,
    sensor_id String,
    sensor_type String,
    sensor_unit String,
    sensor_serial String,
    value_min Float,
    value_max Float,
    value_avg Float,
    charge_speed Float,
    discharge_speed Float,
    on_time Float,
    off_time Float,
    period DateTime,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY id;


/* Конвейер CDC для таблицы users (пользователи) */

-- Буфер-очередь (читает строго из маленького регистра топика 'users')
CREATE TABLE IF NOT EXISTS bionicpro.users_kafka_queue (raw_message String)
ENGINE = Kafka
SETTINGS kafka_broker_list = 'kafka:29092',
         kafka_topic_list = 'cdc_crm.public.users',
         kafka_group_name = 'ch_users_consumers',
         kafka_format = 'LineAsString';

-- Физическая реплика для хранения истории изменений пользователей
CREATE TABLE IF NOT EXISTS bionicpro.users_replica
(
    id UInt64,
    user_name String,
    email String,
    sensors Array(String),
    updated_at DateTime,
    ch_sign Int8 -- Метка удаления: 1 = активен, -1 = удален
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY id;

-- Легковесный триггер-транспорт для разбора JSON Debezium
CREATE MATERIALIZED VIEW IF NOT EXISTS bionicpro.users_mv TO bionicpro.users_replica AS
WITH 
    JSONExtractString(raw_message, 'payload', 'op') AS operation,
    if(operation = 'd', 
       JSONExtractString(raw_message, 'payload', 'before'), 
       JSONExtractString(raw_message, 'payload', 'after')
    ) AS target_payload
SELECT
    JSONExtractUInt(target_payload, 'id') AS id,
    JSONExtractString(target_payload, 'user_name') AS user_name,
    JSONExtractString(target_payload, 'email') AS email,
    JSONExtract(target_payload, 'sensors', 'Array(String)') AS sensors,
    toDateTime(JSONExtractUInt(raw_message, 'payload', 'ts_ms') / 1000) AS updated_at,
    if(operation = 'd', -1, 1) AS ch_sign
FROM bionicpro.users_kafka_queue;


/* Конвейер CDC для таблицы sensors (датчики) */

-- Буфер-очередь (читает строго из маленького регистра топика 'sensors')
CREATE TABLE IF NOT EXISTS bionicpro.sensors_kafka_queue (raw_message String)
ENGINE = Kafka
SETTINGS kafka_broker_list = 'kafka:29092',
         kafka_topic_list = 'cdc_crm.public.sensors',
         kafka_group_name = 'ch_sensors_consumers',
         kafka_format = 'LineAsString';

-- Физическая реплика для хранения истории изменений датчиков
CREATE TABLE IF NOT EXISTS bionicpro.sensors_replica
(
    id String,
    type String,
    serial String,
    unit String,
    updated_at DateTime,
    ch_sign Int8 -- Метка удаления: 1 = активен, -1 = удален
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY id;

-- Легковесный триггер-транспорт для разбора JSON Debezium
CREATE MATERIALIZED VIEW IF NOT EXISTS bionicpro.sensors_mv TO bionicpro.sensors_replica AS
WITH 
    JSONExtractString(raw_message, 'payload', 'op') AS operation,
    if(operation = 'd', 
       JSONExtractString(raw_message, 'payload', 'before'), 
       JSONExtractString(raw_message, 'payload', 'after')
    ) AS target_payload
SELECT
    JSONExtractString(target_payload, 'id') AS id,
    JSONExtractString(target_payload, 'type') AS type,
    JSONExtractString(target_payload, 'serial') AS serial,
    JSONExtractString(target_payload, 'unit') AS unit,
    toDateTime(JSONExtractUInt(raw_message, 'payload', 'ts_ms') / 1000) AS updated_at,
    if(operation = 'd', -1, 1) AS ch_sign
FROM bionicpro.sensors_kafka_queue;


/* Финальная витрина для выгрузки информации о пользователях*/

CREATE OR REPLACE VIEW bionicpro.reports_mart AS
WITH 
    active_users AS (
        SELECT id, user_name, email, sensors 
        FROM bionicpro.users_replica 
        FINAL 
        WHERE ch_sign = 1
    ),
    active_sensors AS (
        SELECT id, type, serial, unit 
        FROM bionicpro.sensors_replica 
        FINAL 
        WHERE ch_sign = 1
    )
SELECT 
    u.id AS user_id,
    u.user_name,
    u.email,
    sensor_id,
    s.type AS sensor_type,
    s.unit AS sensor_unit,
    s.serial AS sensor_serial
FROM active_users AS u
ARRAY JOIN u.sensors AS sensor_id 
LEFT JOIN active_sensors AS s ON sensor_id = s.id;
