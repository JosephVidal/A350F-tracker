from a350f_tracker.detector.state_machine import (
    FlightStateMachine,
    StateTransition,
)
from a350f_tracker.providers.adsbx import AdsbFiProvider
from a350f_tracker.storage.repository import AircraftRepository


class TrackerService:
    def __init__(
        self,
        provider: AdsbFiProvider,
        repository: AircraftRepository,
        registrations: list[str],
    ) -> None:
        self.provider = provider
        self.repository = repository
        self.registrations = registrations

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

        for registration in self.registrations:
            observations = self.provider.get_by_registration(
                registration
            )

            for observation in observations:
                machine = self.machines.get(observation.icao_hex)

                if machine is None:
                    machine = FlightStateMachine()
                    self.machines[observation.icao_hex] = machine

                transition = machine.update(observation)

                self.repository.save_observation_result(
                    observation=observation,
                    state=machine.state,
                    transition=transition,
                )

                if transition is not None:
                    transitions.append(transition)

        return transitions