# Техническая документация: Miranda Weather Stylist Bot

## 1. Описание проекта

**Miranda Weather Stylist Bot** — Telegram-бот-стилист, который рекомендует пользователям одежду на основе прогноза погоды. Бот сочетает **правила (rule-based движок)** и **ML-персонализацию**, учитывая:

* город/район пользователя,
* термочувствительность (профиль “мне холодно/норм/жарко”),
* выбранный стиль одежды (casual/office/sport),
* **персональный сдвиг тепла** (`warmth_shift`), который обновляется по фидбеку пользователя (online adaptation).

Что умеет:

1. **Онбординг и настройки**: город/район, стиль, термопрофиль.
2. **Рекомендация на сегодня** (`/advice` / “Совет на сегодня”): текст + структура комплекта (`Outfit`) + (опционально) фото-референсы.
3. **Сбор обратной связи** и **онлайн-обучение** персонального сдвига.
4. **Фоновая рассылка/алерты**: уведомления о резкой смене погоды / дождь в ближайшие часы (через планировщик).

---

## 2. Стек технологий

* **Язык:** Python 3.12+
* **Фреймворк бота:** aiogram 3.x (asyncio)
* **HTTP:** aiohttp
* **ORM/БД:** SQLAlchemy + SQLite (в текущем описании проекта)
* **ML:** scikit-learn (регрессор комфорта), numpy/pandas
* **Тестирование:** pytest
* **Контейнеризация:** Docker
* **Архитектура:** слои с разделением Domain / Adapters / Recommendation(Core) / Bot(Presentation) / Infra

---

## 3. Архитектура (слои)

### Presentation (bot/)

* aiogram-хендлеры команд, текстовые кнопки меню.
* FSM-диалоги настроек (город/район/стиль/термопрофиль).
* Сбор фидбека и вызов обновления `warmth_shift`.
* Отправка сообщений и (при наличии) фото-референсов.

### Core (recommendation/)

* `engine.py` — ядро логики рекомендаций: получает пользователя + прогноз, вызывает ML, собирает `OutfitAdvice`.

### ML (ml/)

* `model_loader.py` — ленивая загрузка `comfort_regressor.pkl`.
* `features.py` — сбор признаков из пользователя и погоды (`make_features`).
* `online_shift.py` — обновление персонального `warmth_shift` по фидбеку.
* `train_model.py` + `synthetic_dataset.py` — обучение на синтетике.

### Infrastructure / Adapters

* **adapters/weather_api/** — клиент OpenWeather и маппинг JSON → доменные модели прогноза.
* **adapters/user_bd/** — SQLAlchemy setup + репозиторий пользователей/фидбека.
* **infra/** — конфиги и планировщик уведомлений.

---

## 4. Доменные модели данных (models/)

* `User` — профиль пользователя (tg_id, city, термопрофиль, `warmth_shift`, стиль и т.д.)
* `FeedbackRecord` — запись фидбека (оценка рекомендации)
* `DayForecast` — прогноз на день (min/max температура, ветер, дождь и т.п.)
* `Outfit` — структура комплекта (низ/слои/верх/аксессуары)
* `OutfitAdvice` — финальная рекомендация (текст + Outfit + доп. данные)

---

## 5. Рекомендательный движок

### Главная точка: `recommendation/engine.py`

**`build_today_advice(user, forecast)`** делает примерно следующее:

1. Получает прогноз (`DayForecast`) и профиль пользователя (`User`).
2. Генерирует признаки через `ml/features.py::make_features`.
3. Берёт ML-предсказание “какая нужна теплота / комфортная температура”.
4. Корректирует результат с учётом:

   * термопрофиля (холодно/норм/жарко),
   * персонального `warmth_shift`.
5. Подбирает элементы одежды по правилам + по выбранному стилю (modules styles).
6. Формирует `OutfitAdvice` (текст + структура Outfit).
7. (Опционально) подбирает 3 фото-референса из папок стиля по температурному диапазону.

---

## 6. Работа со стилями и фото (bot/handlers/styles/)

Для каждого стиля есть модуль логики и папки с фото-референсами:

* `casual_style/casual.py`
* `office_style/office.py`
* `sport_style/sport.py`

Внутри каждого стиля — каталоги фото по диапазонам температур:

* `photos_winter_temp/`
* `photos_aut_spr_temp/`
* `photos_summer_temp/`

Правило выбора:

* **t < 5°C** → winter
* **6–20°C** → aut/spr
* **≥ 21°C** → summer

---

## 7. Адаптеры и доступ к данным

### Погода: `adapters/weather_api/openweather_client.py`

* `get_forecast_for_city()` — прогноз на день
* `get_two_days_forecast()` — прогноз на 2 дня
* преобразует JSON ответа API в `DayForecast`

### БД пользователей: `adapters/user_bd/`

* `bd.py` — SQLAlchemy engine/session
* `sqlalchemy_user_repo.py` — репозиторий:

  * CRUD по пользователям
  * сохранение `FeedbackRecord`
  * получение списка пользователей для рассылок/уведомлений

---

## 8. Планировщик уведомлений (infra/alerts_scheduler.py)

* Фоновый цикл `run_weather_alerts_loop()`:

  * проверка изменений погоды,
  * дождь в ближайшие часы,
  * отправка уведомлений пользователям.

---

## 9. Поток данных в приложении

1. Пользователь нажимает `/advice` или кнопку меню → `bot/handlers/commands.py`
2. Бот получает `User` из репозитория → `adapters/user_bd/sqlalchemy_user_repo.py`
3. Бот получает прогноз → `adapters/weather_api/openweather_client.py`
4. Движок строит рекомендацию → `recommendation/engine.py`

   * признаки → `ml/features.py`
   * модель → `ml/model_loader.py`
   * персональная адаптация → `ml/online_shift.py` (если есть фидбек)
   * стиль → `bot/handlers/styles/*`
5. Отправка пользователю текста + фото-референсов
6. Фидбек пользователя → запись в БД + апдейт `warmth_shift`

---

## 10. Тестирование

Пакет тестов: `tests/` (pytest)

* `test_commands.py` — хендлеры/команды
* `test_engine.py` — движок рекомендаций
* `test_features.py` — признаки
* `test_model_loader.py` — загрузка модели
* `test_online_shift.py` — обновление `warmth_shift`
* `test_synthetic_dataset.py` — генерация синтетики
