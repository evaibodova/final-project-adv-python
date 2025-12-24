from weather_stylist.ml.online_shift import update_warmth_shift, ALPHA_BASE
from tests.conftest import DummyUser


def test_update_warmth_shift_cold_feedback():
    user = DummyUser(warmth_shift=0.0, feedback_count=0)

    updated = update_warmth_shift(user, label=-1)

    assert updated.feedback_count == 1
    assert updated.cold_count == 1
    assert updated.warmth_shift == ALPHA_BASE


def test_update_warmth_shift_hot_feedback():
    user = DummyUser(warmth_shift=0.0, feedback_count=0)

    updated = update_warmth_shift(user, label=1)

    assert updated.feedback_count == 1
    assert updated.hot_count == 1
    assert updated.warmth_shift == -ALPHA_BASE


def test_update_warmth_shift_neutral_feedback():
    user = DummyUser(warmth_shift=0.3, feedback_count=2)

    updated = update_warmth_shift(user, label=0)

    assert updated.feedback_count == 3
    assert updated.warmth_shift == 0.3