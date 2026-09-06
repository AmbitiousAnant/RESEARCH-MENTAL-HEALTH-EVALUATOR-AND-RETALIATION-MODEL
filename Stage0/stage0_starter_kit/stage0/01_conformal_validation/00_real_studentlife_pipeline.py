"""
Stage 0 — Real StudentLife Data Pipeline (not synthetic)
===========================================================
WHAT THIS IS: real ingestion of the actual StudentLife dataset format --
real per-second activity inference logs and real EMA mood responses from
real Dartmouth students, pulled from the dataset's own public GitHub test
fixture (frycast/studentlife). Nothing in the loading/feature/correlation
code below is synthetic.

WHAT THIS IS NOT: a validated finding. This fixture ships only 3 users
(u00-u02) -- it exists in the package to test the R code, not to power a
study. A correlation computed on n=3 has no statistical meaning and none is
claimed below. What IS real: the parsing logic, the feature engineering, and
the fact that this ran against genuine sensor+EMA files rather than data I
invented.

TO GET TO SOMETHING CITABLE: point DATA_DIR at the full 48-student release
(https://studentlife.cs.dartmouth.edu/dataset/dataset.tar.bz2, ~5GB -- not
reachable from this sandboxed environment, but a plain download on your own
machine) and this script requires zero changes. That's deliberate.
"""

import json
import glob
import os
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from scipy import stats

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "real_data", "sl_sample", "dataset")


def load_activity_daily(data_dir):
    """
    Real activity inference logs: timestamp, activity_code (0=still, 1=walk,
    2=run, 3=unknown, per StudentLife's published codebook). Aggregates to
    a real per-user-per-day 'active fraction' -- share of logged samples
    that were not stationary.
    """
    rows = []
    for path in glob.glob(os.path.join(data_dir, "sensing", "activity", "activity_*.csv")):
        user = os.path.basename(path).replace("activity_", "").replace(".csv", "")
        df = pd.read_csv(path, names=["timestamp", "activity"], header=0,
                          skipinitialspace=True, on_bad_lines="skip")
        df = df.dropna(subset=["timestamp", "activity"])
        df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
        df["activity"] = pd.to_numeric(df["activity"], errors="coerce")
        df = df.dropna()
        df["date"] = df["timestamp"].apply(lambda t: datetime.fromtimestamp(t, tz=timezone.utc).date())
        daily = df.groupby("date")["activity"].apply(lambda s: (s > 0).mean()).reset_index()
        daily.columns = ["date", "active_fraction"]
        daily["user"] = user
        rows.append(daily)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def load_mood_daily(data_dir):
    """
    Real PAM (Photographic Affect Meter) EMA responses: self-reported
    happy/sad scale values with a unix response time. Aggregates to a real
    per-user-per-day net-affect score (happy minus sad, both 1-4 scales).
    """
    rows = []
    for path in glob.glob(os.path.join(data_dir, "EMA", "response", "Mood", "Mood_*.json")):
        user = os.path.basename(path).replace("Mood_", "").replace(".json", "")
        with open(path) as f:
            entries = json.load(f)
        for e in entries:
            try:
                happy = float(e.get("happy", np.nan))
                sad = float(e.get("sad", np.nan))
                ts = int(e["resp_time"])
            except (TypeError, ValueError, KeyError):
                continue
            date = datetime.fromtimestamp(ts, tz=timezone.utc).date()
            rows.append({"user": user, "date": date, "net_affect": happy - sad})
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return df.groupby(["user", "date"])["net_affect"].mean().reset_index()


def main():
    print("=" * 66)
    print("STAGE 0 — REAL STUDENTLIFE DATA (n=3 sample fixture)")
    print("=" * 66)

    activity = load_activity_daily(DATA_DIR)
    mood = load_mood_daily(DATA_DIR)

    print(f"Real activity-log rows aggregated to {len(activity)} user-days")
    print(f"Real mood EMA rows aggregated to {len(mood)} user-days")

    merged = pd.merge(activity, mood, on=["user", "date"], how="inner")
    print(f"User-days with BOTH signals on the same day: {len(merged)}")
    print(f"Distinct users: {sorted(merged['user'].unique().tolist())}")

    if len(merged) < 5:
        print("\nToo few overlapping user-days in this 3-user fixture to even")
        print("compute a meaningful correlation coefficient. Printing what")
        print("exists so the real numbers are visible, not hidden:")
        print(merged.to_string(index=False))
    else:
        r, p = stats.pearsonr(merged["active_fraction"], merged["net_affect"])
        print(f"\nPearson r (active_fraction vs net_affect): {r:.3f}  (p={p:.3f}, n={len(merged)})")
        print("n this small -> do not read the sign or magnitude as a finding.")
        print("What's real: this number came from genuine sensor and EMA files,")
        print("not a generator function. The full 48-student release is what")
        print("would make this number mean something.")

    print("=" * 66)


if __name__ == "__main__":
    main()
