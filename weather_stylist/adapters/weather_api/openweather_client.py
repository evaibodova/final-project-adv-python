from typing import Any, Dict, List
from ...models import HourForecast, DayForecast
from ...infra import CityNotFoundError, WeatherAPIError
import aiohttp
import os


BASE_URL = "https://api.weatherapi.com/v1/forecast.json"

# выгрузка переменных окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

WEATHERAPI_KEY: str | None = os.getenv("WEATHERAPI_KEY")
DEFAULT_CITY: str | None = os.getenv("DEFAULT_CITY")


# вспомогательные функции по солид и драй

def ensure_city(city: str | None) -> str:
    if city:
        return city
    if not DEFAULT_CITY:
        raise RuntimeError("DEFAULT_CITY is not set in environment")
    return DEFAULT_CITY


def ensure_api_key() -> str:
    if not WEATHERAPI_KEY:
        raise RuntimeError("WEATHERAPI_KEY is not set in environment")
    return WEATHERAPI_KEY


def build_params(city: str, days: int) -> Dict[str, str | int]:
    return {
        "key": ensure_api_key(),
        "q": city,
        "days": days,
        "aqi": "no",
        "alerts": "no",
        "lang": "ru",
    }


async def fetch_forecast_json(city: str | None, days: int) -> Dict[str, Any]:
    """JSON для n дней"""
    resolved_city: str = ensure_city(city)
    params: Dict[str, str | int] = build_params(resolved_city, days)

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as resp:
            data: Dict[str, Any] = await resp.json()

    if "error" in data:
        err = data["error"]
        msg = err.get("message", "weather api error")
        code = err.get("code")

        # код 1006 у WeatherAPI — "No matching location found."
        if code == 1006 or "No matching location" in msg:
            raise CityNotFoundError(msg)

        raise WeatherAPIError(msg)

    return data


def parse_day_block(location: str, day_block: Dict[str, Any]) -> DayForecast:
    """JSON за один день -> DayForecast"""
    day = day_block["day"]
    hours = day_block["hour"]

    min_temp: float = day["mintemp_c"]
    max_temp: float = day["maxtemp_c"]
    wind_max_kph: float = day["maxwind_kph"]
    wind_max: float = wind_max_kph / 3.6  # м/с

    will_rain: bool = day.get("daily_will_it_rain", 0) == 1 or day.get(
        "daily_chance_of_rain", 0
    ) > 0

    hourly: List[HourForecast] = []

    for h in hours:
        time_str: str = h["time"]
        hour: int = int(time_str[-5:-3])

        temp: float = h["temp_c"]
        feels_like: float = h["feelslike_c"]
        wind_kph: float = h["wind_kph"]
        wind_ms: float = wind_kph / 3.6
        will_rain_hour: bool = bool(h.get("will_it_rain", 0))

        hourly.append(
            HourForecast(
                hour=hour,
                temp=temp,
                feels_like=feels_like,
                wind=wind_ms,
                will_rain=will_rain_hour,
            )
        )

    return DayForecast(
        city=location,
        min_temp=min_temp,
        max_temp=max_temp,
        wind_max=wind_max,
        will_rain=will_rain,
        hourly=hourly,
    )

# основные функции форкаста


async def get_forecast_for_city(city: str | None = None) -> DayForecast:
    """
    Получаем прогноз на 1 день для города через WeatherAPI и
    приводим к удобной структуре DayForecast.
    """
    data: Dict[str, Any] = await fetch_forecast_json(city, days=1)

    location: str = data["location"]["name"]
    day_block: Dict[str, Any] = data["forecast"]["forecastday"][0]

    return parse_day_block(location, day_block)


async def get_two_days_forecast(city: str | None = None) -> List[DayForecast]:
    data: Dict[str, Any] = await fetch_forecast_json(city, days=2)

    location: str = data["location"]["name"]
    forecast_days: List[Dict[str, Any]] = data["forecast"]["forecastday"]

    result: List[DayForecast] = []

    for day_block in forecast_days[:2]:
        result.append(parse_day_block(location, day_block))

    return result
