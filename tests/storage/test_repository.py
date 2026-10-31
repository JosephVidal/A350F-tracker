import sqlite3
import pytest

from datetime import datetime, timezone

from a350f_tracker.models import AircraftObservation
from a350f_tracker.detector.state_machine import (
    FlightEvent,
    FlightState,
    StateTransition,
)
from a350f_tracker.storage.database import Database
from a350f_tracker.storage.repository import AircraftRepository


def make_observation():
    return AircraftObservation(
        icao_hex="39a53b",
        registration="F-WXLD",
        aircraft_type="A35K",
        on_ground=False,
        observed_at=datetime.now(timezone.utc),
    )


def test_get_state_returns_none_when_aircraft_is_unknown(tmp_path):
    repository = AircraftRepository(Database(tmp_path / "test.db"))
    repository.database.initialize()

    assert repository.get_state("39a53b") is None


def test_save_and_get_state(tmp_path):
    database = Database(tmp_path / "test.db")
    database.initialize()
    repository = AircraftRepository(database)

    observation = make_observation()

    transition = StateTransition(
        event=FlightEvent.TAKEOFF_CONFIRMED,
        previous_state=FlightState.GROUND,
        current_state=FlightState.AIRBORNE,
        observation=observation,
    )

    repository.save_transition(transition)

    assert repository.get_state("39a53b") == FlightState.AIRBORNE


def test_save_transition_creates_event_and_outbox(tmp_path):
    database = Database(tmp_path / "test.db")
    database.initialize()
    repository = AircraftRepository(database)

    transition = StateTransition(
        event=FlightEvent.TAKEOFF_CONFIRMED,
        previous_state=FlightState.GROUND,
        current_state=FlightState.AIRBORNE,
        observation=make_observation(),
    )

    event_id = repository.save_transition(transition)

    with database.connect() as connection:
        event = connection.execute(
            "SELECT * FROM flight_events WHERE id = ?",
            (event_id,),
        ).fetchone()

        outbox = connection.execute(
            "SELECT * FROM outbox WHERE event_id = ?",
            (event_id,),
        ).fetchone()

    assert event is not None
    assert event["event_type"] == "takeoff_confirmed"
    assert outbox is not None
    assert outbox["status"] == "pending"


def test_save_observation(tmp_path):
    database = Database(tmp_path / "test.db")
    database.initialize()
    repository = AircraftRepository(database)

    observation = make_observation()
    repository.save_observation(observation)

    with database.connect() as connection:
        row = connection.execute(
            "SELECT * FROM observations WHERE icao_hex = ?",
            ("39a53b",),
        ).fetchone()

    assert row is not None
    assert row["on_ground"] == 0


def test_save_observation_does_not_replace_newer_observation(tmp_path):
    database = Database(tmp_path / "test.db")
    database.initialize()
    repository = AircraftRepository(database)

    older = make_observation()
    newer = older.model_copy(
        update={
            "observed_at": datetime.now(timezone.utc),
            "altitude_ft": 35000,
        }
    )

    repository.save_observation(newer)
    repository.save_observation(older)

    with database.connect() as connection:
        row = connection.execute(
            "SELECT altitude_ft FROM observations WHERE icao_hex = ?",
            ("39a53b",),
        ).fetchone()

    assert row["altitude_ft"] == 35000


def test_failed_transition_rolls_back_all_writes(tmp_path):
    database = Database(tmp_path / "test.db")
    database.initialize()
    repository = AircraftRepository(database)

    observation = make_observation()

    transition = StateTransition(
        event=FlightEvent.TAKEOFF_CONFIRMED,
        previous_state=FlightState.GROUND,
        current_state=FlightState.AIRBORNE,
        observation=observation,
    )

    with pytest.raises(sqlite3.IntegrityError):
        with database.connect() as connection:
            connection.execute(
                """
                CREATE TRIGGER reject_outbox
                BEFORE INSERT ON outbox
                BEGIN
                    SELECT RAISE(ABORT, 'simulated failure');
                END;
                """
            )

        repository.save_observation_result(
            observation,
            FlightState.AIRBORNE,
            transition,
        )

    with database.connect() as connection:
        state = connection.execute(
            "SELECT * FROM aircraft_states"
        ).fetchall()

        events = connection.execute(
            "SELECT * FROM flight_events"
        ).fetchall()

        observations = connection.execute(
            "SELECT * FROM observations"
        ).fetchall()

    assert state == []
    assert events == []
    assert observations == []
