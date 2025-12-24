from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import select

from weather_stylist.adapters.user_bd.bd import engine, FeedbackORM, UserORM
from weather_stylist.ml.features import FEATURE_COLUMNS

K = 1.0  # насколько “сильный” один фидбек
MIN_ROWS = 30  # меньше — смысла мало


def main() -> None:
    # вытаскиваем погоду + label + текущий warmth_shift пользователя
    stmt = (
        select(
            FeedbackORM.temp_min,
            FeedbackORM.temp_max,
            FeedbackORM.wind_max,
            FeedbackORM.will_rain,
            FeedbackORM.thermo_profile,
            UserORM.warmth_shift,
            FeedbackORM.label,
        )
        .join(UserORM, UserORM.tg_id == FeedbackORM.user_tg_id)
    )

    df = pd.read_sql(stmt, engine)

    if len(df) < MIN_ROWS:
        raise RuntimeError(
            f"not enough real feedback rows: {len(df)} < {MIN_ROWS}")

    # will_rain -> 0/1
    df["will_rain"] = df["will_rain"].astype(int)

    df["delta"] = (-df["label"].clip(-1, 1)) * K

    X = df[FEATURE_COLUMNS]
    y = df["delta"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("ridge", Ridge(alpha=1.0)),
    ])
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    print("Delta model MAE:", mean_absolute_error(y_test, y_pred))
    print("Delta model R^2:", r2_score(y_test, y_pred))
    ml_dir = Path(__file__).parent
    out_path = ml_dir / "comfort_delta_regressor.pkl"
    joblib.dump(model, out_path)
    print(f"delta model saved to {out_path}")


if __name__ == "__main__":
    main()
