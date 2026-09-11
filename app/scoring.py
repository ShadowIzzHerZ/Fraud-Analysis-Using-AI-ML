"""Detection engine: a rules layer + a per-card statistical baseline.

Every signal is an explicit, named detector that produces a human-readable
reason — per the PRD, "explainability: every alert must cite detectors, not
only a numeric score." There is no black-box model here; contributions are
additive weights, capped at 1.0, which keeps it fast enough to score on
ingest and easy to reason about live during a demo.
"""
from __future__ import annotations

from typing import Optional

from app.geo import MAX_PLAUSIBLE_KMH, haversine_km, implied_speed_kmh
from app.models import Reason, ScoreResult, Severity, Transaction
from app.state import CardProfile

VELOCITY_WINDOW_S = 60.0
MULE_WINDOW_S = 90.0
MULE_DISTINCT_MERCHANTS = 6
MULE_AVG_AMOUNT_MAX = 2000.0  # ₹

SEVERITY_THRESHOLDS = [
    (0.85, Severity.CRITICAL),
    (0.65, Severity.HIGH),
    (0.40, Severity.MEDIUM),
    (0.0, Severity.LOW),
]


def _severity_for(score: float) -> Severity:
    for threshold, sev in SEVERITY_THRESHOLDS:
        if score >= threshold:
            return sev
    return Severity.LOW


def _detect_amount_outlier(txn: Transaction, profile: CardProfile) -> Optional[tuple[float, Reason]]:
    if profile.n < 5:
        # Not enough history for a z-score yet — fall back to a conservative
        # absolute threshold. Kept as a supporting signal only (not enough to
        # alert alone) so a young card's first big-but-plausible purchase
        # doesn't page an analyst by itself.
        if txn.amount >= 15000:
            return 0.20, Reason("AMOUNT", f"Large amount (₹{txn.amount:,.0f}) with little or no history on this card")
        return None
    z = profile.amount_zscore(txn.amount)
    if z >= 3.6:
        w = 0.45
    elif z >= 2.9:
        w = 0.30
    elif z >= 2.3:
        w = 0.18
    else:
        return None
    return w, Reason(
        "AMOUNT",
        f"Amount ₹{txn.amount:,.0f} is well above this card's usual range (avg ₹{profile.mean_amount:,.0f})",
    )


def _detect_velocity(txn: Transaction, profile: CardProfile) -> Optional[tuple[float, Reason]]:
    prior = [t for t in profile.recent_txn_times if t >= txn.ts - VELOCITY_WINDOW_S]
    count = len(prior) + 1
    if count >= 9:
        w = 0.55
    elif count >= 7:
        w = 0.40
    elif count >= 5:
        w = 0.18
    else:
        return None
    return w, Reason("VELOCITY", f"{count} transactions on this card in the last {int(VELOCITY_WINDOW_S)}s")


def _detect_impossible_travel(txn: Transaction, profile: CardProfile) -> Optional[tuple[float, Reason]]:
    if not profile.last_country or profile.last_country == txn.country or profile.last_ts is None:
        return None
    dt = max(1.0, txn.ts - profile.last_ts)
    speed = implied_speed_kmh(profile.last_country, txn.country, dt)
    if speed <= MAX_PLAUSIBLE_KMH:
        return None
    dist = haversine_km(profile.last_country, txn.country)
    return 0.50, Reason(
        "GEO_JUMP",
        f"{profile.last_country}→{txn.country} ({dist:,.0f} km) in {dt:.0f}s — implies {speed:,.0f} km/h",
    )


def _detect_new_device(txn: Transaction, profile: CardProfile) -> Optional[tuple[float, Reason]]:
    if profile.n < 3 or txn.device_fp in profile.seen_devices:
        return None
    relative = txn.amount / max(profile.mean_amount, 1e-6)
    if relative < 2.5 and txn.amount < 3000:
        return None
    return 0.25, Reason(
        "NEW_DEVICE",
        f"Unrecognized device for this card, amount ₹{txn.amount:,.0f} (avg ₹{profile.mean_amount:,.0f})",
    )


def _detect_mule_burst(txn: Transaction, profile: CardProfile) -> Optional[tuple[float, Reason]]:
    recent = [e for e in profile.recent_events if e[0] >= txn.ts - MULE_WINDOW_S]
    recent = recent + [(txn.ts, txn.merchant, txn.amount)]
    distinct_merchants = {m for _, m, _ in recent}
    if len(distinct_merchants) < MULE_DISTINCT_MERCHANTS:
        return None
    avg_amount = sum(a for _, _, a in recent) / len(recent)
    if avg_amount > MULE_AVG_AMOUNT_MAX:
        return None
    return 0.45, Reason(
        "MULE_BURST",
        f"{len(distinct_merchants)} distinct merchants in {int(MULE_WINDOW_S)}s, avg ₹{avg_amount:,.0f}",
    )


def _detect_unusual_mcc(txn: Transaction, profile: CardProfile) -> Optional[tuple[float, Reason]]:
    if profile.n < 8 or txn.mcc in profile.seen_mccs:
        return None
    return 0.12, Reason("UNUSUAL_MCC", f"Merchant category {txn.mcc} never seen before for this card")


DETECTORS = [
    _detect_amount_outlier,
    _detect_velocity,
    _detect_impossible_travel,
    _detect_new_device,
    _detect_mule_burst,
    _detect_unusual_mcc,
]


def score_transaction(txn: Transaction, profile: CardProfile) -> ScoreResult:
    """Score `txn` against `profile` history. Must be called BEFORE
    profile.observe(txn), so the baseline reflects strictly prior behaviour."""
    hits: list[tuple[float, Reason]] = []
    for detector in DETECTORS:
        result = detector(txn, profile)
        if result is not None:
            hits.append(result)

    hits.sort(key=lambda h: h[0], reverse=True)
    total = min(1.0, sum(w for w, _ in hits))
    reasons = [r for _, r in hits[:4]]
    contributions = {r.detector: w for w, r in hits}

    return ScoreResult(
        risk_score=total,
        severity=_severity_for(total),
        reasons=reasons,
        contributions=contributions,
    )
