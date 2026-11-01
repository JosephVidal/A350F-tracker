from a350f_tracker.config import (
    AircraftConfig,
    load_aircraft_config,
)


def test_load_aircraft_config(tmp_path):
    config_file = tmp_path / "aircraft.yaml"

    config_file.write_text(
        """
aircraft:
  - registration: F-WXLD
    icao_hex: "39a53b"
    msn: 700
    model: A350F
    operator: Airbus
    enabled: true
  - registration: F-TEST
    icao_hex: "abcdef"
    msn: 701
    model: A350F
    operator: Airbus
    enabled: false
""",
        encoding="utf-8",
    )

    aircraft = load_aircraft_config(config_file)

    assert len(aircraft) == 1
    assert isinstance(aircraft[0], AircraftConfig)
    assert aircraft[0].registration == "F-WXLD"
    assert aircraft[0].icao_hex == "39a53b"
    assert aircraft[0].msn == 700