from dataclasses import dataclass
from enum import Enum

from a350f_tracker.models import AircraftObservation
from a350f_tracker.detector.rules import (
    CONFIRMATION_COUNT,
    MAX_OBSERVATION_AGE,
    MAX_OBSERVATION_GAP,
)


class FlightState(str, Enum):
    GROUND = "ground"
    AIRBORNE = "airborne"
    UNKNOWN = "unknown"


class FlightEvent(str, Enum):
    TAKEOFF_CONFIRMED = "takeoff_confirmed"
    LANDING_CONFIRMED = "landing_confirmed"


@dataclass(frozen=True)
class StateTransition:
    event: FlightEvent
    previous_state: FlightState
    current_state: FlightState
    observation: AircraftObservation


class FlightStateMachine:
    def __init__(
        self,
        initial_state: FlightState = FlightState.UNKNOWN,
        confirmation_count: int = CONFIRMATION_COUNT,
    ) -> None:
        if confirmation_count < 1:
            raise ValueError("confirmation_count must be >= 1")

        self.state = initial_state
        self.confirmation_count = confirmation_count
        self._candidate_state: FlightState | None = None
        self._candidate_count = 0
        self._last_observation = None

    def update(
        self,
        observation: AircraftObservation,
    ) -> StateTransition | None:
        if not self._is_valid(observation):
            return None

        if self._last_observation is not None:
            gap = (
                observation.observed_at - self._last_observation
            ).total_seconds()

            # Ignore duplicate or out-of-order observations.
            if gap <= 0:
                return None

            # A long gap invalidates the current confirmation sequence.
            if gap > MAX_OBSERVATION_GAP:
                self._reset_candidate()

        self._last_observation = observation.observed_at

        observed_state = self._get_observed_state(observation)

        if observed_state is None:
            self._reset_candidate()
            return None

        # First known observation establishes the initial state.
        if self.state == FlightState.UNKNOWN:
            self.state = observed_state
            return None

        # Observation agrees with current state.
        if observed_state == self.state:
            self._reset_candidate()
            return None

        # Start or continue a transition candidate.
        if observed_state != self._candidate_state:
            self._candidate_state = observed_state
            self._candidate_count = 1
        else:
            self._candidate_count += 1

        if self._candidate_count < self.confirmation_count:
            return None

        previous_state = self.state
        self.state = observed_state
        self._reset_candidate()

        event = (
            FlightEvent.TAKEOFF_CONFIRMED
            if self.state == FlightState.AIRBORNE
            else FlightEvent.LANDING_CONFIRMED
        )

        return StateTransition(
            event=event,
            previous_state=previous_state,
            current_state=self.state,
            observation=observation,
        )

    def _reset_candidate(self) -> None:
        self._candidate_state = None
        self._candidate_count = 0

    @staticmethod
    def _get_observed_state(
        observation: AircraftObservation,
    ) -> FlightState | None:
        if observation.on_ground is True:
            return FlightState.GROUND

        if observation.on_ground is False:
            return FlightState.AIRBORNE

        return None

    @staticmethod
    def _is_valid(observation: AircraftObservation) -> bool:
        from datetime import datetime, timezone

        age = (
            datetime.now(timezone.utc) - observation.observed_at
        ).total_seconds()

        return 0 <= age <= MAX_OBSERVATION_AGE