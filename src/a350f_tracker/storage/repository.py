from datetime import datetime, timezone

from a350f_tracker.models import AircraftObservation
from a350f_tracker.detector.state_machine import (
    FlightEvent,
    FlightState,
    StateTransition,
)

from a350f_tracker.storage.database import Database


class AircraftRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get_state(self, icao_hex: str) -> FlightState | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """--sql
                SELECT state
                FROM aircraft_states
                WHERE icao_hex = ?
                """,
                (icao_hex,),
            ).fetchone()

        if row is None:
            return None

        return FlightState(row["state"])

    def save_observation(
        self,
        observation: AircraftObservation,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """--sql
                INSERT INTO observations (
                    icao_hex,
                    observed_at,
                    on_ground,
                    latitude,
                    longitude,
                    altitude_ft,
                    ground_speed_kt,
                    vertical_rate_fpm
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(icao_hex) DO UPDATE SET
                    observed_at = excluded.observed_at,
                    on_ground = excluded.on_ground,
                    latitude = excluded.latitude,
                    longitude = excluded.longitude,
                    altitude_ft = excluded.altitude_ft,
                    ground_speed_kt = excluded.ground_speed_kt,
                    vertical_rate_fpm = excluded.vertical_rate_fpm
                WHERE excluded.observed_at > observations.observed_at
                """,
                (
                    observation.icao_hex,
                    observation.observed_at.isoformat(),
                    (
                        int(observation.on_ground)
                        if observation.on_ground is not None
                        else None
                    ),
                    observation.latitude,
                    observation.longitude,
                    observation.altitude_ft,
                    observation.ground_speed_kt,
                    observation.vertical_rate_fpm,
                ),
            )

    def save_transition(
        self,
        transition: StateTransition,
    ) -> int:
        observation = transition.observation
        now = datetime.now(timezone.utc).isoformat()

        event_type = transition.event.value

        with self.database.connect() as connection:
            connection.execute(
                """--sql
                INSERT INTO aircraft_states (
                    icao_hex,
                    registration,
                    state,
                    last_observed_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(icao_hex) DO UPDATE SET
                    registration = excluded.registration,
                    state = excluded.state,
                    last_observed_at = excluded.last_observed_at,
                    updated_at = excluded.updated_at
                """,
                (
                    observation.icao_hex,
                    observation.registration or "",
                    transition.current_state.value,
                    observation.observed_at.isoformat(),
                    now,
                ),
            )

            cursor = connection.execute(
                """--sql
                INSERT INTO flight_events (
                    icao_hex,
                    registration,
                    event_type,
                    occurred_at,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    observation.icao_hex,
                    observation.registration or "",
                    event_type,
                    observation.observed_at.isoformat(),
                    now,
                ),
            )

            event_id = cursor.lastrowid

            connection.execute(
                """--sql
                INSERT INTO outbox (event_id, created_at)
                VALUES (?, ?)
                """,
                (event_id, now),
            )

            return event_id
        
    def get_all_states(self) -> dict[str, FlightState]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT icao_hex, state FROM aircraft_states"
            ).fetchall()

        return {
            row["icao_hex"]: FlightState(row["state"])
            for row in rows
        }
    
    
    def save_initial_state(
        self,
        observation: AircraftObservation,
        state: FlightState,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()

        with self.database.connect() as connection:
            connection.execute(
                """--sql
                INSERT INTO aircraft_states (
                    icao_hex,
                    registration,
                    state,
                    last_observed_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(icao_hex) DO UPDATE SET
                    registration = excluded.registration,
                    state = excluded.state,
                    last_observed_at = excluded.last_observed_at,
                    updated_at = excluded.updated_at
                """,
                (
                    observation.icao_hex,
                    observation.registration or "",
                    state.value,
                    observation.observed_at.isoformat(),
                    now,
                ),
            )

    def save_observation_result(
        self,
        observation: AircraftObservation,
        state: FlightState,
        transition: StateTransition | None = None,
    ) -> int | None:
        now = datetime.now(timezone.utc).isoformat()

        with self.database.connect() as connection:
            # Save the latest observation.
            connection.execute(
                """--sql
                INSERT INTO observations (
                    icao_hex, observed_at, on_ground, latitude,
                    longitude, altitude_ft, ground_speed_kt,
                    vertical_rate_fpm
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(icao_hex) DO UPDATE SET
                    observed_at = excluded.observed_at,
                    on_ground = excluded.on_ground,
                    latitude = excluded.latitude,
                    longitude = excluded.longitude,
                    altitude_ft = excluded.altitude_ft,
                    ground_speed_kt = excluded.ground_speed_kt,
                    vertical_rate_fpm = excluded.vertical_rate_fpm
                WHERE excluded.observed_at > observations.observed_at
                """,
                (
                    observation.icao_hex,
                    observation.observed_at.isoformat(),
                    int(observation.on_ground)
                    if observation.on_ground is not None else None,
                    observation.latitude,
                    observation.longitude,
                    observation.altitude_ft,
                    observation.ground_speed_kt,
                    observation.vertical_rate_fpm,
                ),
            )

            # Persist the current state.
            connection.execute(
                """--sql
                INSERT INTO aircraft_states (
                    icao_hex, registration, state,
                    last_observed_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(icao_hex) DO UPDATE SET
                    registration = excluded.registration,
                    state = excluded.state,
                    last_observed_at = excluded.last_observed_at,
                    updated_at = excluded.updated_at
                """,
                (
                    observation.icao_hex,
                    observation.registration or "",
                    state.value,
                    observation.observed_at.isoformat(),
                    now,
                ),
            )

            if transition is None:
                return None

            # Create the confirmed event.
            cursor = connection.execute(
                """--sql
                INSERT INTO flight_events (
                    icao_hex, registration, event_type,
                    occurred_at, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    observation.icao_hex,
                    observation.registration or "",
                    transition.event.value,
                    observation.observed_at.isoformat(),
                    now,
                ),
            )

            event_id = cursor.lastrowid

            # Add it to the publishing queue.
            connection.execute(
                """--sql
                INSERT INTO outbox (event_id, created_at)
                VALUES (?, ?)
                """,
                (event_id, now),
            )

            return event_id