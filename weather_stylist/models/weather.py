from dataclasses import dataclass


@dataclass
class DayForecast:
    city: str
    min_temp: float
    max_temp: float
    wind_max: float
    will_rain: bool
