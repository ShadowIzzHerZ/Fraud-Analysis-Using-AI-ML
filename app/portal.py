"""Customer-facing "make a test payment" portal.

This is the public-facing counterpart to the analyst console in
`app/ui_dashboard.py`: a customer fills in an amount and a test card, gets a
UPI-style QR back, and submitting it appends one synthetic `Transaction` to
the exact same `AppState` / `simulator.process_transaction` pipeline the
background simulator feeds — so it shows up live on the analyst feed and can
trip the same detectors, exactly like flipping on "Inject Attack" but driven
by a human filling out a form instead of a scripted burst.

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
    payee name is also stamped "RISKPULSE SIMULATION" and the rendered QR
    carries a visible "SIMULATION" stamp.
  - There is no outbound call to any bank, card network, or NPCI/UPI switch
    anywhere in this file. "Processing a payment" here means exactly one
    thing: constructing a `Transaction` and handing it to
    `simulator.process_transaction`, the same function the ambient
    background traffic uses.
"""
from __future__ import annotations

import hashlib
import io
import random
import time
from dataclasses import dataclass
from typing import Optional

import qrcode
import qrcode.image.svg
from nicegui import ui

from app import simulator
from app.geo import COUNTRY_CODES
from app.models import AlertStatus, Channel, Transaction, new_id
from app.state import state
from app.ui_dashboard import C, bd, bg, fmt_money, icon, raw_html, tx

# Despite the field name, `Transaction.country` holds one of these Indian
# city names (see app/geo.py) — the impossible-travel detector looks up
# haversine distance between two of THESE, not ISO country codes, so the
# portal's "suspicious" mode must pick from this pool, not "US"/"IN".
HOME_CITY = "Mumbai"

# Published sandbox card numbers (Stripe/Razorpay/PayPal test-mode docs) —
# Luhn-valid, but none of these have ever been issued to a real cardholder.
# Anything not in this map is rejected outright.
TEST_CARDS: dict[str, str] = {
    "4242424242424242": "Visa (test)",
    "4111111111111111": "Visa (test)",
    "5555555555554444": "Mastercard (test)",
    "5105105105105100": "Mastercard (test)",
    "378282246310005": "American Express (test)",
    "371449635398431": "American Express (test)",
    "6011111111111117": "Discover (test)",
}

# (payee name, mcc) — mcc values reused from app/simulator.py's MERCHANTS so
# scoring context (category baselines) lines up with the rest of the demo.
PAYEES: dict[str, str] = {
    "RiskPulse Demo Kirana Store": "5411",
    "RiskPulse Demo Electronics Bazaar": "5732",
    "RiskPulse Demo Travel Co.": "4511",
    "RiskPulse Demo Subscription": "5968",
}


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


def _qr_svg(data: str) -> str:
    """Render a scannable QR as inline SVG (no Pillow / raster dependency),
    high error-correction so the corner "SIMULATION" stamp overlaid on top
    of it in the UI doesn't break scanning."""
    img = qrcode.make(
        data,
        image_factory=qrcode.image.svg.SvgPathImage,
        box_size=8,
        border=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
    )
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode()
    svg = svg.split("?>", 1)[-1]  # drop the <?xml ...?> prolog
    svg = svg.replace("<path ", f'<path fill="{C["on_surface"]}" ', 1)
    return svg


@dataclass
class PortalReceipt:
    txn_id: str
    vpa: str
    amount: float
    payee: str
    uri: str
    qr_svg: str
    score: float
    outcome: str
    outcome_cls: str


