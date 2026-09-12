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

# (display name, mcc, category) — category drives amount range + channel mix.
# Vendors are fictional but India-flavored, matching the CURRENCY below.
# Several vendors per category (not just one canonical one) so the "prefer a
# merchant this card has shopped at before" logic in _pick_merchant actually
# has real variety to draw from, and enough categories to give the live
# stream a believable everyday spread rather than a handful of repeats.
MERCHANTS: list[tuple[str, str, str]] = [
    # grocery
    ("Sabzi Mandi Grocers", "5411", "grocery"),
    ("BigBasket", "5411", "grocery"),
    ("Reliance Fresh", "5411", "grocery"),
    ("JioMart", "5411", "grocery"),
    ("DMart", "5411", "grocery"),
    ("More Supermarket", "5411", "grocery"),
    # restaurant
    ("Dilli Darbar Dhaba", "5812", "restaurant"),
    ("Chai Tapri Café", "5814", "restaurant"),
    ("Pizza Junction India", "5812", "restaurant"),
    ("Swiggy", "5812", "restaurant"),
    ("Zomato", "5812", "restaurant"),
    ("Domino's Pizza", "5812", "restaurant"),
    ("Barbeque Nation", "5812", "restaurant"),
    # fuel
    ("Bharat Petrol Pump", "5541", "fuel"),
    ("HP Highway Fuel Station", "5541", "fuel"),
    ("Indian Oil Petrol Pump", "5541", "fuel"),
    ("Shell Fuel Station", "5541", "fuel"),
    # electronics
    ("Lotus Electronics Bazaar", "5732", "electronics"),
    ("Croma", "5732", "electronics"),
    ("Reliance Digital", "5732", "electronics"),
    ("Vijay Sales", "5732", "electronics"),
    # travel
    ("Garuda Airways", "4511", "travel"),
    ("IRCTC Rail Booking", "4112", "travel"),
    ("MakeMyStay Travels", "4722", "travel"),
    ("MakeMyTrip", "4722", "travel"),
    ("Yatra", "4722", "travel"),
    ("IndiGo Airlines", "4511", "travel"),
    # hotel
    ("Taj Vista Hotel", "7011", "hotel"),
    ("OYO Comfort Rooms", "7011", "hotel"),
    ("Airbnb Stay", "7011", "hotel"),
    ("Lemon Tree Hotels", "7011", "hotel"),
    # subscription
    ("StreamPlus India", "5968", "subscription"),
    ("PlayFlix OTT", "5968", "subscription"),
    ("Netflix", "5968", "subscription"),
    ("Spotify", "5968", "subscription"),
    ("JioCinema", "5968", "subscription"),
    # online_marketplace
    ("DesiMarket Online", "5969", "online_marketplace"),
    ("Amazon.in", "5969", "online_marketplace"),
    ("Flipkart", "5969", "online_marketplace"),
    ("Tata CLiQ", "5969", "online_marketplace"),
    ("Meesho", "5969", "online_marketplace"),
    # pharmacy
    ("Apollo CarePoint Pharmacy", "5912", "pharmacy"),
    ("MedPlus Wellness Store", "5912", "pharmacy"),
    ("PharmEasy", "5912", "pharmacy"),
    ("1mg", "5912", "pharmacy"),
    # atm
    ("Bharat ATM Network", "6011", "atm"),
    ("SBI ATM", "6011", "atm"),
    ("HDFC Bank ATM", "6011", "atm"),
    # luxury
    ("Rajwada Jewellers", "5944", "luxury"),
    ("Royal Timepieces Boutique", "5944", "luxury"),
    ("Tanishq", "5944", "luxury"),
    ("Kalyan Jewellers", "5944", "luxury"),
    # rideshare
    ("RideNow India", "4121", "rideshare"),
    ("QuickCab Rides", "4121", "rideshare"),
    ("Ola Cabs", "4121", "rideshare"),
    ("Uber", "4121", "rideshare"),
    # utilities
    ("CityLight Power Utilities", "4900", "utilities"),
    ("BharatGas Cylinder Booking", "4900", "utilities"),
    ("Airtel Bill Pay", "4900", "utilities"),
    ("Tata Power", "4900", "utilities"),
    # clothing
    ("Thread & Co. Apparel India", "5651", "clothing"),
    ("Myntra", "5651", "clothing"),
    ("Reliance Trends", "5651", "clothing"),
    ("Ajio", "5651", "clothing"),
    ("Urban Threads Fashion", "5651", "clothing"),
    ("Pantaloons", "5651", "clothing"),
    # home
    ("Ghar Decor Home Store", "5200", "home"),
    ("Furnish & Co. Furniture", "5712", "home"),
    ("Pepperfry", "5712", "home"),
    ("Urban Ladder", "5712", "home"),
    # entertainment
    ("PVR CineMax", "7832", "entertainment"),
    ("Inox Movie Lounge", "7832", "entertainment"),
    ("BookMyShow", "7832", "entertainment"),
    # education
    ("BrightMinds Learning Center", "8299", "education"),
    ("BYJU'S Learning", "8299", "education"),
    ("Unacademy", "8299", "education"),
    # fitness
    ("FitZone Gym & Wellness", "7997", "fitness"),
    ("PowerHouse CrossFit Studio", "7997", "fitness"),
    ("Cult.fit", "7997", "fitness"),
    # salon
    ("Glow Salon & Spa", "7230", "salon"),
    ("Naturals Salon", "7230", "salon"),
    ("Lakmé Salon", "7230", "salon"),
    # pet_care
    ("Pawsome Pet Store", "5995", "pet_care"),
    ("Woof & Whiskers Pet Clinic", "0742", "pet_care"),
    # bakery
    ("Sweet Treats Bakery", "5462", "bakery"),
    ("Theobroma Bakery", "5462", "bakery"),
    ("Monginis", "5462", "bakery"),
]

