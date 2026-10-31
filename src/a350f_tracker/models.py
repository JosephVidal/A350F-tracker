from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class AircraftObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    icao_hex: str
    registration: str | None = None
    aircraft_type: str | None = None

    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    altitude_ft: float | None = None
    ground_speed_kt: float | None = None
    vertical_rate_fpm: float | None = None
    on_ground: bool | None = None

    observed_at: datetime

    @classmethod
    def now_utc(cls) -> datetime:
        return datetime.now(timezone.utc)
