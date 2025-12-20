from dataclasses import dataclass

from weather_stylist.recommendation.engine import (
    required_warmth_rule_based,
    pick_outfit_by_index,
    build_today_advice,
)


@dataclass
class DummyForecast:
    city: str
    min_temp: float
    max_temp: float
    wind_max: float
    will_rain: bool


@dataclass
class DummyUser:
    name: str = "тест"
    warmth_shift: float = 0.0
    thermo_profile: int = 0


def test_required_warmth_colder_bigger():
    f_cold = DummyForecast("Москва", -15, -10, 5, False)
    f_warm = DummyForecast("Москва", +5, +10, 5, False)
    user = DummyUser()

    cold_idx = required_warmth_rule_based(f_cold, user)
    warm_idx = required_warmth_rule_based(f_warm, user)

    assert cold_idx > warm_idx


def test_pick_outfit_very_cold_has_outer():
    forecast = DummyForecast("Москва", -20, -15, 4, False)
    user = DummyUser()

    target = required_warmth_rule_based(forecast, user)
    outfit = pick_outfit_by_index(forecast, user, target)

    assert outfit.outer in {"coat", "parka", "winter_coat"}


def test_pick_outfit_warm_day_without_heavy_outer():
    forecast = DummyForecast("Сочи", 20, 27, 2, False)
    user = DummyUser()

    target = required_warmth_rule_based(forecast, user)
    outfit = pick_outfit_by_index(forecast, user, target)

    assert outfit.outer in {"none_outer", "light_jacket", "coat"}


def test_build_today_advice_returns_text_and_outfit():
    forecast = DummyForecast("Амстердам", 5, 10, 7, True)
    user = DummyUser()

    advice = build_today_advice(forecast, user)

    assert advice.text
    assert "Амстердам" in advice.text
    assert advice.outfit.outer