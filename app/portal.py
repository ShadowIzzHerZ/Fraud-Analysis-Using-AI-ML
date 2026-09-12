"""Test-payment API for the standalone "ZenPay" Android app
(android/ZenPay/) — the actual UI (test-card entry, QR display, past-
transaction history) lives natively on the phone now, not in this web app.
The analyst console (app/ui_dashboard.py) is analyst-only and carries no
payment/QR UI; this module's only surface is JSON the native app calls over
HTTP — normally over Wi-Fi to this machine's LAN IP (phone and this machine
on the same network, no cable needed; see android/ZenPay/README.md),
with a USB + `adb reverse tcp:8080 tcp:8080` tunnel to 127.0.0.1 as a fallback
when Wi-Fi isn't available.

SIMULATION ONLY — this cannot move real money, by construction, not just by
policy:
  - Card numbers are checked against `TEST_CARDS`, a short allowlist of the
    same publicly published sandbox PANs Stripe/Razorpay/PayPal docs use
    (Luhn-valid, never issued to a real cardholder). Anything else is
    rejected before it ever reaches the pipeline.
  - The "UPI QR" encodes a standard `upi://pay?...` deep link so it *looks*
    and scans like a real one, but the payee handle is `sim.<hash>@fakebank`
    — `@fakebank` is not an NPCI-registered PSP suffix, so any real UPI app
    that scans it will fail payee resolution and refuse to proceed. The
    payee name is also stamped "ZENPAY SIMULATION" and the app renders a
    visible "SIMULATION" stamp over the QR.
  - There is no outbound call to any bank, card network, or NPCI/UPI switch
    anywhere in this file. "Processing a payment" here means exactly one
    thing: constructing a `Transaction` and handing it to
    `simulator.process_transaction`, the same function the ambient
    background traffic uses.
  - The QR itself is never rendered as an image server-side — this endpoint
    returns the raw module matrix (a grid of booleans) and the phone draws
    it, so there's no image-generation dependency on this end at all.
"""
from __future__ import annotations

import hashlib
import random
import time

import qrcode
from nicegui import app
from pydantic import BaseModel

from app import simulator
from app.geo import COUNTRY_CODES
from app.models import AlertStatus, Channel, Transaction, new_id
from app.state import state

# Published sandbox card numbers (Stripe/Razorpay/PayPal test-mode docs) —
# Luhn-valid, but none of these have ever been issued to a real cardholder.
# Anything not in this map is rejected outright. Mirrored in the Android app
# (TestCards.kt) for the "fill example" chips — this copy is the one that's
# actually enforced.
TEST_CARDS: dict[str, str] = {
    "4242424242424242": "Visa (test)",
    "4111111111111111": "Visa (test)",
    "5555555555554444": "Mastercard (test)",
    "5105105105105100": "Mastercard (test)",
    "378282246310005": "American Express (test)",
    "371449635398431": "American Express (test)",
    "6011111111111117": "Discover (test)",
}

# (payee name -> mcc) — mcc values reused from app/simulator.py's MERCHANTS
# so scoring context (category baselines) lines up with the rest of the demo.
# A spread of everyday purchase categories, not just one or two, so the demo
# feed (and the UNUSUAL_MCC detector) has real variety to work with — mirror
# any addition/removal in the Android app's TestCards.kt PAYEES list.
PAYEES: dict[str, str] = {
    "ZenPay Demo Kirana Store": "5411",
    "ZenPay Demo Electronics Bazaar": "5732",
    "ZenPay Demo Travel Co.": "4511",
    "ZenPay Demo Subscription": "5968",
    "ZenPay Demo Chai Tapri Café": "5812",
    "ZenPay Demo Petrol Pump": "5541",
    "ZenPay Demo Fashion Hub": "5651",
    "ZenPay Demo Pharmacy": "5912",
    "ZenPay Demo Home & Decor": "5200",
    "ZenPay Demo Cinema": "7832",
    "ZenPay Demo RideNow Cabs": "4121",
    "ZenPay Demo Jewellers": "5944",
    "ZenPay Demo Online Mart": "5969",
    "ZenPay Demo Hotel Stay": "7011",
}

# Despite the field name, `Transaction.country` holds one of these Indian
# city names (see app/geo.py) — the impossible-travel detector looks up
# haversine distance between two of THESE, not ISO country codes.
HOME_CITY = "Mumbai"

# -- user-to-user wallet transfers (ScanActivity -> SendMoneyActivity) ------
#
# Each ZenPay install generates its own random 15-digit "ZenPay ID" on
# first launch (see UserIdentity.kt) — a wallet key that looks like an
# account number but is purely local to this demo, never a real bank
# account or UPI handle. Scanning another device's ID QR and sending fake
# money debits/credits these in-memory balances so the transfer is real
# *within the simulation* on both ends, same "not a database" scope as the
# rest of AppState (app/state.py) — this resets whenever the backend
# restarts, which is fine for a hackathon demo.
WALLETS: dict[str, float] = {}
DEFAULT_WALLET_BALANCE = 100_000.0

