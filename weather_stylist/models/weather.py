from dataclasses import dataclass
from typing import List

@dataclass
class HourForecast:
    hour: int          
    temp: float       
    feels_like: float  
    wind: float       
    will_rain: bool


@dataclass
class DayForecast:
    city: str
    min_temp: float
    max_temp: float
    wind_max: float
    will_rain: bool
    hourly: List[HourForecast]
