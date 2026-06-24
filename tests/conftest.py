"""
Pytest fixtures and test configuration.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ============================================================
# Project paths
# ============================================================

ROOT_DIR: Path = Path(__file__).resolve().parents[1]

APP_DIR: Path = ROOT_DIR / "app"
SRC_DIR: Path = APP_DIR / "src"


# Add root project directory to Python import path
sys.path.insert(0, str(ROOT_DIR))


# Import Flask application
from src.main import app   # noqa: E402


# ============================================================
# Flask client fixture
# ============================================================

@pytest.fixture(scope="session")
def client():
    """
    Create Flask test client.
    """

    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


# ============================================================
# Environment isolation
# ============================================================

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """
    Mock environment variables.
    """

    monkeypatch.setenv(
        "DB_HOST",
        "localhost"
    )

    monkeypatch.setenv(
        "DB_PORT",
        "3306"
    )

    monkeypatch.setenv(
        "DB_NAME",
        "test_db"
    )

    monkeypatch.setenv(
        "DB_USER",
        "test_user"
    )

    monkeypatch.setenv(
        "DB_PASSWORD_FILE",
        "/tmp/fake_secret"
    )


# ============================================================
# Mock database connection
# ============================================================

@pytest.fixture(autouse=True)
def mock_db_connection():
    """
    Mock MySQL connection.
    """

    with patch(
        "src.main.mysql.connector.connect"
    ) as mock:

        mock_connection = mock.return_value
        mock_connection.is_connected.return_value = True

        yield mock_connection
        

# ============================================================
# Mock external dependencies
# ============================================================

@pytest.fixture(autouse=True)
def mock_dependencies():
    """
    Mock external dependencies.

    Purpose:
    - Avoid real database connections
    - Avoid reading Docker secrets
    """

    with patch(
        "src.main.mysql.connector.connect"
    ) as mock_db, patch(
        "src.main.read_secret"
    ) as mock_secret:

        # Simulate valid database connection
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = True

        mock_db.return_value = mock_connection

        # Simulate Docker secret content
        mock_secret.return_value = "fake_password"

        yield