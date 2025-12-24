from typing import Any, List

FEATURE_COLUMNS = [
    "temp_min",
    "temp_max",
    "wind_max",
    "will_rain",
    "thermo_profile",
    "warmth_shift",
]


def make_features(forecast: Any, user: Any) -> List[float]:
    """
    превращает (forecast, user) в вектор признаков для модели

    ожидаемые поля:
    forecast.min_temp: float
    forecast.max_temp: float
    forecast.wind_max: float
    forecast.will_rain: bool/int
    user.thermo_profile: int  (-1 / 0 / +1)
    user.warmth_shift: float - персонально под пользователя
    """
    temp_min = float(getattr(forecast, "min_temp"))
    temp_max = float(getattr(forecast, "max_temp"))
    wind_max = float(getattr(forecast, "wind_max"))
    will_rain_raw = getattr(forecast, "will_rain")
    will_rain = 1.0 if bool(will_rain_raw) else 0.0

    thermo_profile = float(getattr(user, "thermo_profile"))
    warmth_shift = float(getattr(user, "warmth_shift", 0.0))

    features = [
        temp_min,
        temp_max,
        wind_max,
        will_rain,
        thermo_profile,
        warmth_shift,
    ]
    return features
