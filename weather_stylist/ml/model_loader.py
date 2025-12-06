from pathlib import Path
from typing import Optional

import joblib

_regressor = None  # type: Optional[object]


def get_regressor():
    """
    лениво загружает и кеширует модель регрессии,
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