# Per-recipient log of completed incoming transfers, newest last. The app
# only ever asks for its OWN balance number (GET /wallet/{id}) — that tells
# a device a credit landed, but not from whom, for how much, or that it
# should say so in "Past transactions" (HistoryStore.kt is purely local and
# only ever gets an entry appended by the SENDING device). This is what the
# receiving device polls instead, alongside its balance, to backfill that.
INCOMING: dict[str, list[dict]] = {}


def _valid_wallet_id(user_id: str) -> bool:
    return len(user_id) == 15 and user_id.isdigit()


def _wallet_balance(user_id: str) -> float:
    return WALLETS.setdefault(user_id, DEFAULT_WALLET_BALANCE)


def _luhn_ok(digits: str) -> bool:
    if not digits.isdigit() or len(digits) < 12:
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _fake_vpa(pan_digits: str) -> str:
    """A payee handle that LOOKS like a UPI ID but can't resolve on any real
    UPI app — `@fakebank` isn't an NPCI-registered PSP suffix (real ones look
    like @okaxis, @ybl, @oksbi, ...)."""
    h = hashlib.sha256(pan_digits.encode()).hexdigest()[:10]
    return f"sim.{h}@fakebank"


def _card_token(pan_digits: str) -> str:
    return "test_" + hashlib.sha1(pan_digits.encode()).hexdigest()[:12]


def _qr_matrix(data: str) -> list[list[bool]]:
    """Raw QR module grid (quiet-zone border included), high error-correction
    so the phone-side "SIMULATION" stamp drawn over the QR doesn't break
    scanning. No image library needed on this end — the app draws the grid."""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=1, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.get_matrix()


class PayRequest(BaseModel):
    card: str
    amount: float
    payee: str
    suspicious: bool = False


class PayResponse(BaseModel):
    ok: bool
    error: str = ""
    txn_id: str = ""
    vpa: str = ""
    uri: str = ""
    amount: float = 0.0
    payee: str = ""
    score: float = 0.0
    severity: str = ""
    outcome: str = ""
    qr_modules: list[list[bool]] = []


@app.get("/api/portal/ping")
def portal_ping() -> dict:
    """Health check for the app's Settings screen ("Test Connection") — just
    confirms this backend is reachable at all before a user bothers filling
    in a card and amount."""
    return {"ok": True, "service": "zenpay-portal", "payees": list(PAYEES.keys())}


@app.post("/api/portal/pay")
def portal_pay(req: PayRequest) -> PayResponse:
    raw_pan = "".join(ch for ch in req.card if ch.isdigit())
    if raw_pan not in TEST_CARDS or not _luhn_ok(raw_pan):
        return PayResponse(ok=False, error="Not a recognized test-card number.")

    if req.amount <= 0:
        return PayResponse(ok=False, error="Amount must be greater than 0.")

    payee_name = req.payee if req.payee in PAYEES else next(iter(PAYEES))
    mcc = PAYEES[payee_name]

    card_token = _card_token(raw_pan)
    profile = state.profile_for(card_token)
    now = time.time()
    amount = req.amount

    if req.suspicious:
        device = f"dev_{random.randrange(16**8):08x}"  # always unrecognized -> NEW_DEVICE fires (once n>=3)
        far_cities = [c for c in COUNTRY_CODES if c != profile.last_country] or COUNTRY_CODES
        country = random.choice(far_cities)  # forces a geo flip -> GEO_JUMP, needs only one prior txn
        baseline = max(profile.mean_amount, amount)
        amount = round(baseline * random.uniform(8, 15) + random.uniform(2000, 6000), 2)
    else:
        device = f"dev_{_card_token(raw_pan)[5:13]}"  # stable per test card, like a remembered device
        country = HOME_CITY

    vpa = _fake_vpa(raw_pan)
    txn = Transaction(
        id=new_id("txn"), ts=now, amount=round(amount, 2), currency="INR",
        merchant=payee_name, mcc=mcc, channel=Channel.UPI, country=country,
        device_fp=device, card_token=card_token, user_id=f"portal_{card_token[-8:]}",
        ip="127.0.0.1", scenario="portal_upi", upi_vpa=vpa,
    )
    simulator.process_transaction(txn)
    score, severity, outcome = _score_and_outcome(txn.id)

    uri = (
        f"upi://pay?pa={vpa}&pn=ZENPAY%20SIMULATION%20-%20NOT%20REAL"
        f"&am={amount:.2f}&cu=INR&tn=ZenPay%20test%20payment%20-%20simulation%20only"
    )
    return PayResponse(
        ok=True, txn_id=txn.id, vpa=vpa, uri=uri, amount=amount, payee=payee_name,
        score=score, severity=severity, outcome=outcome, qr_modules=_qr_matrix(uri),
    )


