from weather_stylist.domain.user import UserProfile


ALPHA_BASE = 0.5


def update_warmth_shift(user: UserProfile, label: int) -> UserProfile:
    """
    label:
      -1 = было холодно  -> сделать теплее
       0 = норм          -> не менять
      +1 = было жарко    -> сделать прохладнее

    обновляет user.warmth_shift и счётчики.
    """

    user.feedback_count += 1

    if label == -1:
        user.cold_count += 1
    elif label == 1:
        user.hot_count += 1
    denom = user.feedback_count ** 0.5
    if denom < 1.0:
        denom = 1.0

    alpha = ALPHA_BASE / denom

    if label == -1:
        user.warmth_shift += alpha
    elif label == 1:
        user.warmth_shift -= alpha

    return user
