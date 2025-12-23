from dataclasses import dataclass
from typing import List

import aiohttp
import os


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


BASE_URL = "https://api.weatherapi.com/v1/forecast.json"

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

WEATHERAPI_KEY = os.getenv("WEATHERAPI_KEY")
DEFAULT_CITY = os.getenv("DEFAULT_CITY")


async def get_forecast_for_city(city: str | None = None) -> DayForecast:
    """
    Получаем прогноз на 1 день для города через WeatherAPI и
    приводим к удобной структуре DayForecast.
    """
    if not city:
        city = DEFAULT_CITY

    params = {
        "key": WEATHERAPI_KEY,
        "q": city,
        "days": 1,
        "aqi": "no",
        "alerts": "no",
        "lang": "ru",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as resp:
            data = await resp.json()
            
    if "error" in data:
        raise ValueError(data["error"].get("message", "weather api error"))

    location = data["location"]["name"]
    day = data["forecast"]["forecastday"][0]["day"]
    hours = data["forecast"]["forecastday"][0]["hour"]

    min_temp = day["mintemp_c"]
    max_temp = day["maxtemp_c"]
    wind_max_kph = day["maxwind_kph"]
    wind_max = wind_max_kph / 3.6

    will_rain = day.get("daily_will_it_rain", 0) == 1 or day.get(
        "daily_chance_of_rain", 0
    ) > 0

    hourly: List[HourForecast] = []

    for h in hours:
        time_str: str = h["time"]          
        hour = int(time_str[-5:-3])

        temp = h["temp_c"]
        feels_like = h["feelslike_c"]
        wind_kph = h["wind_kph"]
        wind_ms = wind_kph / 3.6
        will_rain_hour = bool(h.get("will_it_rain", 0))

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


async def get_two_days_forecast(city: str | None = None) -> list[DayForecast]:
    if not city:
        city = DEFAULT_CITY

    params = {
        "key": WEATHERAPI_KEY,
        "q": city,
        "days": 2,
        "aqi": "no",
        "alerts": "no",
        "lang": "ru",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as resp:
            data = await resp.json()

    if "error" in data:
        raise ValueError(data["error"].get("message", "weather api error"))

    location = data["location"]["name"]
    forecast_days = data["forecast"]["forecastday"]

    result: list[DayForecast] = []

    for day_block in forecast_days[:2]:
        day = day_block["day"]
        hours = day_block["hour"]

        min_temp = day["mintemp_c"]
        max_temp = day["maxtemp_c"]
        wind_max_kph = day["maxwind_kph"]
        wind_max = wind_max_kph / 3.6

        will_rain = day.get("daily_will_it_rain", 0) == 1 or day.get(
            "daily_chance_of_rain", 0
        ) > 0

        hourly: List[HourForecast] = []

        for h in hours:
            time_str: str = h["time"]
            hour = int(time_str[-5:-3])

            temp = h["temp_c"]
            feels_like = h["feelslike_c"]
            wind_kph = h["wind_kph"]
            wind_ms = wind_kph / 3.6
            will_rain_hour = bool(h.get("will_it_rain", 0))

            hourly.append(
                HourForecast(
                    hour=hour,
                    temp=temp,
                    feels_like=feels_like,
                    wind=wind_ms,
                    will_rain=will_rain_hour,
                )
            )

        result.append(
            DayForecast(
                city=location,
                min_temp=min_temp,
                max_temp=max_temp,
                wind_max=wind_max,
                will_rain=will_rain,
                hourly=hourly,
            )
        )

    return result
