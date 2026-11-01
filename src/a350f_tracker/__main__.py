import logging
import time

from a350f_tracker.config import Settings
from a350f_tracker.providers.adsbx import AdsbFiProvider
from a350f_tracker.storage.database import Database
from a350f_tracker.storage.repository import AircraftRepository
from a350f_tracker.service import TrackerService
from a350f_tracker.config import Settings, load_aircraft_config


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    
    aircraft = load_aircraft_config(settings.aircraft_config_path)
    database = Database(settings.database_path)
    database.initialize()

    provider = AdsbFiProvider()
    repository = AircraftRepository(database)

    service = TrackerService(
        provider=provider,
        repository=repository,
        aircraft=aircraft,
    )

    service.initialize()

    logger.info("A350F Tracker started")
    logger.info(
        "Monitoring: %s",
        [item.registration for item in aircraft],
    )
    logger.info(
        "Polling interval: %d seconds",
        settings.polling_interval_seconds,
    )

    try:
        while True:
            transitions = service.poll()

            for transition in transitions:
                logger.info(
                    "Flight event detected: %s (%s)",
                    transition.event.value,
                    transition.observation.icao_hex,
                )

            time.sleep(settings.polling_interval_seconds)

    except KeyboardInterrupt:
        logger.info("Stopping A350F Tracker")


if __name__ == "__main__":
    main()