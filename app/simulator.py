"""The transaction firehose: a simulator that behaves like a payment gateway.

Generates a steady baseline of plausible card traffic across a large-enough
card population that legitimate velocity stays low, plus four "inject"
scenarios (velocity spike, amount outlier, impossible travel, mule burst)
that each produce a believable pre-timed burst of events for the detection
engine in `app/scoring.py` to catch.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

from app.geo import COUNTRY_CODES
from app.models import Alert, AlertStatus, Channel, Transaction, new_id
from app.scoring import score_transaction
from app.state import AppState, state

CARD_POOL_SIZE = 1000

# (display name, mcc, category) — category drives amount range + channel mix
MERCHANTS: list[tuple[str, str, str]] = [
    ("Green Valley Grocers", "5411", "grocery"),
    ("Corner Bistro", "5812", "restaurant"),
    ("QuickFuel Station", "5541", "fuel"),
    ("Circuit City Electronics", "5732", "electronics"),
    ("SkyLine Airways", "4511", "travel"),
    ("Harborview Hotel", "7011", "hotel"),
    ("StreamPlus Subscription", "5968", "subscription"),
    ("MarketHub Online", "5969", "online_marketplace"),
    ("CarePoint Pharmacy", "5912", "pharmacy"),
    ("Metro ATM Network", "6011", "atm"),
    ("Aurelia Jewellers", "5944", "luxury"),
    ("RideNow", "4121", "rideshare"),
    ("CityPower Utilities", "4900", "utilities"),
    ("Thread & Co Apparel", "5651", "clothing"),
    ("Bean There Coffee", "5814", "restaurant"),
    ("HomeGoods Depot", "5200", "home"),
]

CATEGORY_AMOUNT_RANGE = {
    "grocery": (15, 140),
    "restaurant": (8, 90),
    "fuel": (25, 100),
    "electronics": (60, 1200),
    "travel": (150, 1800),
    "hotel": (90, 950),
    "subscription": (5, 60),
    "online_marketplace": (10, 400),
    "pharmacy": (8, 120),
    "atm": (40, 400),
    "luxury": (200, 6000),
    "rideshare": (6, 55),
    "utilities": (30, 220),
    "clothing": (15, 260),
    "home": (20, 500),
}

CATEGORY_ONLINE_BIAS = {
    "subscription": 0.98, "online_marketplace": 0.9, "travel": 0.6, "hotel": 0.5,
    "electronics": 0.4, "clothing": 0.5, "utilities": 0.7, "rideshare": 0.05,
    "grocery": 0.05, "restaurant": 0.05, "fuel": 0.02, "pharmacy": 0.1,
    "atm": 0.0, "luxury": 0.3, "home": 0.4,
}

CURRENCY_BY_COUNTRY = {
    "US": "USD", "GB": "GBP", "DE": "EUR", "FR": "EUR", "IN": "INR", "BR": "BRL",
    "AU": "AUD", "JP": "JPY", "NG": "NGN", "CN": "CNY", "RU": "RUB", "ZA": "ZAR",
    "CA": "CAD", "MX": "MXN", "AE": "AED", "SG": "SGD",
}


@dataclass
class SimCard:
    card_token: str
    user_id: str
    home_country: str
    devices: list[str]
    base_amount: float
    mcc_habits: list[str]


def _make_card(i: int) -> SimCard:
    home = random.choice(COUNTRY_CODES)
    n_devices = 1 if random.random() < 0.8 else 2
    devices = [f"dev_{random.randrange(16**8):08x}" for _ in range(n_devices)]
    base_amount = random.choice([20, 35, 55, 80, 120, 180, 300])
    habits = random.sample([m[1] for m in MERCHANTS], k=random.randint(3, 6))
    return SimCard(
        card_token=f"tok_{i:05d}",
        user_id=f"usr_{i:05d}",
        home_country=home,
        devices=devices,
        base_amount=base_amount,
        mcc_habits=habits,
    )


CARDS: list[SimCard] = [_make_card(i) for i in range(CARD_POOL_SIZE)]
CARD_BY_TOKEN = {c.card_token: c for c in CARDS}


def _pick_merchant(card: SimCard) -> tuple[str, str, str]:
    if random.random() < 0.7:
        candidates = [m for m in MERCHANTS if m[1] in card.mcc_habits]
        if candidates:
            return random.choice(candidates)
    return random.choice(MERCHANTS)


def _amount_for(category: str, base: float) -> float:
    lo, hi = CATEGORY_AMOUNT_RANGE[category]
    mid = max(lo, min(hi, base))
    amt = random.lognormvariate(_safe_ln(mid), 0.45)
    return round(max(lo * 0.5, min(hi * 1.5, amt)), 2)


def _safe_ln(x: float) -> float:
    import math
    return math.log(max(x, 1.0))


def _channel_for(category: str) -> Channel:
    p_online = CATEGORY_ONLINE_BIAS.get(category, 0.2)
    return Channel.ONLINE if random.random() < p_online else Channel.CARD_PRESENT


def generate_normal_transaction(now: float) -> Transaction:
    card = random.choice(CARDS)
    name, mcc, category = _pick_merchant(card)
    amount = _amount_for(category, card.base_amount)
    country = card.home_country
    # rare legitimate foreign transaction, only once it's been a while since
    # this card's last event (keeps baseline velocity/geo noise low)
    profile = state.profile_for(card.card_token)
    if profile.last_ts is not None and (now - profile.last_ts) > 600 and random.random() < 0.02:
        country = random.choice(COUNTRY_CODES)
    device = random.choice(card.devices) if random.random() > 0.015 else f"dev_{random.randrange(16**8):08x}"
    return Transaction(
        id=new_id("txn"),
        ts=now,
        amount=amount,
        currency=CURRENCY_BY_COUNTRY.get(country, "USD"),
        merchant=name,
        mcc=mcc,
        channel=_channel_for(category),
        country=country,
        device_fp=device,
        card_token=card.card_token,
        user_id=card.user_id,
    )


def _seasoned_card() -> SimCard:
    """Pick a card with enough transaction history for its baseline to be
    meaningful — real card-fraud victims are established accounts, not blank
    ones, and this is also what lets the amount-outlier detector's z-score
    fire reliably instead of falling back to a weak cold-start heuristic."""
    candidates = [c for c in CARDS if state.profile_for(c.card_token).n >= 8]
    return random.choice(candidates) if candidates else random.choice(CARDS)


# -- attack scenarios ---------------------------------------------------------

def _mk(card: SimCard, ts: float, name: str, mcc: str, category: str, amount: float,
        scenario: str, country: str | None = None, device: str | None = None) -> Transaction:
    country = country or card.home_country
    return Transaction(
        id=new_id("txn"),
        ts=ts,
        amount=round(amount, 2),
        currency=CURRENCY_BY_COUNTRY.get(country, "USD"),
        merchant=name,
        mcc=mcc,
        channel=_channel_for(category),
        country=country,
        device_fp=device or random.choice(card.devices),
        card_token=card.card_token,
        user_id=card.user_id,
        scenario=scenario,
    )


def inject_velocity(now: float) -> list[tuple[float, Transaction]]:
    card = _seasoned_card()
    out = []
    t = now
    for _ in range(random.randint(7, 10)):
        name, mcc, category = random.choice(MERCHANTS)
        amount = _amount_for(category, card.base_amount)
        out.append((t, _mk(card, t, name, mcc, category, amount, "velocity")))
        t += random.uniform(2.0, 4.5)
    return out


def inject_amount_outlier(now: float) -> list[tuple[float, Transaction]]:
    card = _seasoned_card()
    profile = state.profile_for(card.card_token)
    baseline = max(profile.mean_amount, card.base_amount)
    name, mcc, category = random.choice([m for m in MERCHANTS if m[2] in ("luxury", "electronics", "travel")])
    amount = baseline * random.uniform(12, 22) + random.uniform(1200, 3500)
    return [(now + 0.5, _mk(card, now + 0.5, name, mcc, category, amount, "amount_outlier"))]


def inject_impossible_travel(now: float) -> list[tuple[float, Transaction]]:
    card = _seasoned_card()
    name1, mcc1, cat1 = _pick_merchant(card)
    far_countries = [c for c in COUNTRY_CODES if c != card.home_country]
    far = random.choice(far_countries)
    t1 = now
    t2 = now + random.uniform(20, 70)
    first = _mk(card, t1, name1, mcc1, cat1, _amount_for(cat1, card.base_amount), "impossible_travel",
                country=card.home_country)
    name2, mcc2, cat2 = random.choice(MERCHANTS)
    second = _mk(card, t2, name2, mcc2, cat2, _amount_for(cat2, card.base_amount), "impossible_travel",
                  country=far, device=f"dev_{random.randrange(16**8):08x}")
    return [(t1, first), (t2, second)]


def inject_mule_burst(now: float) -> list[tuple[float, Transaction]]:
    card = _seasoned_card()
    out = []
    t = now
    used_names = random.sample(MERCHANTS, k=min(len(MERCHANTS), random.randint(7, 9)))
    for name, mcc, category in used_names:
        amount = random.uniform(8, 45)
        out.append((t, _mk(card, t, name, mcc, category, amount, "mule_burst")))
        t += random.uniform(6.0, 11.0)
    return out


SCENARIOS = {
    "velocity": ("Velocity spike", inject_velocity),
    "amount_outlier": ("Amount outlier", inject_amount_outlier),
    "impossible_travel": ("Impossible travel", inject_impossible_travel),
    "mule_burst": ("Mule burst", inject_mule_burst),
}


def inject_scenario(name: str) -> int:
    """Queue a scenario's events and temporarily raise ambient throughput.
    Returns the number of events queued."""
    _, fn = SCENARIOS[name]
    now = time.time()
    events = fn(now)
    state.pending_events.extend(events)
    state.pending_events.sort(key=lambda e: e[0])
    state.sim.burst_until = max(state.sim.burst_until, now + 12.0)
    return len(events)


# -- ingest pipeline ---------------------------------------------------------

def process_transaction(txn: Transaction, st: AppState = state) -> None:
    profile = st.profile_for(txn.card_token)
    result = score_transaction(txn, profile)
    profile.observe(txn)  # AFTER scoring: baseline must reflect prior history only
    st.add_transaction(txn, result)

    if result.risk_score < 0.40:
        return

    alert = Alert(id=new_id("alrt"), transaction=txn, score=result)
    if st.policy.auto_freeze_enabled and result.risk_score >= st.policy.auto_freeze_threshold:
        alert.status = AlertStatus.FROZEN
        alert.log(f"Auto-frozen by policy (score ≥ {st.policy.auto_freeze_threshold:.2f})")
        st.frozen_total += 1
    st.add_alert(alert)


def tick(st: AppState = state) -> None:
    """Advance the simulator by one tick: emit due scenario events, and roll
    the dice for `rate * tick_seconds` fresh baseline transactions."""
    now = time.time()

    due = [e for e in st.pending_events if e[0] <= now]
    if due:
        st.pending_events = [e for e in st.pending_events if e[0] > now]
        due.sort(key=lambda e: e[0])
        for _, txn in due:
            process_transaction(txn, st)

    if not st.sim.running:
        return

    rate = st.sim.burst_rate if now < st.sim.burst_until else st.sim.base_rate
    expected = rate * st.sim.tick_seconds
    n = int(expected)
    if random.random() < (expected - n):
        n += 1
    for _ in range(n):
        process_transaction(generate_normal_transaction(now), st)
