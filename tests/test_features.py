from weather_stylist.ml.features import FEATURE_COLUMNS, make_features
from tests.conftest import DummyForecast, DummyUser


def test_make_features_basic():
    forecast = DummyForecast(min_temp=-5, max_temp=0, wind_max=8.5, will_rain=True)
    user = DummyUser(thermo_profile=-1, warmth_shift=0.5)

    feats = make_features(forecast, user)

    assert len(feats) == len(FEATURE_COLUMNS)
    assert feats[0] == -5
    assert feats[1] == 0
    assert feats[2] == 8.5
    assert feats[4] == -1.0
    assert feats[5] == 0.5


def test_make_features_rain_encoding():
    forecast = DummyForecast(min_temp=10, max_temp=15, wind_max=3, will_rain=False)
    user = DummyUser(thermo_profile=0, warmth_shift=0.0)

    feats = make_features(forecast, user)

    assert feats[3] == 0.0