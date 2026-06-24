"""
Dummy application for Docker Compose validation.

Purpose:
- Read database configuration from environment variables.
- Read Docker Secret from mounted file.
- Test MySQL connectivity.
- Expose HTTP endpoint.
"""

import os
from flask import Flask
import mysql.connector

app = Flask(__name__)


def read_secret(secret_env):
    """
    Read secret content from Docker secret file.

    Args:
        secret_env (str): Environment variable
                          containing secret path.

    Returns:
        str: Secret content.
    """

    secret_path = os.getenv(secret_env)

    if secret_path is None:
        return ""

    with open(secret_path, "r") as file:
        return file.read().strip()


def check_database():
    """
    Attempt database connection.

    Returns:
        tuple(bool, str): Status and message.
    """

    try:

        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USER"),
            password=read_secret("DB_PASSWORD_FILE"),
            database=os.getenv("DB_NAME")
        )

        if connection.is_connected():
            connection.close()
            return True, "Database connected"

    except mysql.connector.Error as error:
        return False, str(error)

    return False, "Unknown error"


@app.route("/")
def home():
    """
    Main endpoint.
    """

    db_status, message = check_database()

    return {
        "service": "dummy-python-app",
        "python_version": "3.11",
        "database_status": db_status,
        "message": message
    }


@app.route("/health")
def health():
    """
    Health endpoint.
    """

    return {"status": "UP"}


if __name__ == "__main__":

    app.run(host="0.0.0.0", port=8000)