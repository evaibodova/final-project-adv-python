class WeatherStylistError(Exception):
    """
    Базовое исключение
    """


# ошибки внешних сервисов


class ExternalServiceError(WeatherStylistError):
    """Ошибка при работе с внешними сервисами"""


class WeatherAPIError(ExternalServiceError):
    """Проблема c Weather API """


class CityNotFoundError(WeatherAPIError):
    """Город не найден в Weather API"""

# ошибки модели


class ModelError(WeatherStylistError):
    """Общая ошибка с ML-моделью"""


class ModelNotReadyError(ModelError):
    """
    Модель ещё не обучена или файл с весами недоступен
    """