def _score_and_outcome(txn_id: str) -> tuple[float, str, str]:
    """Look up the alert (if any) `simulator.process_transaction` produced
    for `txn_id` and translate it into the score/severity/outcome triple
    both /pay and /transfer return."""
    alert = next(
        (state.alerts[aid] for aid in state.alert_order if state.alerts[aid].transaction.id == txn_id),
        None,
    )
    score = alert.score.risk_score if alert else 0.0
    severity = alert.score.severity.value if alert else "low"
    if alert and alert.status == AlertStatus.FROZEN:
        outcome = "Blocked — auto-frozen by fraud policy"
    elif alert:
        outcome = "Flagged for analyst review"
    else:
        outcome = "Processed — no risk signals"
    return score, severity, outcome


class TransferRequest(BaseModel):
    from_id: str
    to_id: str
    amount: float


class TransferResponse(BaseModel):
    ok: bool
    error: str = ""
    txn_id: str = ""
    from_balance: float = 0.0
    to_balance: float = 0.0
    score: float = 0.0
    severity: str = ""
    outcome: str = ""


class WalletResponse(BaseModel):
    id: str
    balance: float


@app.get("/api/portal/wallet/{user_id}")
def portal_wallet(user_id: str) -> WalletResponse:
    """Authoritative shared balance for a ZenPay ID — polled by the app on
    resume (when sync is on) so an incoming transfer from another device
    actually shows up, not just outgoing ones this device itself sent."""
    return WalletResponse(id=user_id, balance=_wallet_balance(user_id))


@app.post("/api/portal/transfer")
def portal_transfer(req: TransferRequest) -> TransferResponse:
    from_id, to_id = req.from_id.strip(), req.to_id.strip()
    if not _valid_wallet_id(from_id) or not _valid_wallet_id(to_id):
        return TransferResponse(ok=False, error="Both sender and recipient must be 15-digit ZenPay IDs.")
    if from_id == to_id:
        return TransferResponse(ok=False, error="Can't send money to yourself.")
    if req.amount <= 0:
        return TransferResponse(ok=False, error="Amount must be greater than 0.")

    from_balance = _wallet_balance(from_id)
    if req.amount > from_balance:
        return TransferResponse(ok=False, error="Insufficient balance.", from_balance=from_balance, to_balance=_wallet_balance(to_id))

    WALLETS[from_id] = from_balance - req.amount
    WALLETS[to_id] = _wallet_balance(to_id) + req.amount

    # Same pipeline as a merchant payment — a P2P wallet is just another
    # channel, with its own persistent per-sender profile so repeated
    # transfers from the same ZenPay ID build velocity/amount history like
    # everything else in this demo.
    txn = Transaction(
        id=new_id("txn"), ts=time.time(), amount=round(req.amount, 2), currency="INR",
        merchant=f"ZenPay user •••{to_id[-4:]}", mcc="6540", channel=Channel.P2P,
        country=HOME_CITY, device_fp=f"dev_{from_id[:8]}", card_token=f"wallet_{from_id}",
        user_id=f"wallet_{from_id}", ip="127.0.0.1", scenario="p2p_transfer",
    )
    simulator.process_transaction(txn)
    score, severity, outcome = _score_and_outcome(txn.id)

    INCOMING.setdefault(to_id, []).append({
        "txn_id": txn.id, "from_id": from_id, "amount": round(req.amount, 2),
        "ts": txn.ts, "score": score, "severity": severity, "outcome": outcome,
    })

    return TransferResponse(
        ok=True, txn_id=txn.id, from_balance=WALLETS[from_id], to_balance=WALLETS[to_id],
        score=score, severity=severity, outcome=outcome,
    )


class IncomingTransfer(BaseModel):
    txn_id: str
    from_id: str
    amount: float
    ts: float
    score: float
    severity: str
    outcome: str


class IncomingTransfersResponse(BaseModel):
    transfers: list[IncomingTransfer] = []


@app.get("/api/portal/wallet/{user_id}/incoming")
def portal_incoming(user_id: str, since_ts: float = 0.0) -> IncomingTransfersResponse:
    """Polled by the app (alongside the balance) so a RECEIVED transfer gets
    its own "Received from •••XXXX" entry in that device's Past Transactions,
    not just a balance number that changed for no visible reason. `since_ts`
    lets the app ask for only what it hasn't already recorded locally."""
    records = INCOMING.get(user_id, [])
    return IncomingTransfersResponse(
        transfers=[IncomingTransfer(**r) for r in records if r["ts"] > since_ts][-50:],
    )
