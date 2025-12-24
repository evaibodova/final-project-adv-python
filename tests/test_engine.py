from weather_stylist.recommendation.engine import (
    required_warmth_rule_based,
    pick_outfit_by_index,
    build_today_advice,
)
from tests.conftest import DummyForecast, DummyUser


def test_required_warmth_colder_bigger():
    f_cold = DummyForecast(min_temp=-15, max_temp=-10, wind_max=5, will_rain=False, city="Москва")
    f_warm = DummyForecast(min_temp=5, max_temp=10, wind_max=5, will_rain=False, city="Москва")
    user = DummyUser()

    cold_idx = required_warmth_rule_based(f_cold, user)
    warm_idx = required_warmth_rule_based(f_warm, user)

    assert cold_idx > warm_idx


def test_pick_outfit_very_cold_has_outer():
    forecast = DummyForecast(min_temp=-20, max_temp=-15, wind_max=4, will_rain=False, city="Москва")
    user = DummyUser()

    target = required_warmth_rule_based(forecast, user)
    outfit = pick_outfit_by_index(forecast, user, target)

    # Проверяем, что выбрана теплая верхняя одежда для холодной погоды
    warm_outers = {"coat", "parka", "winter_jacket", "winter_puffer", "down_jacket"}
    assert outfit.outer in warm_outers, f"Expected warm outer, got {outfit.outer}"


def test_pick_outfit_warm_day_without_heavy_outer():
    forecast = DummyForecast(min_temp=20, max_temp=27, wind_max=2, will_rain=False, city="Сочи")
    user = DummyUser()

    target = required_warmth_rule_based(forecast, user)
    outfit = pick_outfit_by_index(forecast, user, target)

    # Проверяем, что для теплой погоды не выбрана тяжелая верхняя одежда
    light_outers = {"none_outer", "light_jacket", "denim_jacket", "cardigan", "blazer"}
    heavy_outers = {"parka", "winter_jacket", "winter_puffer", "down_jacket"}
    assert outfit.outer in light_outers, f"Expected light outer for warm weather, got {outfit.outer}"
    assert outfit.outer not in heavy_outers, f"Should not have heavy outer for warm weather, got {outfit.outer}"


def test_build_today_advice_returns_text_and_outfit():
    forecast = DummyForecast(min_temp=5, max_temp=10, wind_max=7, will_rain=True, city="Амстердам")
    user = DummyUser()

    advice = build_today_advice(forecast, user)

    assert advice.text
    assert "Амстердам" in advice.text
    assert advice.outfit.outer