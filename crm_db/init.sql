CREATE TABLE IF NOT EXISTS Users (
    id SERIAL PRIMARY KEY,
    user_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    sensors VARCHAR(255)[] DEFAULT '{}' NOT NULL
);

CREATE TABLE IF NOT EXISTS Sensors (
    id VARCHAR(255) PRIMARY KEY,
    type VARCHAR(100) NOT NULL,
    serial VARCHAR(100) NOT NULL,
    unit VARCHAR(50) NOT NULL
);

INSERT INTO Users (user_name, email, sensors)
SELECT * FROM (VALUES
    ('prothetic1', 'prothetic1@example.com', ARRAY['temp_1', 'press_1']::VARCHAR(255)[]),
    ('prothetic2', 'prothetic2@example.com', ARRAY['acc_1', 'ang_1']::VARCHAR(255)[]),
    ('prothetic3', 'prothetic3@example.com', ARRAY['emg_1']::VARCHAR(255)[]),
    ('john.doe', 'john@example.com', ARRAY['emg_2']::VARCHAR(255)[]),
    ('alex.johnson', 'alex@example.com', ARRAY['ang_2']::VARCHAR(255)[])
) AS v(user_name, email, sensors)
WHERE NOT EXISTS (SELECT 1 FROM Users);

INSERT INTO Sensors (id, type, serial, unit)
SELECT * FROM (VALUES
    ('temp_1', 'Temperature', 'SN-TEMP-001', '°C'),
    ('press_1', 'Pressure', 'SN-PRES-001', 'kPa'),
    ('acc_1', 'Accelerometer', 'SN-ACC-001', 'm/s²'),
    ('ang_1', 'Angle', 'SN-ANG-001', 'deg'),
    ('emg_1', 'Electromyography', 'SN-EMG-001', 'mV'),
    ('emg_2', 'Electromyography', 'SN-EMG-002', 'mV'),
    ('ang_2', 'Angle', 'SN-ANG-002', 'deg')
) AS v(id, type, serial, unit)
WHERE NOT EXISTS (SELECT 1 FROM Sensors);
