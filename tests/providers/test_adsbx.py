from unittest.mock import Mock

import httpx
import pytest

from a350f_tracker.providers.adsbx import AdsbFiProvider


def mock_response(payload):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_aircraft_on_ground(monkeypatch):
    payload = {
        "ac": [
            {
                "hex": "39a53b",
                "r": "F-WXLD",
                "t": "A35K",
                "alt_baro": "ground",
                "seen": 1.1,
            }
        ]
    }

    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: mock_response(payload),
    )

    observations = AdsbFiProvider().get_by_registration("F-WXLD")

    assert len(observations) == 1

    aircraft = observations[0]
    assert aircraft.icao_hex == "39a53b"
    assert aircraft.registration == "F-WXLD"
    assert aircraft.aircraft_type == "A35K"
    assert aircraft.altitude_ft is None
    assert aircraft.on_ground is True


def test_empty_aircraft_list(monkeypatch):
    payload = {"ac": [], "total": 0}

    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: mock_response(payload),
    )

    observations = AdsbFiProvider().get_by_registration("F-WXLD")

    assert observations == []


def test_aircraft_in_flight(monkeypatch):
    payload = {
        "ac": [
            {
                "hex": "39a53b",
                "r": "F-WXLD",
                "t": "A35K",
                "lat": 43.5,
                "lon": 1.2,
                "alt_baro": 35000,
                "gs": 450,
                "baro_rate": 1200,
                "gnd": False,
                "seen": 2.0,
            }
        ]
    }

    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: mock_response(payload),
    )

    aircraft = AdsbFiProvider().get_by_registration("F-WXLD")[0]

    assert aircraft.latitude == 43.5
    assert aircraft.longitude == 1.2
    assert aircraft.altitude_ft == 35000
    assert aircraft.ground_speed_kt == 450
    assert aircraft.vertical_rate_fpm == 1200
    assert aircraft.on_ground is False


def test_missing_optional_fields(monkeypatch):
    payload = {
        "ac": [
            {
                "hex": "39a53b",
                "r": "F-WXLD",
                "t": "A35K",
            }
        ]
    }

    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: mock_response(payload),
    )

    aircraft = AdsbFiProvider().get_by_registration("F-WXLD")[0]

    assert aircraft.latitude is None
    assert aircraft.longitude is None
    assert aircraft.altitude_ft is None
    assert aircraft.ground_speed_kt is None
    assert aircraft.vertical_rate_fpm is None
    assert aircraft.on_ground is None


def test_http_error_is_propagated(monkeypatch):
    def raise_http_error(*args, **kwargs):
        raise httpx.HTTPStatusError(
            "Server error",
            request=Mock(),
            response=Mock(),
        )

    monkeypatch.setattr(httpx, "get", raise_http_error)

    with pytest.raises(httpx.HTTPStatusError):
        AdsbFiProvider().get_by_registration("F-WXLD")


def test_registration_is_used_in_request(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return mock_response({"ac": []})

    monkeypatch.setattr(httpx, "get", fake_get)

    AdsbFiProvider().get_by_registration("F-WXLD")

    assert captured["url"].endswith("/registration/F-WXLD")
    assert captured["kwargs"]["timeout"] == 10.0
