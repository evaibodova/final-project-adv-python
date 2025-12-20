from weather_stylist.ml.model_loader import get_regressor


def test_get_regressor_returns_same_instance():
    model1 = get_regressor()
    model2 = get_regressor()

    assert model1 is model2
    assert hasattr(model1, "predict")
