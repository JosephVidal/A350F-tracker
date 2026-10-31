from datetime import datetime, timezone

import httpx

from a350f_tracker.models import AircraftObservation


BASE_URL = "https://opendata.adsb.fi/api/v2"


class AdsbFiProvider:
    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def get_by_registration(
        self, registration: str
    ) -> list[AircraftObservation]:
        url = f"{BASE_URL}/registration/{registration}"

        response = httpx.get(url, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()

        observations = []

        for aircraft in payload.get("ac", []):
            altitude = aircraft.get("alt_baro")

            # L'API peut renvoyer "ground" ou une altitude numérique.
            altitude_ft = (
                float(altitude)
                if isinstance(altitude, (int, float))
                else None
            )

            seen = aircraft.get("seen")
            observed_at = datetime.now(timezone.utc)

            if isinstance(seen, (int, float)):
                from datetime import timedelta

                observed_at -= timedelta(seconds=seen)

            observations.append(
                AircraftObservation(
                    icao_hex=aircraft["hex"],
                    registration=aircraft.get("r"),
                    aircraft_type=aircraft.get("t"),
                    latitude=aircraft.get("lat"),
                    longitude=aircraft.get("lon"),
                    altitude_ft=altitude_ft,
                    ground_speed_kt=aircraft.get("gs"),
                    vertical_rate_fpm=aircraft.get("baro_rate"),
                    on_ground=(
                        True
                        if altitude == "ground"
                        else aircraft.get("gnd")
                    ),
                    observed_at=observed_at,
                )
            )

        return observations
