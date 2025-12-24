from pathlib import Path
from typing import Optional

import joblib

_regressor: Optional[object] = None


def get_regressor():
    """
    загружает и кеширует модель регрессии,
    которая предсказывает required_warmth
    """
    global _regressor

    if _regressor is None:
        model_path = Path(__file__).with_name("comfort_regressor.pkl")
        if not model_path.exists():
            raise FileNotFoundError(
                f"model file not found: {model_path}. "
                f"сначала запусти обучение train_model.py"
            )
        _regressor = joblib.load(model_path)

    return _regressor


_delta_regressor: Optional[object] = None


def try_get_delta_regressor():
    global _delta_regressor

    if _delta_regressor is None:
        model_path = Path(__file__).with_name("comfort_delta_regressor.pkl")
        if not model_path.exists():
            return None
        _delta_regressor = joblib.load(model_path)

    return _delta_regressor
