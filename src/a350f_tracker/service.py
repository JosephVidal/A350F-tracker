from a350f_tracker.detector.state_machine import (
    FlightStateMachine,
    StateTransition,
)
from a350f_tracker.providers.adsbx import AdsbFiProvider
from a350f_tracker.storage.repository import AircraftRepository
from a350f_tracker.config import AircraftConfig

from copy import deepcopy

import logging
import httpx


logger = logging.getLogger(__name__)

class TrackerService:
    def __init__(
        self,
        provider: AdsbFiProvider,
        repository: AircraftRepository,
        aircraft: list[AircraftConfig],
    ) -> None:
        self.provider = provider
        self.repository = repository
        self.aircraft = aircraft

        self.machines: dict[str, FlightStateMachine] = {}

    def initialize(self) -> None:
        """Restore aircraft states from SQLite."""
        states = self.repository.get_all_states()

        for icao_hex, state in states.items():
            self.machines[icao_hex] = FlightStateMachine(
                initial_state=state
            )

    
    def poll(self) -> list[StateTransition]:
        """Fetch observations and detect confirmed transitions."""
        transitions = []

        for aircraft in self.aircraft:
            registration = aircraft.registration

            try:
                observations = self.provider.get_by_registration(
                    registration
                )
            except httpx.HTTPError:
                logger.exception(
                    "ADS-B request failed for registration %s",
                    registration,
                )
                continue

            logger.info(
                "Received %d observations for %s",
                len(observations),
                registration,
            )

            for observation in observations:
                logger.debug(
                    "Aircraft %s: on_ground=%s altitude=%s ft speed=%s kt",
                    observation.registration,
                    observation.on_ground,
                    observation.altitude_ft,
                    observation.ground_speed_kt,
                )

                if observation.icao_hex.lower() != aircraft.icao_hex.lower():
                    logger.warning(
                        "Unexpected ICAO hex for %s: expected=%s received=%s",
                        registration,
                        aircraft.icao_hex,
                        observation.icao_hex,
                    )
                    continue

                machine = self.machines.get(observation.icao_hex)

                if machine is None:
                    machine = FlightStateMachine()
                    self.machines[observation.icao_hex] = machine

                # Sauvegarde de l'état avant modification
                previous_machine = deepcopy(machine)

                transition = machine.update(observation)

                try:
                    self.repository.save_observation_result(
                        observation=observation,
                        state=machine.state,
                        transition=transition,
                    )
                except Exception:
                    self.machines[observation.icao_hex] = previous_machine
                    raise

                if transition is not None:
                    logger.info(
                        "Confirmed event=%s registration=%s icao=%s observed_at=%s",
                        transition.event.value,
                        observation.registration,
                        observation.icao_hex,
                        observation.observed_at.isoformat(),
                    )
                    transitions.append(transition)

        return transitions