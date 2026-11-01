from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from a350f_tracker.config import AircraftConfig
from a350f_tracker.detector.state_machine import (
    FlightState,
    FlightStateMachine,
)
from a350f_tracker.models import AircraftObservation
from a350f_tracker.service import TrackerService


class FakeProvider:
    def __init__(self, observation):
        self.observation = observation

    def get_by_registration(self, registration):
        return [self.observation]


class FakeRepository:
    def get_all_states(self):
        return {}

    def save_observation_result(self, **kwargs):
        raise RuntimeError("Simulated database failure")


def test_poll_restores_machine_if_persistence_fails():
    now = datetime.now(timezone.utc)

    # La machine a déjà confirmé que l'avion est au sol.
    machine = FlightStateMachine(
        initial_state=FlightState.GROUND
    )

    # Première observation en vol : elle démarre une transition candidate.
    first_airborne = AircraftObservation(
        icao_hex="ABC123",
        registration="F-WXLD",
        observed_at=now - timedelta(seconds=2),
        on_ground=False,
    )

    assert machine.update(first_airborne) is None

    # On conserve une copie complète de la machine avant le prochain traitement.
    previous_machine = deepcopy(machine)

    # Cette observation provoquera une erreur de persistance.
    failing_observation = AircraftObservation(
        icao_hex="ABC123",
        registration="F-WXLD",
        observed_at=now,
        on_ground=False,
    )

    aircraft = [
        AircraftConfig(
            registration="F-WXLD",
            icao_hex="abc123",
            msn=700,
            model="A350F",
            operator="Airbus",
        )
    ]

    provider = FakeProvider(failing_observation)
    repository = FakeRepository()

    service = TrackerService(
        provider=provider,
        repository=repository,
        aircraft=aircraft,
    )

    service.machines["ABC123"] = machine

    # L'erreur de persistance doit remonter.
    with pytest.raises(
        RuntimeError,
        match="Simulated database failure",
    ):
        service.poll()

    # La machine doit avoir retrouvé son état complet précédent.
    restored_machine = service.machines["ABC123"]

    assert restored_machine.state == previous_machine.state
    assert restored_machine._candidate_state == previous_machine._candidate_state
    assert restored_machine._candidate_count == previous_machine._candidate_count
    assert restored_machine._last_observation == previous_machine._last_observation