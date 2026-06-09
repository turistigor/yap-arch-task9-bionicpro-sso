#!/bin/sh

echo "Waiting for Debezium to start..."
until curl -s -o /dev/null -w "%{http_code}" http://cdc:8083/connectors | grep -q "200"; do
  sleep 2
done

echo "Debezium is up! Registering PostgreSQL connector for Users and Sensors..."

curl -X POST http://cdc:8083/connectors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "crm-postgres-connector",
    "config": {
      "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
      "tasks.max": "1",
      "plugin.name": "pgoutput",
      "database.hostname": "crm_db",
      "database.port": "5432",
      "database.user": "crm_user",
      "database.password": "crm_password",
      "database.dbname": "crm_db",
      "topic.prefix": "cdc_crm",
      "table.include.list": "public.Users,public.Sensors"
    }
  }'

echo -e "\nConnector successfully registered!"