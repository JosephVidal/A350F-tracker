
import sqlite3

from a350f_tracker.storage.database import Database


def test_database_initialization(tmp_path):
    db_path = tmp_path / "test.db"
    database = Database(db_path)

    database.initialize()

    assert db_path.exists()

    with database.connect() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert {
        "aircraft_states",
        "observations",
        "flight_events",
        "outbox",
    }.issubset(tables)


def test_database_initialization_is_idempotent(tmp_path):
    database = Database(tmp_path / "test.db")

    database.initialize()
    database.initialize()

    with database.connect() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
        ).fetchone()[0]

    assert count >= 4


def test_foreign_keys_are_enabled(tmp_path):
    database = Database(tmp_path / "test.db")
    database.initialize()

    with database.connect() as connection:
        result = connection.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0]

    assert result == 1
