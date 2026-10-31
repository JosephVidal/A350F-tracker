import sqlite3
from pathlib import Path


SCHEMA = """--sql
CREATE TABLE IF NOT EXISTS aircraft_states (
    icao_hex TEXT PRIMARY KEY,
    registration TEXT NOT NULL,
    state TEXT NOT NULL,
    last_observed_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS observations (
    icao_hex TEXT PRIMARY KEY,
    observed_at TEXT NOT NULL,
    on_ground INTEGER,
    latitude REAL,
    longitude REAL,
    altitude_ft REAL,
    ground_speed_kt REAL,
    vertical_rate_fpm REAL
);

CREATE TABLE IF NOT EXISTS flight_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    icao_hex TEXT NOT NULL,
    registration TEXT NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (icao_hex, event_type, occurred_at)
);

CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    published_at TEXT,
    FOREIGN KEY (event_id) REFERENCES flight_events(id)
);

CREATE INDEX IF NOT EXISTS idx_observations_aircraft
ON observations (icao_hex, observed_at);

CREATE INDEX IF NOT EXISTS idx_outbox_status
ON outbox (status);
"""


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)