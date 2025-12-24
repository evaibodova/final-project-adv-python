import csv
import random
from pathlib import Path

from weather_stylist.ml.features import FEATURE_COLUMNS


def rule_based_required_warmth(
        temp_min: float,
        temp_max: float,
        wind_max: float,
        will_rain: int,
        thermo_profile: int,
) -> float:

    t = temp_max
    base = 0.0
    if t <= -25:
        base = 20.0
    if t <= -15:
        base = 15.0
    elif t <= -5:
        base = 11.0
    elif t <= 3:
        base = 7.0
    elif t <= 10:
        base = 6.0
    elif t <= 18:
        base = 4.0
    else:
        base = 2.0
    if wind_max >= 10.0:
        base += 1.0
    if will_rain == 1:
        base += 1.0
    if thermo_profile == -1:
        base += 1.0
    elif thermo_profile == 1:
        base -= 1.0

    return base


def random_weather():
    temp_max = random.randint(-20, 35)
    delta = random.randint(0, 10)
    temp_min = temp_max - delta
    if temp_min < -30:
        temp_min = -30
    wind_max = random.uniform(0.0, 15.0)
    will_rain = random.choice([0, 1])

    return temp_min, temp_max, wind_max, will_rain


def random_thermo_profile() -> int:
    return random.choice([-1, 0, 1])


def generate_synthetic_dataset(n_samples: int = 5000) -> None:
    ml_dir = Path(__file__).parent
    data_dir = ml_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    out_path = data_dir / "synthetic_feedback.csv"

    fieldnames = FEATURE_COLUMNS + ["required_warmth"]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for _ in range(n_samples):
            temp_min, temp_max, wind_max, will_rain = random_weather()
            thermo_profile = random_thermo_profile()
            warmth_shift = 0.0

            required = rule_based_required_warmth(
                temp_min=temp_min,
                temp_max=temp_max,
                wind_max=wind_max,
                will_rain=will_rain,
                thermo_profile=thermo_profile,
            )

            row = {
                "temp_min": temp_min,
                "temp_max": temp_max,
                "wind_max": wind_max,
                "will_rain": will_rain,
                "thermo_profile": thermo_profile,
                "warmth_shift": warmth_shift,
                "required_warmth": required,
            }
            writer.writerow(row)

        print(f"synthetic dataset saved to {out_path}")


if __name__ == "__main__":
    generate_synthetic_dataset(5000)
