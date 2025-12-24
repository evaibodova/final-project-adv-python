from __future__ import annotations

from typing import List, Dict

from weather_stylist.ml.features import make_features
from weather_stylist.ml.model_loader import get_regressor, try_get_delta_regressor
from weather_stylist.models.user import User
from weather_stylist.models.weather import DayForecast
from weather_stylist.models.outfit import Outfit, OutfitAdvice
from weather_stylist.recommendation.outfit_catalog import ClothingItem, ITEMS

ITEMS_BY_CODE: Dict[str, ClothingItem] = {it.code: it for it in ITEMS}

BOTTOM_ITEMS: List[ClothingItem] = [
    it for it in ITEMS if it.category == "bottom"]
MID_ITEMS: List[ClothingItem] = [it for it in ITEMS if it.category == "mid"]
OUTER_ITEMS: List[ClothingItem] = [
    it for it in ITEMS if it.category == "outer"]
ACCESSORY_ITEMS: List[ClothingItem] = [
    it for it in ITEMS if it.category == "accessory"]
SHOES_ITEMS: List[ClothingItem] = [
    it for it in ITEMS if it.category == "shoes"]

BASE_TOPS: List[ClothingItem] = [it for it in MID_ITEMS if it.warmth <= 1.4]
MID_TOPS: List[ClothingItem] = [it for it in MID_ITEMS if it.warmth > 1.4]


class _NoneMid:
    """
    нет среднего слоя
    """
    code = "none_mid"
    title = ""
    category = "mid"
    warmth = 0.0
    rain_protect = False
    wind_protect = False
    style_tags = set()


NONE_MID_ITEM = _NoneMid()


class _NoneBottom:
    """
    нет отдельного низа
    """
    code = "none_bottom"
    title = ""
    category = "bottom"
    warmth = 0.0
    rain_protect = False
    wind_protect = False
    style_tags = set()


NONE_BOTTOM_ITEM = _NoneBottom()


def _is_dress(item) -> bool:
    """
    Платье ли это
    """
    code = getattr(item, "code", "")
    return code.startswith("dress_")


def required_warmth_ml(forecast: DayForecast, user: User) -> float:
    """
    Предсказываем комфортный уровень "тепло-индекса"
    по погоде и профилю пользователя (RandomForest).
    """
    reg = get_regressor()
    x = make_features(forecast, user)
    return float(reg.predict([x])[0])


def required_warmth_rule_based(forecast: DayForecast, user: User) -> float:
    """
    База: температура + ветер + дождь + thermo_profile + персональный shift
    """
    t = float(getattr(forecast, "max_temp", 0.0))
    wind_max = float(getattr(forecast, "wind_max", 0.0))
    will_rain = 1 if bool(getattr(forecast, "will_rain", 0)) else 0
    thermo_profile = int(getattr(user, "thermo_profile", 0))
    if t <= -25:
        base = 25.0
    elif t <= -15:
        base = 18.0
    elif t <= -5:
        base = 13.0
    elif t <= 3:
        base = 8.0
    elif t <= 10:
        base = 5.0
    elif t <= 18:
        base = 3.0
    else:
        base = 1.0

    if forecast.wind_max >= 10.0:
        base += 1.0
    if bool(forecast.will_rain):
        base += 1.0

    if user.thermo_profile == -1:
        base += 1.0
    elif user.thermo_profile == 1:
        base -= 1.0
    # мерзляк / нет
    base += float(thermo_profile)
    # персональный сдвиг
    base += float(getattr(user, "warmth_shift", 0.0))
    return base


