CREATE DATABASE IF NOT EXISTS bionicpro;

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
