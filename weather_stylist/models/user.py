from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    tg_id: int
    city: str
    name: str
    region: str
    thermo_profile: int  # -1 - i'm cold, 0 - i'm ok, +1 - i'm hot
    warmth_shift: float
    feedback_count: int
    cold_count: int
    hot_count: int


@dataclass
class FeedbackRecord:
    user_tg_id: int
    created_at: datetime
    temp_min: float
    temp_max: float
    wind_max: float
    will_rain: bool
    thermo_profile: int
    outfit_code: str
    label: int
