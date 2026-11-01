import os
import yaml

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pathlib import Path

load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Variable d'environnement manquante : {name}"
        )
    return value


class Settings(BaseModel):
    polling_interval_seconds: int = Field(default=60, ge=10)


class Settings(BaseModel):
    polling_interval_seconds: int = Field(default=60, ge=10)

    database_path: Path = Path("data/tracker.db")

    registrations: list[str] = Field(
        default_factory=lambda: ["F-WXLD"]
    )


class AircraftConfig(BaseModel):
    registration: str
    icao_hex: str
    msn: int
    model: str
    operator: str
    enabled: bool = True


class AircraftConfigFile(BaseModel):
    aircraft: list[AircraftConfig]


class Settings(BaseModel):
    polling_interval_seconds: int = Field(default=60, ge=10)
    database_path: Path = Path("data/tracker.db")
    aircraft_config_path: Path = Path("config/aircraft.yaml")


def load_aircraft_config(path: Path) -> list[AircraftConfig]:
    with path.open("r", encoding="utf-8") as file:
        payload = yaml.safe_load(file)

    config = AircraftConfigFile.model_validate(payload)

    return [
        aircraft
        for aircraft in config.aircraft
        if aircraft.enabled
    ]