from itertools import product
from typing import List

from weather_stylist.domain.user import UserProfile
from weather_stylist.domain.weather import DayForecast
from weather_stylist.domain.outfit import Outfit, OutfitAdvice

ITEM_WARMTH = {
    # базовый слой
    "tshirt": 1.0,
    "longsleeve": 1.5,
    "thermal": 2.0,

    # средний слой
    "none_mid": 0.0,
    "hoodie": 2.0,
    "sweater": 3.0,

    # верхняя одежда
    "none_outer": 0.0,
    "light_jacket": 3.0,   # демисезонная
    "coat": 4.0,
    "winter_jacket": 5.0,

    # аксессуары
    "hat": 0.5,
    "scarf": 0.5,
    "gloves": 0.5,
}

BASE_OPTIONS = ["tshirt", "longsleeve", "thermal"]
MID_OPTIONS = ["none_mid", "hoodie", "sweater"]
OUTER_OPTIONS = ["none_outer", "light_jacket", "coat", "winter_jacket"]
ACCESSORY_OPTIONS: List[List[str]] = [
    [],
    ["hat"],
    ["hat", "scarf"],
    ["hat", "scarf", "gloves"],
]

def is_valid_combo(forecast: DayForecast, outer: str) -> bool:
    """доменные ограничения, чтобы не было 'без куртки при -20'."""
    t_min = forecast.min_temp

    if t_min < 0 and outer == "none_outer":
        return False

    if t_min < -10 and outer not in ["coat", "winter_jacket"]:
        return False

    return True

def combo_warmth(base: str, mid: str, outer: str, accessories: List[str]) -> float:
    w = 0.0
    w += ITEM_WARMTH[base]
    w += ITEM_WARMTH[mid]
    w += ITEM_WARMTH[outer]
    for a in accessories:
        w += ITEM_WARMTH[a]
    return w

def required_warmth_rule_based(forecast: DayForecast, user: UserProfile) -> float:
    """
    Возвращает, сколько условных единиц тепла хотим дать пользователю.
    Потом это можно заменить на model.predict(features).
    """
    t = forecast.max_temp
    base = 0.0

    if t <= -15:
        base = 7.0
    elif t <= -5:
        base = 6.0
    elif t <= +3:
        base = 5.0
    elif t <= +10:
        base = 4.0
    elif t <= +18:
        base = 3.0
    else:
        base = 2.0

    # поправка на индивидуальность: warmth_shift >0 -> теплее, <0 -> прохладнее
    return base + user.warmth_shift

def pick_outfit_by_index(forecast: DayForecast, user: UserProfile, target_warmth: float) -> Outfit:
    best_combo = None
    best_diff = 999.0

    for base, mid, outer, accessories in product(
        BASE_OPTIONS, MID_OPTIONS, OUTER_OPTIONS, ACCESSORY_OPTIONS
    ):
        if not is_valid_combo(forecast, outer):
            continue

        w = combo_warmth(base, mid, outer, accessories)
        diff = abs(w - target_warmth)

        if diff < best_diff:
            best_diff = diff
            best_combo = (base, mid, outer, accessories)

    if best_combo is None:
        # на всякий случай fallback
        best_combo = ("tshirt", "hoodie", "light_jacket", [])

    base, mid, outer, accessories = best_combo
    return Outfit(base=base, mid=mid, outer=outer, accessories=accessories)

def render_outfit_text(forecast: DayForecast, user: UserProfile, outfit: Outfit) -> str:
    parts: List[str] = []

    # база
    if outfit.base == "tshirt":
        parts.append("футболку")
    elif outfit.base == "longsleeve":
        parts.append("лонгслив")
    elif outfit.base == "thermal":
        parts.append("термобельё")

    # средний слой
    if outfit.mid == "hoodie":
        parts.append("худи")
    elif outfit.mid == "sweater":
        parts.append("свитер")

    # верхняя одежда
    if outfit.outer == "light_jacket":
        parts.append("лёгкую демисезонную куртку")
    elif outfit.outer == "coat":
        parts.append("пальто")
    elif outfit.outer == "winter_jacket":
        parts.append("тёплый пуховик")

    # аксессуары
    if "hat" in outfit.accessories:
        parts.append("шапку")
    if "scarf" in outfit.accessories:
        parts.append("шарф")
    if "gloves" in outfit.accessories:
        parts.append("перчатки")

    clothes_text = ", ".join(parts)
    forecast_text = (
        f"сегодня в {forecast.city} от {round(forecast.min_temp)}° до "
        f"{round(forecast.max_temp)}°, ветер до {round(forecast.wind_max)} м/с"
    )
    if forecast.will_rain:
        forecast_text += ", возможен дождь ☔"

    return (
        f"{forecast_text}.\n\n"
        f"я бы предложил тебе надеть {clothes_text}."
    )

def build_today_advice(forecast: DayForecast, user: UserProfile) -> OutfitAdvice:
    # 1. считаем, сколько тепла нужно (пока rule-based)
    target_warmth = required_warmth_rule_based(forecast, user)

    # 2. подбираем комплект ближе всего к этому уровню тепла
    outfit = pick_outfit_by_index(forecast, user, target_warmth)

    # 3. собираем текст
    text = render_outfit_text(forecast, user, outfit)

    return OutfitAdvice(text=text, outfit=outfit)