def required_warmth(forecast: DayForecast, user: User) -> float:
    base = required_warmth_rule_based(forecast, user)
    target = base

    if getattr(user, "feedback_count", 0) > 0:
        ml_pred = required_warmth_ml(forecast, user)
        raw = user.feedback_count / 10
        cf = min(0.7, max(0.1, raw))
        target = (1 - cf) * base + cf * ml_pred

    # delta по фидбекам
    delta_reg = try_get_delta_regressor()
    if delta_reg is not None and getattr(user, "feedback_count", 0) >= 5:
        x = make_features(forecast, user)
        delta = float(delta_reg.predict([x])[0])
        if delta > 2.0:
            delta = 2.0
        elif delta < -2.0:
            delta = -2.0
        raw = float(getattr(user, "feedback_count", 0)) / 50.0
        dcf = min(0.6, max(0.1, user.feedback_count / 50))
        target = target + dcf * delta

    return float(target)


# подбор комплекта по целевому тепло-индексу

def is_valid_combo(
        forecast: DayForecast,
        bottom: ClothingItem,
        base: ClothingItem,
        mid: ClothingItem,
        outer: ClothingItem,
) -> bool:
    """
    Доменные ограничения, чтобы не было совсем странных луков.
    Смотрим в первую очередь на min_temp и "теплоту" вещей.
    """
    t_min = forecast.min_temp

    # без верхней одежды при минусе — нельзя
    if t_min < 0 and outer.warmth < 0.5:
        return False

    # при сильном морозе нужна серьёзная верхняя одежда
    if t_min < -10 and outer.warmth < 3.5:  # типа пуховик/очень тёплое пальто
        return False

    is_dress_combo = _is_dress(base) or _is_dress(mid)

    if not is_dress_combo:
        if t_min < 5 and bottom.warmth < 1.0:
            return False
        if t_min < -5 and bottom.warmth < 1.5:
            return False

    # совсем лёгкий низ в холод
    if t_min < 5 and bottom.warmth < 1.0:
        return False
    if t_min < -5 and bottom.warmth < 1.5:
        return False

    # если очень холодно, а слоёв мало
    if t_min < -15 and (mid.warmth + outer.warmth) < 4.0:
        return False

    return True


def _combo_warmth(
        bottom: ClothingItem,
        base: ClothingItem,
        mid: ClothingItem,
        outer: ClothingItem,
) -> float:
    return bottom.warmth + base.warmth + mid.warmth + outer.warmth


def _pick_shoes(forecast: DayForecast) -> str | None:
    if not SHOES_ITEMS:
        return None

    t_min = forecast.min_temp

    if t_min <= -10:
        desired = 2.3
    elif t_min <= 0:
        desired = 1.8
    elif t_min <= 15:
        desired = 1.2
    else:
        desired = 0.7

    if forecast.will_rain:
        pool = [s for s in SHOES_ITEMS if s.rain_protect] or SHOES_ITEMS
    else:
        pool = SHOES_ITEMS

    def score(sh: ClothingItem) -> float:
        penalty = abs(sh.warmth - desired)
        if forecast.wind_max >= 10.0 and sh.wind_protect:
            penalty -= 0.2
        return penalty

    best = min(pool, key=score)
    return best.code


def _pick_accessories(forecast: DayForecast) -> List[str]:
    """
    Подбор аксессуаров + обуви
    """
    result: List[str] = []

    t_min = forecast.min_temp

    # холодно → берём самые тёплые аксессуары
    if t_min <= 0:
        warm_acc = sorted(
            ACCESSORY_ITEMS, key=lambda a: a.warmth, reverse=True
        )
        for item in warm_acc[:2]:
            result.append(item.code)

    # дождь → если ни верх, ни аксессуаров с rain_protect нет,
    # добавим хоть что-то дождезащитное
    if forecast.will_rain:
        rain_acc = [a for a in ACCESSORY_ITEMS if a.rain_protect]
        if rain_acc:
            result.append(rain_acc[0].code)

    # обувь
    shoes_code = _pick_shoes(forecast)
    if shoes_code is not None:
        result.append(shoes_code)

    # уникализируем
    seen: set[str] = set()
    unique: List[str] = []
    for code in result:
        if code not in seen:
            seen.add(code)
            unique.append(code)

    return unique