@ui.page("/portal")
def portal_page() -> None:
    refs: dict = {}
    receipt: dict[str, Optional[PortalReceipt]] = {"value": None}

    ui.add_head_html(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800'
        '&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">'
        '<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">'
        '<link rel="stylesheet" href="/static/theme.css">'
        '<style>body,.font-sans{font-family:"Plus Jakarta Sans",ui-sans-serif,sans-serif}'
        '.font-mono,input{font-family:"JetBrains Mono",ui-monospace,monospace}</style>'
    )
    ui.page_title("Test Payment Portal — RiskPulse Simulation")

    def fill_example(pan: str) -> None:
        refs["card"].value = pan
        refs["card"].update()

    def submit(suspicious: bool) -> None:
        raw_pan = "".join(ch for ch in (refs["card"].value or "") if ch.isdigit())
        if raw_pan not in TEST_CARDS or not _luhn_ok(raw_pan):
            ui.notify(
                "Not a recognized test-card number. Pick one of the published sandbox numbers below — "
                "this portal never accepts a real card.",
                type="negative", position="top", timeout=5000,
            )
            return

        try:
            amount = float(refs["amount"].value)
        except (TypeError, ValueError):
            amount = 0.0
        if amount <= 0:
            ui.notify("Enter an amount greater than ₹0.", type="negative", position="top")
            return

        payee_name = refs["payee"].value or next(iter(PAYEES))
        mcc = PAYEES[payee_name]

        card_token = _card_token(raw_pan)
        profile = state.profile_for(card_token)
        now = time.time()

        if suspicious:
            device = f"dev_{random.randrange(16**8):08x}"  # always unrecognized -> NEW_DEVICE fires
            country = "US" if profile.last_country in (None, "IN") else "IN"  # forces a geo flip on repeated use
            baseline = max(profile.mean_amount, amount)
            amount = round(baseline * random.uniform(8, 15) + random.uniform(2000, 6000), 2)
        else:
            device = f"dev_{_card_token(raw_pan)[5:13]}"  # stable per test card, like a remembered device
            country = "IN"

        vpa = _fake_vpa(raw_pan)
        txn = Transaction(
            id=new_id("txn"), ts=now, amount=round(amount, 2), currency="INR",
            merchant=payee_name, mcc=mcc, channel=Channel.UPI, country=country,
            device_fp=device, card_token=card_token, user_id=f"portal_{card_token[-8:]}",
            ip="127.0.0.1", scenario="portal_upi", upi_vpa=vpa,
        )
        simulator.process_transaction(txn)

        alert = next(
            (state.alerts[aid] for aid in state.alert_order if state.alerts[aid].transaction.id == txn.id),
            None,
        )
        score = alert.score.risk_score if alert else 0.0
        if alert and alert.status == AlertStatus.FROZEN:
            outcome, outcome_cls = "Blocked — auto-frozen by fraud policy", "text-rose-700 bg-rose-50 border-rose-200"
        elif alert:
            outcome, outcome_cls = "Flagged for analyst review", "text-amber-700 bg-amber-50 border-amber-200"
        else:
            outcome, outcome_cls = "Processed — no risk signals", "text-emerald-700 bg-emerald-50 border-emerald-200"

        uri = (
            f"upi://pay?pa={vpa}&pn=RISKPULSE%20SIMULATION%20-%20NOT%20REAL"
            f"&am={amount:.2f}&cu=INR&tn=RiskPulse%20test%20payment%20-%20simulation%20only"
        )
        receipt["value"] = PortalReceipt(
            txn_id=txn.id, vpa=vpa, amount=amount, payee=payee_name, uri=uri,
            qr_svg=_qr_svg(uri), score=score, outcome=outcome, outcome_cls=outcome_cls,
        )
        result_panel.refresh()
        ui.notify("Test payment simulated — sent to the analyst console.", position="bottom-right", type="positive")

    @ui.refreshable
    def result_panel() -> None:
        r = receipt["value"]
        if r is None:
            with ui.element("div").classes(f'flex-1 flex flex-col items-center justify-center gap-2 {tx("muted")} p-8 text-center'):
                raw_html(icon("qr_code_2", "text-[40px]"))
                raw_html('<div class="text-[12.5px] font-medium">Fill in the form and submit to generate a test UPI QR.</div>')
            return

        with ui.element("div").classes("flex-1 flex flex-col items-center gap-3 p-5"):
            raw_html(
                '<div class="relative inline-block p-3 bg-white border-2 border-dashed border-rose-400 rounded-xl">'
                f'{r.qr_svg}'
                '<div class="absolute -top-2 -right-3 -rotate-12 bg-rose-600 text-white text-[10px] font-extrabold '
                'tracking-wider px-2.5 py-1 rounded shadow-md">SIMULATION</div>'
                '</div>'
            )
            raw_html(
                f'<div class="text-[11px] {tx("muted")} text-center max-w-[260px] leading-snug">'
                f'Fake payee handle <span class="font-mono font-semibold {tx("on_surface")}">{r.vpa}</span> — '
                '<code>@fakebank</code> is not a real PSP, so this QR cannot resolve or move money on any real UPI app.'
                '</div>'
            )
            with ui.element("div").classes(f'w-full {bg("surface_low")} border {bd("outline_subtle")} rounded-xl p-3 space-y-1.5'):
                raw_html(
                    f'<div class="flex justify-between text-[12px]"><span class="{tx("muted")}">Payee</span>'
                    f'<span class="font-semibold {tx("on_surface")}">{r.payee}</span></div>'
                    f'<div class="flex justify-between text-[12px]"><span class="{tx("muted")}">Amount</span>'
                    f'<span class="font-semibold {tx("on_surface")}">{fmt_money(r.amount)}</span></div>'
                    f'<div class="flex justify-between text-[12px]"><span class="{tx("muted")}">Transaction ID</span>'
                    f'<span class="font-mono {tx("on_surface")}">{r.txn_id[-9:].upper()}</span></div>'
                )
            raw_html(
                f'<div class="w-full flex flex-col gap-0.5 px-3 py-2 rounded-xl border text-[12px] font-semibold {r.outcome_cls}">'
                f'<span>{r.outcome}</span><span class="text-[10px] font-bold uppercase tracking-wider opacity-80">Risk score {r.score:.2f}</span></div>'
            )

    with ui.element("div").classes(f'min-h-screen w-full {bg("background")} {tx("on_surface")} flex justify-center py-10 px-4'):
        with ui.element("div").classes("w-full max-w-4xl space-y-5"):
            raw_html(
                f'<a href="/" class="inline-flex items-center gap-1.5 {tx("muted")} text-[12px] font-semibold hover:{tx("primary")}">'
                f'{icon("arrow_back", "text-[16px]")}<span>Back to analyst console</span></a>'
            )
            raw_html(
                '<div class="flex items-start gap-3 bg-amber-50 border border-amber-200 text-amber-900 rounded-2xl p-4">'
                f'{icon("warning", "text-amber-700 text-[20px] mt-0.5")}'
                '<div class="text-[12.5px] leading-relaxed">'
                '<div class="font-extrabold uppercase tracking-wide text-[11px] mb-1">Simulation environment — no real payments</div>'
                'Only published sandbox test-card numbers are accepted, and the generated QR encodes a payee handle '
                'that does not exist on the real UPI network. This can never debit a real card or move real money — '
                'submitting appends one synthetic event to the RiskPulse demo pipeline, visible live on the '
                '<a href="/" class="underline font-semibold">analyst console</a>.'
                '</div></div>'
            )

            with ui.element("div").classes("flex gap-4 flex-wrap md:flex-nowrap items-start"):
                with ui.element("div").classes(
                    f'flex-1 min-w-[300px] {bg("surface_lowest")} border {bd("outline_variant")} rounded-2xl shadow-sm p-6 space-y-4'
                ):
                    raw_html(f'<div class="text-[16px] font-extrabold {tx("on_surface")}">Make a test UPI payment</div>')

                    refs["payee"] = ui.select(list(PAYEES.keys()), value=next(iter(PAYEES)), label="Pay to") \
                        .props('dense outlined color="#b8431e"').classes("w-full text-[13px]")
                    refs["amount"] = ui.number(label="Amount (₹)", value=499, min=1, step=1, format="%.2f") \
                        .props('dense outlined color="#b8431e"').classes("w-full text-[13px]")
                    refs["card"] = ui.input(label="Test card number", placeholder="4242 4242 4242 4242") \
                        .props('dense outlined color="#b8431e"').classes("w-full text-[13px] font-mono")

                    with ui.element("div").classes("flex gap-2"):
                        refs["expiry"] = ui.input(label="Expiry (MM/YY)", value="12/29") \
                            .props('dense outlined color="#b8431e"').classes("flex-1 text-[13px] font-mono")
                        refs["cvv"] = ui.input(label="CVV", value="123", password=True) \
                            .props('dense outlined color="#b8431e"').classes("w-20 text-[13px] font-mono")

                    raw_html(f'<div class="text-[10px] font-bold {tx("muted")} uppercase tracking-wider pt-1">Published test cards</div>')
                    with ui.element("div").classes("flex flex-wrap gap-1.5"):
                        for pan, label in TEST_CARDS.items():
                            pretty = " ".join(pan[i:i + 4] for i in range(0, len(pan), 4))
                            raw_html(
                                f'<button title="{label}" class="px-2 py-1 rounded-lg border {bd("outline_variant")} {bg("surface_low")} '
                                f'hover:{bg("surface_container")} text-[10.5px] font-mono {tx("on_surface")}">{pretty}</button>'
                            ).on("click", lambda e, p=pan: fill_example(p))

                    ui.separator().classes("my-1")

                    with ui.element("div").classes("flex items-center gap-2 pt-1"):
                        raw_html(
                            f'<button class="flex-1 flex items-center justify-center gap-1.5 px-3.5 py-2 {bg("primary")} '
                            f'hover:bg-[{C["primary_hover"]}] text-white rounded-full font-semibold text-[13px] shadow-sm '
                            f'transition-all active:scale-[0.98]">{icon("qr_code_2", "text-[16px]")}<span>Pay via UPI (simulated)</span></button>'
                        ).on("click", lambda e: submit(False))
                    raw_html(
                        f'<button title="Skews the amount/device so the demo detectors are more likely to fire" '
                        f'class="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 border {bd("outline_variant")} '
                        f'{tx("muted_dark")} hover:{bg("surface_low")} rounded-full font-semibold text-[11px] transition-all">'
                        f'{icon("bolt", "text-[14px]")}<span>Simulate as suspicious pattern</span></button>'
                    ).on("click", lambda e: submit(True))

                with ui.element("div").classes(
                    f'flex-1 min-w-[300px] flex flex-col {bg("surface_lowest")} border {bd("outline_variant")} rounded-2xl shadow-sm min-h-[420px]'
                ):
                    result_panel()
