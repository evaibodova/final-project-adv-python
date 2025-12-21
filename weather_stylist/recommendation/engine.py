from itertools import product
from typing import List

from weather_stylist.ml.features import make_features
from weather_stylist.ml.model_loader import get_regressor


from weather_stylist.models.user import User
from weather_stylist.models.weather import DayForecast
from weather_stylist.models.outfit import Outfit, OutfitAdvice

ITEM_WARMTH = {
    # низ
    "shorts": 1.0,
    "short_skirt": 0.0,
    "long_skirt": 1.5,
    "trousers": 2.0,
    "jeans": 3.0,
    "warm_trousers": 4.0,

    # базовый слой
    "top": 0.0,
    "tshirt": 1.0,
    "longsleeve": 1.5,
    "thermal": 2.0,

    # средний слой
    "none_mid": 0.0,
    "shirt": 1.0,
    "hoodie": 2.0,
    "sweater": 3.0,

    # верхняя одежда
    "none_outer": 0.0,
    "light_jacket": 3.0,  # демисезонная
    "coat": 4.0,
    "winter_jacket": 5.0,

    # аксессуары
    "hat": 0.5,
    "tights": 1.0,
    "scarf": 0.5,
    "gloves": 0.5,
}

BOTTOM = ["shorts", "short_skirt", "long_skirt",
          "trousers", "jeans", "warm_trousers"]
BASE_OPTIONS = ["tshirt", "longsleeve", "thermal", "top"]
MID_OPTIONS = ["none_mid", "hoodie", "sweater", "shirt"]
OUTER_OPTIONS = ["none_outer", "light_jacket", "coat", "winter_jacket"]
ACCESSORY_OPTIONS: List[List[str]] = [
    [],
    ["hat"],
    ["tights"],
    ["hat", "tights"],
    ["hat", "scarf"],
    ["hat", "scarf", "tights"],
    ["hat", "scarf", "gloves", "tights"],
]


def is_valid_combo(forecast: DayForecast, bottom: str, outer: str) -> bool:
    t_min = forecast.min_temp

    if t_min < 0 and outer == "none_outer":
        return False

    if t_min < -10 and outer not in ["coat", "winter_jacket"]:
        return False

    if t_min < 5 and bottom in ["shorts", "short_skirt"]:
        return False

    if t_min < -5 and bottom not in ["jeans", "warm_trousers"]:
        return False

    return True


def combo_warmth(bottom: str, base: str, mid: str, outer: str, accessories: List[str]) -> float:
    w = 0.0
    w += ITEM_WARMTH[bottom]
    w += ITEM_WARMTH[base]
    w += ITEM_WARMTH[mid]
    w += ITEM_WARMTH[outer]
    for a in accessories:
        w += ITEM_WARMTH[a]
    return w

def required_warmth_ml(forecast: DayForecast, user: User) -> float:
    reg = get_regressor()
    x = make_features(forecast, user)
    # regressor ожидает shape (1, n_features)
    return float(reg.predict([x])[0])

def required_warmth_rule_based(forecast: DayForecast, user: User) -> float:
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
    return base + user.warmth_shift


def pick_outfit_by_index(forecast: DayForecast, user: User, target_warmth: float) -> Outfit:
    best_combo = None
    best_diff = 999.0

    for bottom, base, mid, outer, accessories in product(
        BOTTOM, BASE_OPTIONS, MID_OPTIONS, OUTER_OPTIONS, ACCESSORY_OPTIONS
    ):
        if not is_valid_combo(forecast, bottom, outer):
            continue

        w = combo_warmth(bottom, base, mid, outer, accessories)
        diff = abs(w - target_warmth)

        if diff < best_diff:
            best_diff = diff
            best_combo = (bottom, base, mid, outer, accessories)

    if best_combo is None:
        best_combo = ("jeans", "tshirt", "hoodie", "light_jacket", [])

    bottom, base, mid, outer, accessories = best_combo
    return Outfit(
        bottom=bottom,
        base=base,
        mid=mid,
        outer=outer,
        accessories=accessories,
    )
    
def required_warmth(forecast: DayForecast, user: User) -> float:
    """
    Если нет фидбека используем только rule_based
    Если фидбек есть смешиваем rule_based и модель
    """
    base = required_warmth_rule_based(forecast, user)

    if user.feedback_count <= 0:
        return base

    try:
        ml_pred = required_warmth_ml(forecast, user)
        return 0.5 * base + 0.5 * ml_pred
    except Exception:
        return base



def render_outfit_text(forecast: DayForecast, user: User, outfit: Outfit) -> str:
    parts: List[str] = []

      # низ
    if outfit.bottom == "shorts":
        parts.append("шорты")
    elif outfit.bottom == "short_skirt":
        parts.append("короткую юбку")
    elif outfit.bottom == "long_skirt":
        parts.append("длинную юбку")
    elif outfit.bottom == "trousers":
        parts.append("брюки")
    elif outfit.bottom == "jeans":
        parts.append("джинсы")
    elif outfit.bottom == "warm_trousers":
        parts.append("тёплые штаны")

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
        forecast_text += ", возможен дождь, не забудь про зонт ☔"

    return (
        f"{forecast_text}.\n\n"
        f"я бы предложил тебе надеть {clothes_text}."
    )


def build_today_advice(forecast: DayForecast, user: User) -> OutfitAdvice:
    target_warmth = required_warmth(forecast, user)
    outfit = pick_outfit_by_index(forecast, user, target_warmth)
    text = render_outfit_text(forecast, user, outfit)
    return OutfitAdvice(text=text, outfit=outfit)

