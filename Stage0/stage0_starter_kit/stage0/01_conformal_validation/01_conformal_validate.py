"""
Stage 0 — Conformal Coverage Validation
=========================================
Gate this satisfies (paper Section 4.3, Stage table, row 0): "Coverage holds."

WHAT THIS PROVES RIGHT NOW: the conformal-prediction *methodology* Sentinel's
detection layer depends on actually delivers the coverage guarantee it claims,
mechanically. That's a real, checkable result today.

WHAT THIS DOES NOT PROVE YET: that Sentinel's *specific* features correlate
with real distress the way the synthetic generator below assumes. That claim
still needs real data (see the StudentLife replication step in the README).
The synthetic generator is built to have the same *shape* as what Saeb et al.
and StudentLife reported (sleep/mobility/screen-time direction of effect) so
this script is a faithful rehearsal of the real analysis, not a toy unrelated
to it. Swap load_synthetic_cohort() for a real feature table and everything
downstream is unchanged.

Run: python3 01_conformal_validate.py
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RNG = np.random.default_rng(42)
TARGET_COVERAGE = 0.90  # matches the paper's stated conformal coverage target


def load_synthetic_cohort(n=1200):
    """
    Generates a synthetic cohort with the SAME feature set Section 3.2 specifies
    (sleep, app usage, mobility-proxy, keystroke-derived affect) and a distress
    score whose relationship to those features follows the DIRECTION reported
    in Saeb et al. [3] and StudentLife [4] -- less/irregular sleep, more erratic
    app usage, and higher "restlessness" all push distress up -- plus a
    per-person baseline offset (everyone has a different resting state, which
    is why Sentinel scores against a personal 7-14 day baseline, not a
    population norm) and realistic noise so the correlation is real but not
    trivially perfect.
    """
    sleep_hours = RNG.normal(6.5, 1.3, n).clip(2, 11)
    sleep_irregularity = RNG.gamma(2.0, 0.6, n)  # night-to-night variance proxy
    social_app_min = RNG.gamma(3.0, 25, n)
    app_switch_rate = RNG.gamma(2.5, 4.0, n)  # unlocks/hour, a restlessness proxy
    keystroke_latency_var = RNG.gamma(2.0, 0.8, n)  # BiAffect-style typing variability
    person_baseline = RNG.normal(0, 6, n)  # stable individual offset

    distress = (
        30
        + person_baseline
        - 2.1 * (sleep_hours - 7.0)
        + 4.0 * sleep_irregularity
        + 0.06 * social_app_min
        + 1.8 * app_switch_rate
        + 3.2 * keystroke_latency_var
        + RNG.normal(0, 7, n)  # irreducible noise
    ).clip(0, 100)

    return pd.DataFrame({
        "sleep_hours": sleep_hours,
        "sleep_irregularity": sleep_irregularity,
        "social_app_min": social_app_min,
        "app_switch_rate": app_switch_rate,
        "keystroke_latency_var": keystroke_latency_var,
        "distress_score": distress,
    })


def split_conformal_intervals(model, X_calib, y_calib, X_test, coverage=TARGET_COVERAGE):
    """
    Standard split-conformal regression, implemented by hand (no library) so
    the mechanism is fully visible rather than a black-box call:
      1. score residuals on a held-out calibration set the model never trained on
      2. take the (1-alpha)-quantile of |residual|, with the small-sample
         finite-correction (ceil((n+1)*coverage)/n) rather than a naive quantile
      3. every test prediction gets the SAME half-width -- that's what makes
         the coverage guarantee distribution-free and mathematically guaranteed
         (not just "usually works")
    """
    calib_preds = model.predict(X_calib)
    residuals = np.abs(y_calib - calib_preds)
    n = len(residuals)
    q_level = min(np.ceil((n + 1) * coverage) / n, 1.0)
    half_width = np.quantile(residuals, q_level)

    test_preds = model.predict(X_test)
    lower = test_preds - half_width
    upper = test_preds + half_width
    return test_preds, lower, upper, half_width


def main():
    df = load_synthetic_cohort()
    features = ["sleep_hours", "sleep_irregularity", "social_app_min", "app_switch_rate", "keystroke_latency_var"]
    X, y = df[features], df["distress_score"]

    # Three-way split: train the model / calibrate the intervals / test coverage.
    # Calibration MUST be data the model never trained on -- reusing training
    # residuals is the single most common way people accidentally break the
    # coverage guarantee, so it's kept as a hard separate split here on purpose.
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.5, random_state=42)
    X_calib, X_test, y_calib, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

    model = RandomForestRegressor(n_estimators=200, max_depth=6, random_state=42)
    model.fit(X_train, y_train)

    # --- The claim Section 2.5 makes: point accuracy alone is misleading ---
    point_preds = model.predict(X_test)
    mae = np.mean(np.abs(point_preds - y_test))
    r2 = model.score(X_test, y_test)

    # --- The claim Section 4.3's gate actually requires: does coverage hold? ---
    preds, lower, upper, half_width = split_conformal_intervals(model, X_calib, y_calib, X_test)
    covered = (y_test.values >= lower) & (y_test.values <= upper)
    empirical_coverage = covered.mean()

    print("=" * 62)
    print("STAGE 0 — CONFORMAL COVERAGE VALIDATION (synthetic cohort)")
    print("=" * 62)
    print(f"Cohort size:              {len(df)}  (train={len(X_train)} / calib={len(X_calib)} / test={len(X_test)})")
    print(f"Point-accuracy framing:   MAE={mae:.2f}, R^2={r2:.3f}")
    print(f"  -> looks precise. This is exactly the framing Section 2.5 warns")
    print(f"     against treating as the headline result.")
    print()
    print(f"Target coverage:          {TARGET_COVERAGE:.0%}")
    print(f"Empirical coverage:       {empirical_coverage:.1%}  (n={len(y_test)} test points)")
    print(f"Interval half-width:      +/- {half_width:.2f} distress-score points")
    print()
    gate_passed = abs(empirical_coverage - TARGET_COVERAGE) <= 0.03
    print(f"GATE (Stage table, row 0): {'PASS' if gate_passed else 'FAIL'} "
          f"-- {'within' if gate_passed else 'outside'} 3pp of the {TARGET_COVERAGE:.0%} target")
    print("=" * 62)

    # Plot: sorted by prediction, showing interval + whether it actually covered truth
    order = np.argsort(preds)
    fig, ax = plt.subplots(figsize=(9, 5))
    idx = np.arange(len(order))
    ax.fill_between(idx, lower[order], upper[order], alpha=0.25, color="#2E5257", label=f"{TARGET_COVERAGE:.0%} conformal interval")
    ax.plot(idx, preds[order], color="#2E5257", lw=1, label="point prediction")
    miss = ~covered[order]
    ax.scatter(idx[~miss], y_test.values[order][~miss], s=10, color="#4E9C93", label="actual (covered)", zorder=3)
    ax.scatter(idx[miss], y_test.values[order][miss], s=16, color="#B5651D", label="actual (missed)", zorder=4)
    ax.set_xlabel("test cases, sorted by predicted score")
    ax.set_ylabel("distress score (0-100)")
    ax.set_title(f"Split-conformal intervals: {empirical_coverage:.1%} empirical coverage vs {TARGET_COVERAGE:.0%} target")
    ax.legend(loc="upper left", fontsize=8)
    plt.tight_layout()
    plt.savefig("conformal_coverage_result.png", dpi=150)
    print("\nSaved: conformal_coverage_result.png")


if __name__ == "__main__":
    main()
