from weather_stylist.ml.features import FEATURE_COLUMNS
from weather_stylist.ml.synthetic_dataset import (
    rule_based_required_warmth,
    random_weather,
    random_thermo_profile,
)


def test_rule_based_required_warmth_temperature_ranges():
    """проверяет правильность расчета базового тепла по темп диапазонам"""
    assert rule_based_required_warmth(-30, -25, 5, 0, 0) == 25.0
    assert rule_based_required_warmth(-20, -15, 5, 0, 0) == 18.0
    assert rule_based_required_warmth(-10, -5, 5, 0, 0) == 13.0
    assert rule_based_required_warmth(0, 3, 5, 0, 0) == 8.0
    assert rule_based_required_warmth(5, 10, 5, 0, 0) == 5.0
    assert rule_based_required_warmth(15, 18, 5, 0, 0) == 3.0
    assert rule_based_required_warmth(20, 25, 5, 0, 0) == 1.0


def test_rule_based_required_warmth_wind_effect():
    """проверяет влияние сильного ветра на тепло"""
    base = rule_based_required_warmth(10, 15, 5, 0, 0)
    with_wind = rule_based_required_warmth(10, 15, 12, 0, 0)
    
    assert with_wind == base + 1.0


def test_rule_based_required_warmth_rain_effect():
    """проверяет влияние дождя на тепло"""
    base = rule_based_required_warmth(10, 15, 5, 0, 0)
    with_rain = rule_based_required_warmth(10, 15, 5, 1, 0)
    
    assert with_rain == base + 1.0


def test_rule_based_required_warmth_thermo_profile():
    """проверяет влияние термопрофиля пользователя"""
    base = rule_based_required_warmth(10, 15, 5, 0, 0)  # обычный чел
    
    cold_profile = rule_based_required_warmth(10, 15, 5, 0, -1)  # мерзляк
    assert cold_profile == base + 1.0
    
    hot_profile = rule_based_required_warmth(10, 15, 5, 0, 1)  # климакс чел
    assert hot_profile == base - 1.0


def test_rule_based_required_warmth_combined_effects():
    """проверяет комбинацию всех факторов"""
    result = rule_based_required_warmth(-20, -15, 12, 1, -1)
    # тепло для -15°C = 18.0 (+ ветер (>=10) + дождь + мерзляк = +3.0)
    assert result == 21.0


def test_random_weather_returns_valid_values():
    """проверяет, что random_weather возвращает валидные значения"""
    temp_min, temp_max, wind_max, will_rain = random_weather()
    
    #диапазоны
    assert -30 <= temp_min <= temp_max <= 35
    assert temp_min <= temp_max
    assert 0.0 <= wind_max <= 15.0
    assert will_rain in [0, 1]


def test_random_weather_multiple_calls():
    """проверяет, что функция генерирует разные значения при повторных вызовах"""
    results = [random_weather() for _ in range(10)]
    
    # хотяб некоторые значения должны отличаться; проверяем, что не все результаты одинаковые
    unique_results = set(results)
    assert len(unique_results) > 1, "функция должна генерировать разные значения"


def test_random_thermo_profile_returns_valid_values():
    """проверяет, что random_thermo_profile возвращает валидные значения"""
    profile = random_thermo_profile()
    assert profile in [-1, 0, 1]


def test_random_thermo_profile_distribution():
    """проверяет, что все значения термопрофиля могут быть сгенерированы"""
    profiles = [random_thermo_profile() for _ in range(30)]
    unique_profiles = set(profiles)
    assert len(unique_profiles) == 3, "должны встречаться все три значения: -1, 0, 1"


def test_generate_synthetic_dataset_structure():
    """проверяет структуру и валидность данных, генерируемых для синтетического датасета"""
    #логика создания строк датасета напрямую (без файловой системы для изоляции теста)
    n_samples = 10
    fieldnames = FEATURE_COLUMNS + ["required_warmth"]
    rows = []
    
    for _ in range(n_samples):
        temp_min, temp_max, wind_max, will_rain = random_weather()
        thermo_profile = random_thermo_profile()
        warmth_shift = 0.0
        
        required = rule_based_required_warmth(
            temp_min=temp_min,
            temp_max=temp_max,
            wind_max=wind_max,
            will_rain=will_rain,
            thermo_profile=thermo_profile,
        )
        
        row = {
            "temp_min": temp_min,
            "temp_max": temp_max,
            "wind_max": wind_max,
            "will_rain": will_rain,
            "thermo_profile": thermo_profile,
            "warmth_shift": warmth_shift,
            "required_warmth": required,
        }
        rows.append(row)
    
    assert len(rows) == n_samples
    
    for row in rows:
        assert set(row.keys()) == set(fieldnames)
        
        #валидность данных
        assert float(row["temp_min"]) <= float(row["temp_max"])
        assert -30 <= float(row["temp_min"]) <= 35
        assert -20 <= float(row["temp_max"]) <= 35
        assert 0.0 <= float(row["wind_max"]) <= 15.0
        assert int(row["will_rain"]) in [0, 1]
        assert int(row["thermo_profile"]) in [-1, 0, 1]
        assert float(row["warmth_shift"]) == 0.0
        assert float(row["required_warmth"]) > 0
        
        #required_warmth соответствует правилам
        calculated = rule_based_required_warmth(
            temp_min=float(row["temp_min"]),
            temp_max=float(row["temp_max"]),
            wind_max=float(row["wind_max"]),
            will_rain=int(row["will_rain"]),
            thermo_profile=int(row["thermo_profile"]),
        )
        assert abs(float(row["required_warmth"]) - calculated) < 0.001