from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from a350f_tracker.models import AircraftObservation


def test_valid_observation():
    observation = AircraftObservation(
        icao_hex="ABC123",
        registration="F-WXLD",
        latitude=43.6,
        longitude=1.4,
        altitude_ft=3200,
        on_ground=False,
        observed_at=datetime(2026, 10, 31, 10, 42, tzinfo=timezone.utc),
    )

    assert observation.icao_hex == "ABC123"
    assert observation.on_ground is False


def test_invalid_latitude():
    with pytest.raises(ValidationError):
        AircraftObservation(
            icao_hex="ABC123",
            latitude=120,
            observed_at=datetime.now(timezone.utc),
        )


def test_unknown_ground_state_is_allowed():
    observation = AircraftObservation(
        icao_hex="ABC123",
        on_ground=None,
        observed_at=datetime.now(timezone.utc),
    )

    assert observation.on_ground is None