def pick_outfit_by_index(
        forecast: DayForecast,
        user: User,
        target_warmth: float,
) -> Outfit:
    """
    Перебираем разумные комбинации (низ + базовый верх + средний слой + верхняя одежда),
    ищем ту, у которой суммарный warmth ближе всего к target_warmth.
    """
    # если вдруг нет разбиения — фоллбек
    base_tops = BASE_TOPS or MID_ITEMS or []
    mid_tops = MID_TOPS or []
    bottoms = BOTTOM_ITEMS or []
    outers = OUTER_ITEMS or []

    if not bottoms or not base_tops or not outers:
        return Outfit(
            bottom="",
            base="",
            mid="",
            outer="",
            accessories=[],
        )

    best_combo: tuple[str, str, str, str] | None = None
    best_diff = 1e9

    mid_candidates: List[ClothingItem] = [NONE_MID_ITEM] + mid_tops

    for base in base_tops:
        for mid in mid_candidates:
            is_dress_combo = _is_dress(base) or _is_dress(mid)
            candidate_bottoms = [
                NONE_BOTTOM_ITEM] if is_dress_combo else bottoms

            for bottom in candidate_bottoms:
                for outer in outers:
                    if not is_valid_combo(forecast, bottom, base, mid, outer):
                        continue

                    warmth = _combo_warmth(bottom, base, mid, outer)
                    diff = abs(warmth - target_warmth)

                    if diff < best_diff:
                        best_diff = diff
                        best_combo = (
                            bottom.code,
                            base.code,
                            mid.code,
                            outer.code,
                        )

    if best_combo is None:
        # фоллбек на первые попавшиеся вещи
        bottom_code = bottoms[0].code
        base_code = base_tops[0].code
        outer_code = outers[0].code
        mid_code = ""
    else:
        bottom_code, base_code, mid_code, outer_code = best_combo
        if mid_code == NONE_MID_ITEM.code:
            mid_code = ""
        if bottom_code == NONE_BOTTOM_ITEM.code:
            bottom_code = ""

    accessories_codes = _pick_accessories(forecast)

    return Outfit(
        bottom=bottom_code,
        base=base_code,
        mid=mid_code,
        outer=outer_code,
        accessories=accessories_codes,
    )


# ---- сборка текста для пользователя ----

def render_outfit_text(
        forecast: DayForecast,
        user: User,
        outfit: Outfit,
) -> str:
    parts: List[str] = []

    def add_title(code: str | None) -> None:
        if not code:
            return
        item = ITEMS_BY_CODE.get(code)
        if item and item.title:
            parts.append(item.title)

    # низ + верх (база + слой) + верхняя одежда
    add_title(getattr(outfit, "bottom", ""))
    add_title(getattr(outfit, "base", ""))
    add_title(getattr(outfit, "mid", ""))
    add_title(getattr(outfit, "outer", ""))

    # аксессуары + обувь
    for code in getattr(outfit, "accessories", []):
        add_title(code)

    clothes_text = ", ".join(
        parts) if parts else "что-нибудь удобное по погоде"

    forecast_text = (
        f"сегодня в {forecast.city} от {round(forecast.min_temp)}° до "
        f"{round(forecast.max_temp)}°, ветер до {round(forecast.wind_max)} м/с"
    )
    if forecast.will_rain:
        forecast_text += ", возможен дождь"

    return (
        f"{forecast_text}.\n\n"
        f"я бы предложила тебе надеть: {clothes_text}."
    )


def build_today_advice(forecast: DayForecast, user: User) -> OutfitAdvice:
    """
    точка входа для бота:
    - считаем нужный тепло-индекс
    - подбираем комплект
    - собираем текст ответа бота
    """
    target_warmth = required_warmth(forecast, user)
    outfit = pick_outfit_by_index(forecast, user, target_warmth)
    text = render_outfit_text(forecast, user, outfit)
    return OutfitAdvice(text=text, outfit=outfit)
