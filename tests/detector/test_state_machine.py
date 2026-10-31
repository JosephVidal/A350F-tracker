from datetime import datetime, timedelta, timezone

import pytest

from a350f_tracker.models import AircraftObservation
from a350f_tracker.detector.state_machine import (
    FlightEvent,
    FlightState,
    FlightStateMachine,
)


def make_observation(on_ground, seconds_ago=0):
    return AircraftObservation(
        icao_hex="39a53b",
        registration="F-WXLD",
        aircraft_type="A35K",
        on_ground=on_ground,
        observed_at=datetime.now(timezone.utc)
        - timedelta(seconds=seconds_ago),
    )


def test_initial_state_is_unknown():
    machine = FlightStateMachine()

    assert machine.state == FlightState.UNKNOWN


def test_first_observation_establishes_ground_state():
    machine = FlightStateMachine()

    machine.update(make_observation(True))

    assert machine.state == FlightState.GROUND


def test_takeoff_requires_three_observations():
    machine = FlightStateMachine(initial_state=FlightState.GROUND)

    assert machine.update(make_observation(False)) is None
    assert machine.update(make_observation(False)) is None

    transition = machine.update(make_observation(False))

    assert transition is not None
    assert transition.event == FlightEvent.TAKEOFF_CONFIRMED
    assert machine.state == FlightState.AIRBORNE


def test_landing_requires_three_observations():
    machine = FlightStateMachine(initial_state=FlightState.AIRBORNE)

    assert machine.update(make_observation(True)) is None
    assert machine.update(make_observation(True)) is None

    transition = machine.update(make_observation(True))

    assert transition is not None
    assert transition.event == FlightEvent.LANDING_CONFIRMED
    assert machine.state == FlightState.GROUND


def test_candidate_is_reset_when_observation_matches_current_state():
    machine = FlightStateMachine(initial_state=FlightState.GROUND)

    machine.update(make_observation(False))
    machine.update(make_observation(False))
    machine.update(make_observation(True))

    assert machine.state == FlightState.GROUND

    # Three new airborne observations are required.
    assert machine.update(make_observation(False)) is None
    assert machine.update(make_observation(False)) is None
    assert machine.update(make_observation(False)) is not None


def test_unknown_observation_does_not_trigger_transition():
    machine = FlightStateMachine(initial_state=FlightState.GROUND)

    machine.update(make_observation(None))
    machine.update(make_observation(None))
    machine.update(make_observation(None))

    assert machine.state == FlightState.GROUND


def test_stale_observation_is_ignored():
    machine = FlightStateMachine(initial_state=FlightState.GROUND)

    result = machine.update(make_observation(False, seconds_ago=120))

    assert result is None
    assert machine.state == FlightState.GROUND


def test_confirmation_count_must_be_positive():
    with pytest.raises(ValueError):
        FlightStateMachine(confirmation_count=0)
        

def test_duplicate_observation_is_ignored():
    machine = FlightStateMachine(initial_state=FlightState.GROUND)

    observation = make_observation(False)

    assert machine.update(observation) is None
    assert machine.update(observation) is None

    # The duplicate must not count as a second observation.
    assert machine._candidate_count == 1


def test_out_of_order_observation_is_ignored():
    machine = FlightStateMachine(initial_state=FlightState.GROUND)

    base_time = datetime.now(timezone.utc) - timedelta(seconds=20)

    first = make_observation(False)
    first = first.model_copy(update={"observed_at": base_time})

    older = make_observation(False)
    older = older.model_copy(
        update={"observed_at": base_time - timedelta(seconds=5)}
    )

    latest = make_observation(False)
    latest = latest.model_copy(
        update={"observed_at": base_time + timedelta(seconds=10)}
    )

    machine.update(first)
    machine.update(older)

    assert machine._candidate_count == 1

    machine.update(latest)

    assert machine._candidate_count == 2


def test_long_gap_resets_confirmation_sequence():
    machine = FlightStateMachine(initial_state=FlightState.GROUND)

    base_time = datetime.now(timezone.utc) - timedelta(seconds=20)

    first = make_observation(False)
    first = first.model_copy(update={"observed_at": base_time})

    second = make_observation(False)
    second = second.model_copy(
        update={"observed_at": base_time + timedelta(seconds=91)}
    )

    machine.update(first)
    machine.update(second)

    # The second observation starts a new sequence.
    assert machine._candidate_count == 1
    assert machine.state == FlightState.GROUND
