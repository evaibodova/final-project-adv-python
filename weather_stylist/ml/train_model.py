from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from weather_stylist.ml.features import FEATURE_COLUMNS


def main() -> None:
    ml_dir = Path(__file__).parent
    data_dir = ml_dir / 'data'
    data_path = data_dir / "synthetic_feedback.csv"

    if not data_path.exists():
        raise FileNotFoundError(
            f"dataset not found: {data_path}. "
            f"сначала запусти synthetic_dataset.py"
        )

    df = pd.read_csv(data_path)

    X = df[FEATURE_COLUMNS]
    y = df["required_warmth"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=6,
        random_state=42,
    )

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print("MAE:", mae)
    print("R^2:", r2)

    model_path = ml_dir / "comfort_regressor.pkl"
    joblib.dump(model, model_path)
    print(f"model saved to {model_path}")


if __name__ == "__main__":
    main()
