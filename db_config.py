import os
import re

import mysql.connector


def load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.isfile(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


load_env_file()


def _required_setting(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required database environment variable: {name}")
    return value


DB_HOST = _required_setting("DB_HOST")
DB_USER = _required_setting("DB_USER")
DB_NAME = _required_setting("DB_NAME")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
try:
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
except ValueError as error:
    raise RuntimeError("DB_PORT must be a valid TCP port number.") from error

if not 1 <= DB_PORT <= 65535:
    raise RuntimeError("DB_PORT must be between 1 and 65535.")
if not re.fullmatch(r"[A-Za-z0-9_]+", DB_NAME):
    raise RuntimeError("DB_NAME may contain only letters, numbers, and underscores.")


PREDICTION_COLUMNS = {
    "username": "VARCHAR(50)",
    "nitrogen": "FLOAT",
    "phosphorus": "FLOAT",
    "potassium": "FLOAT",
    "temperature": "FLOAT",
    "humidity": "FLOAT",
    "ph_value": "FLOAT",
    "rainfall": "FLOAT",
    "crop_name": "VARCHAR(50)",
}


def ensure_prediction_columns(cursor):
    cursor.execute("SHOW COLUMNS FROM crop_predictions")
    existing_columns = {column[0] for column in cursor.fetchall()}
    for column_name, column_type in PREDICTION_COLUMNS.items():
        if column_name not in existing_columns:
            cursor.execute(
                f"ALTER TABLE crop_predictions ADD COLUMN {column_name} {column_type}"
            )


def get_mysql_connection(include_database=True):
    connection_options = {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "connection_timeout": 10,
    }
    if include_database:
        connection_options["database"] = DB_NAME
    return mysql.connector.connect(**connection_options)