# All amounts are ₹ (INR) — realistic everyday Indian price levels per category.
CATEGORY_AMOUNT_RANGE = {
    "grocery": (150, 3000),
    "restaurant": (100, 2500),
    "fuel": (300, 4000),
    "electronics": (1000, 80000),
    "travel": (1500, 25000),
    "hotel": (1200, 18000),
    "subscription": (99, 999),
    "online_marketplace": (150, 12000),
    "pharmacy": (80, 3000),
    "atm": (500, 15000),
    "luxury": (3000, 300000),
    "rideshare": (60, 800),
    "utilities": (300, 6000),
    "clothing": (250, 8000),
    "home": (400, 20000),
    "entertainment": (150, 1500),
    "education": (500, 15000),
    "fitness": (500, 5000),
    "salon": (300, 4000),
    "pet_care": (200, 3000),
    "bakery": (100, 1200),
}

CATEGORY_ONLINE_BIAS = {
    "subscription": 0.98, "online_marketplace": 0.9, "travel": 0.6, "hotel": 0.5,
    "electronics": 0.4, "clothing": 0.5, "utilities": 0.7, "rideshare": 0.05,
    "grocery": 0.05, "restaurant": 0.05, "fuel": 0.02, "pharmacy": 0.1,
    "atm": 0.0, "luxury": 0.3, "home": 0.4,
    "entertainment": 0.3, "education": 0.6, "fitness": 0.2, "salon": 0.05,
    "pet_care": 0.3, "bakery": 0.1,
}

CURRENCY = "INR"


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
    base_amount = random.choice([300, 600, 1000, 1800, 3000, 5000, 9000])
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


def _random_ip() -> str:
    return f"{random.randrange(10, 223)}.{random.randrange(0, 255)}.{random.randrange(0, 255)}.{random.randrange(1, 255)}"


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
        currency=CURRENCY,
        merchant=name,
        mcc=mcc,
        channel=_channel_for(category),
        country=country,
        device_fp=device,
        card_token=card.card_token,
        user_id=card.user_id,
        ip=_random_ip(),
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
        currency=CURRENCY,
        merchant=name,
        mcc=mcc,
        channel=_channel_for(category),
        country=country,
        device_fp=device or random.choice(card.devices),
        card_token=card.card_token,
        user_id=card.user_id,
        ip=_random_ip(),
        scenario=scenario,
    )


AMBIENT_ANOMALY_MERCHANTS = [m for m in MERCHANTS if m[2] in ("luxury", "electronics", "travel", "online_marketplace")]


def _freshly_active_card_token(now: float, window: float = 4.0) -> str | None:
    """A card whose last transaction was within `window` seconds of `now` —
    good raw material for a same-tick impossible-travel anomaly, which
    (unlike AMOUNT/NEW_DEVICE) needs no seasoning: GEO_JUMP fires off a
    single prior event, so it works even seconds into a brand-new stream,
    before any card has built up the n>=5-8 history the other signals need."""
    candidates = [tok for tok, p in state.card_profiles.items() if p.last_ts is not None and now - p.last_ts < window]
    return random.choice(candidates) if candidates else None


def generate_ambient_anomaly(now: float) -> Transaction:
    """A single standalone suspicious transaction, woven into ordinary
    background traffic at `state.sim.ambient_fraud_pct`% (see console/
    simulation controls) — distinct from the deliberate multi-event
    "Inject Attack" scenarios, this is just one transaction that actually
    crosses the 0.40 alert threshold on its own, so a plain run (nobody
    clicking Inject) still produces some alerts organically instead of
    scoring silently below the floor.

    Prefers a same-country-flip GEO_JUMP (weight 0.50, needs only one prior
    transaction on the card) over an AMOUNT+NEW_DEVICE combo (needs a
    seasoned card, n>=5ish, for AMOUNT's real z-score branch instead of its
    weak cold-start fallback) — early in a fresh stream, before any card has
    that much history, GEO_JUMP is the only signal that can reliably alert
    on a single isolated event."""
    recent_token = _freshly_active_card_token(now)
    if recent_token is not None:
        card = CARD_BY_TOKEN[recent_token]
        profile = state.profile_for(card.card_token)
        far_countries = [c for c in COUNTRY_CODES if c != profile.last_country]
        if far_countries:
            name, mcc, category = _pick_merchant(card)
            amount = _amount_for(category, card.base_amount)
            return _mk(card, now, name, mcc, category, amount, "ambient",
                       country=random.choice(far_countries), device=random.choice(card.devices))

    card = _seasoned_card()
    profile = state.profile_for(card.card_token)
    name, mcc, category = random.choice(AMBIENT_ANOMALY_MERCHANTS)
    baseline = max(profile.mean_amount, card.base_amount)
    amount = baseline * random.uniform(6, 12) + random.uniform(1500, 5000)
    device = f"dev_{random.randrange(16**8):08x}"  # always unrecognized -> NEW_DEVICE fires too
    return _mk(card, now, name, mcc, category, amount, "ambient", device=device)


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
    amount = baseline * random.uniform(12, 22) + random.uniform(5000, 15000)
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
        amount = random.uniform(150, 1200)
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
    ambient_p = max(0.0, st.sim.ambient_fraud_pct) / 100.0
    for _ in range(n):
        if ambient_p > 0 and random.random() < ambient_p:
            process_transaction(generate_ambient_anomaly(now), st)
        else:
            process_transaction(generate_normal_transaction(now), st)
