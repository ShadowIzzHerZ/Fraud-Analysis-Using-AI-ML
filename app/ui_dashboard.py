"""The NiceGUI dashboard — "Warm Civic Minimal" visual system (ported from a
Google Stitch mockup, docs/stitch/code.html) wired to the real backend in
app/state.py, app/scoring.py and app/simulator.py.

The mockup used Tailwind's Play CDN with a custom color config; NiceGUI
already bundles that same Play CDN runtime, so all markup here uses Tailwind
utility classes directly. To avoid any risk of a runtime `tailwind.config`
script losing a race against NiceGUI's own framework scripts, custom theme
colors are written as Tailwind arbitrary values (`bg-[#f7f5f0]`, ...) via the
`C` palette dict below rather than named theme colors — arbitrary values need
no config at all. Standard Tailwind palette classes (rose-*, amber-*,
emerald-*, white) are used as-is.

As before, rendering is split into small `@ui.refreshable` regions so a
timer can redraw data-driven parts without touching in-progress input.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Optional

from nicegui import app, ui

from app import simulator
from app.models import Alert, AlertStatus, Reason, ScoreResult, Severity, Transaction, new_id
from app.state import state

app.add_static_files("/static", str(Path(__file__).parent / "static"))

# -- palette ("Warm Civic Minimal", from docs/stitch/DESIGN.md) --------------
C = {
    "primary": "#b8431e",
    "primary_hover": "#9e391b",
    "primary_container": "#ffe5de",
    "on_primary_container": "#3a0a00",
    "background": "#f7f5f0",
    "surface": "#fbf9f5",
    "surface_lowest": "#ffffff",
    "surface_low": "#f4f1ea",
    "surface_container": "#ede9e0",
    "surface_high": "#e5e1d6",
    "surface_highest": "#ded9cd",
    "outline": "#8c716a",
    "outline_variant": "#e5e1d8",
    "outline_subtle": "#ece8de",
    "on_surface": "#1b1c1a",
    "on_surface_variant": "#58423b",
    "muted": "#76726c",
    "muted_dark": "#4a4742",
}


def bg(key: str, opacity: str = "") -> str:
    return f"bg-[{C[key]}]" + (f"/{opacity}" if opacity else "")


def tx(key: str) -> str:
    return f"text-[{C[key]}]"


def bd(key: str) -> str:
    return f"border-[{C[key]}]"


SEV_DOT = {"critical": "bg-rose-600", "high": "bg-amber-600", "medium": bg("surface_high"), "low": bg("surface_high")}
SEV_BADGE = {
    "critical": "bg-rose-600 text-white",
    "high": "bg-amber-600 text-white",
    "medium": f"{bg('surface_high')} {tx('on_surface')}",
    "low": f"{bg('surface_high')} {tx('on_surface')}",
}
SEV_CARD_BORDER = {
    "critical": "border-rose-200 hover:border-rose-300",
    "high": "border-amber-200 hover:border-amber-300",
    "medium": f"{bd('outline_variant')} hover:border-outline",
    "low": f"{bd('outline_variant')} hover:border-outline",
}
STATUS_BADGE = {
    "frozen": "bg-rose-100 text-rose-800 font-bold",
    "investigating": f"{bg('primary_container')} {tx('primary')} font-bold",
    "dismissed": f"{bg('surface_container')} {tx('muted')} line-through",
    "new": f"{bg('surface_container')} {tx('muted_dark')}",
}
STATUS_LABEL = {"new": "NEW", "investigating": "IN REVIEW", "frozen": "FROZEN", "dismissed": "DISMISSED"}
SCENARIO_EMOJI = {"velocity": "⚡", "amount_outlier": "💎", "impossible_travel": "✈️", "mule_burst": "🕸️"}


def score_badge_class(score: float) -> str:
    if score >= 0.90:
        return "text-rose-700 bg-rose-50 border-rose-200 font-bold"
    if score >= 0.75:
        return "text-amber-800 bg-amber-50 border-amber-200 font-bold"
    if score >= 0.50:
        return "text-amber-700 bg-amber-50/50 border-amber-200"
    return "text-emerald-700 bg-emerald-50 border-emerald-200"


def raw_html(content: str = ""):
    """ui.html wrapper: content here is markup we build ourselves (free text
    already passed through `escape()`), so unsanitized rendering is safe —
    sanitizing would strip every Tailwind class attribute."""
    return ui.html(content, sanitize=False)


def icon(name: str, extra: str = "") -> str:
    return f'<span class="material-symbols-outlined {extra}">{name}</span>'


# -- formatting ---------------------------------------------------------

def fmt_money(amount: float, currency: str) -> str:
    return f"{currency} {amount:,.2f}"


def fmt_money0(amount: float, currency: str = "$") -> str:
    return f"{currency}{amount:,.0f}"


def fmt_time(ts: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts)) + f".{int((ts % 1) * 1000):03d}"


def time_ago(ts: float) -> str:
    d = max(0, time.time() - ts)
    if d < 5:
        return "just now"
    if d < 60:
        return f"{int(d)}s ago"
    return f"{int(d // 60)}m ago"


def sparkline_path(values: list[float], width: float = 100, height: float = 20) -> str:
    if len(values) < 2:
        return f"M0,{height} L{width},{height}"
    lo, hi = min(values), max(values)
    span = max(hi - lo, 1e-6)
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        x = i / (n - 1) * width
        y = height - ((v - lo) / span) * height * 0.85 - height * 0.1
        pts.append(f"{x:.1f},{y:.1f}")
    return "M" + " L".join(pts)


# -- data lookups ---------------------------------------------------------

def find_feed_item(txn_id: str) -> Optional[tuple[Transaction, ScoreResult]]:
    for t, r in state.feed:
        if t.id == txn_id:
            return t, r
    return None


def find_alert_by_txn(txn_id: str) -> Optional[Alert]:
    for aid in state.alert_order:
        a = state.alerts.get(aid)
        if a and a.transaction.id == txn_id:
            return a
    return None


def ensure_alert_for(txn_id: str) -> Optional[Alert]:
    """Resolve a transaction id to a real Alert, promoting a plain feed
    transaction (one that never crossed the auto-alert threshold) into a
    manually-opened case the first time an analyst acts on it."""
    existing = find_alert_by_txn(txn_id)
    if existing:
        return existing
    found = find_feed_item(txn_id)
    if not found:
        return None
    txn, result = found
    alert = Alert(id=new_id("alrt"), transaction=txn, score=result)
    alert.log("Manually opened from live feed by investigator")
    state.add_alert(alert)
    return alert


# -- row / card markup ---------------------------------------------------------

# Grid columns shared by the feed header and every feed row — a real <table>
# can't carry a per-row Python click handler (each row needs its own NiceGUI
# element instance for that), so the "table" is really a CSS grid list.
FEED_GRID = "grid-template-columns:104px 92px 1fr 96px 60px 84px 150px 96px"


def feed_row_html(txn: Transaction, result: ScoreResult, flash: bool = False) -> str:
    score_cls = score_badge_class(result.risk_score)
    bar_color = "bg-[#b8431e]" if result.risk_score >= 0.75 else "bg-emerald-600"
    channel_badge = (
        f'<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold {bg("surface_container")} {tx("muted_dark")} border {bd("outline_subtle")}">ONLINE</span>'
        if txn.channel.value == "online" else
        f'<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold {bg("surface_low")} {tx("muted")} border {bd("outline_subtle")}">POS</span>'
    )
    amount_cls = tx("primary") if txn.amount > 3000 else tx("on_surface")
    flash_cls = " flash-new-tx" if flash else ""
    return (
        f'<div class="grid items-center border-b {bd("outline_subtle")} hover:{bg("surface_low")} transition-colors cursor-pointer{flash_cls}" '
        f'style="{FEED_GRID}">'
        f'<div class="px-4 py-2 {tx("muted")} text-[11px]">{fmt_time(txn.ts)}</div>'
        f'<div class="px-2 py-2 font-bold {tx("on_surface")} text-[12px]">{escape(txn.id[-9:].upper())}</div>'
        f'<div class="px-2 py-2 min-w-0">'
        f'<div class="truncate {tx("on_surface")} font-semibold text-[12px] font-sans">{escape(txn.merchant)}</div>'
        f'<div class="text-[10px] {tx("muted")} truncate font-sans">{escape(txn.mcc)}</div>'
        f'</div>'
        f'<div class="px-2 py-2 {tx("muted_dark")} text-[11px]">•••• {escape(txn.card_token[-4:])}</div>'
        f'<div class="px-2 py-2 text-center text-[12px]"><span class="text-[10px] {tx("muted")}">{escape(txn.country)}</span></div>'
        f'<div class="px-2 py-2 text-center">{channel_badge}</div>'
        f'<div class="px-2 py-2">'
        f'<div class="flex items-center gap-1.5">'
        f'<span class="px-2 py-0.5 rounded-full text-[11px] border {score_cls}">{result.risk_score:.2f}</span>'
        f'<div class="flex-1 {bg("surface_high")} h-1.5 rounded-full overflow-hidden block">'
        f'<div class="h-full rounded-full {bar_color}" style="width:{max(3, round(result.risk_score * 100))}%"></div>'
        f'</div></div></div>'
        f'<div class="px-4 py-2 text-right font-bold {amount_cls}">{fmt_money(txn.amount, txn.currency)}</div>'
        f'</div>'
    )


def detector_tag_html(reason: Reason, weight: float) -> str:
    return (
        f'<div class="flex items-center gap-1.5 text-[10px] {tx("muted_dark")} {bg("surface_low")} px-2 py-1 rounded-lg border {bd("outline_subtle")}">'
        f'<span class="text-rose-700 font-bold">+{weight:.2f}</span>'
        f'<span class="truncate">{escape(reason.text)}</span>'
        f'</div>'
    )


def alert_card_html(alert: Alert) -> str:
    t = alert.transaction
    sev = alert.score.severity.value
    tags = "".join(
        detector_tag_html(r, alert.score.contributions.get(r.detector, 0.0))
        for r in alert.score.reasons[:2]
    ) or f'<div class="text-[10px] {tx("muted")} px-2 py-1">No detector reasons on file.</div>'
    score_cls = "text-rose-700" if alert.score.risk_score >= 0.85 else "text-amber-700"
    amount_cls = tx("primary") if t.amount > 3000 else tx("on_surface")
    return (
        f'<div class="{bg("surface_lowest")} border {SEV_CARD_BORDER[sev]} p-3 rounded-2xl cursor-pointer hover:shadow-md transition-all active:scale-[0.99] space-y-2" data-txid="{escape(t.id)}">'
        f'<div class="flex items-center justify-between">'
        f'<div class="flex items-center gap-1.5">'
        f'<span class="px-2 py-0.5 rounded-full text-[9px] font-bold {SEV_BADGE[sev]}">{sev.upper()}</span>'
        f'<span class="px-2 py-0.5 rounded-full text-[9px] font-semibold {STATUS_BADGE[alert.status.value]}">{STATUS_LABEL[alert.status.value]}</span>'
        f'<span class="text-[10px] {tx("muted")}">{time_ago(alert.created_at)}</span>'
        f'</div>'
        f'<div class="flex items-center gap-1">'
        f'<span class="text-[9px] {tx("muted")} uppercase">Score:</span>'
        f'<span class="text-[12px] font-extrabold {score_cls}">{alert.score.risk_score:.2f}</span>'
        f'</div></div>'
        f'<div class="flex items-center justify-between pt-0.5">'
        f'<div><span class="text-[13px] font-bold {tx("on_surface")} leading-snug">{escape(t.merchant)}</span>'
        f'<div class="text-[10px] {tx("muted")} mt-0.5">•••• {escape(t.card_token[-4:])} · {escape(t.country)} · {escape(t.channel.value.upper())}</div></div>'
        f'<div class="text-right"><span class="text-[14px] font-extrabold {amount_cls}">{fmt_money(t.amount, t.currency)}</span></div>'
        f'</div>'
        f'<div class="space-y-1 pt-0.5">{tags}</div>'
        f'</div>'
    )


def pill(label: str, active: bool) -> str:
    cls = "px-2.5 py-0.5 font-semibold rounded-full text-[11px] transition-colors " + (
        f'{bg("primary")} text-white' if active
        else f'{bg("surface_low")} {tx("muted_dark")} hover:{bg("surface_container")}'
    )
    return f'<button class="{cls}">{escape(label)}</button>'


# -- per-client UI state -------------------------------------------------------------

@dataclass
class UIFilters:
    search: str = ""
    severity: str = "ALL"
    status: str = "ALL"
    channel: str = "ALL"
    drawer_txn_id: Optional[str] = None
    feed_cleared_at: float = 0.0
    hiccup: bool = False
    prev_events_per_min: float = 0.0
    max_at_risk_seen: float = 1.0
    throughput_history: list = field(default_factory=list)
    last_seen_version: int = -1


@ui.page("/")
def dashboard_page() -> None:
    filters = UIFilters()
    refs: dict = {"note": None}

    ui.add_head_html(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800'
        '&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">'
        '<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">'
        '<link rel="stylesheet" href="/static/theme.css">'
        '<style>body,.font-sans{font-family:"Plus Jakarta Sans",ui-sans-serif,sans-serif}'
        '.font-mono,table,input,textarea{font-family:"JetBrains Mono",ui-monospace,monospace}</style>'
    )
    ui.page_title("RiskPulse — Fraud Operations Console")

    # -- handlers --------------------------------------------------------------
    def on_search_change(e) -> None:
        filters.search = (e.value or "").strip()
        feed_body.refresh()
        alerts_body.refresh()

    def set_severity(sev: str) -> None:
        filters.severity = sev
        alerts_body.refresh()
        severity_pills.refresh()

    def set_status(st: str) -> None:
        filters.status = st
        alerts_body.refresh()
        status_pills.refresh()

    def on_channel_change(e) -> None:
        filters.channel = e.value
        feed_body.refresh()

    def clear_feed_display() -> None:
        filters.feed_cleared_at = time.time()
        feed_body.refresh()
        ui.notify("Live table buffer display cleared.", position="bottom-right", timeout=3500)

    def open_drawer(txn_id: str) -> None:
        filters.drawer_txn_id = txn_id
        drawer.style("width:420px")
        drawer_body.refresh()
        drawer_status_badge.refresh()
        alerts_body.refresh()

    def close_drawer() -> None:
        drawer.style("width:0px")
        filters.drawer_txn_id = None
        drawer_status_badge.refresh()
        alerts_body.refresh()

    def do_action(status: AlertStatus) -> None:
        if not filters.drawer_txn_id:
            return
        alert = ensure_alert_for(filters.drawer_txn_id)
        if not alert:
            return
        note_val = refs["note"].value if refs["note"] else ""
        updated = state.set_alert_status(alert.id, status, note=note_val)
        if updated:
            msgs = {
                AlertStatus.FROZEN: (f"🛑 Card •••• {updated.transaction.card_token[-4:]} frozen. Merchant notified.", "negative"),
                AlertStatus.INVESTIGATING: (f"🔍 Case {updated.transaction.id[-9:].upper()} escalated for review.", "ongoing"),
                AlertStatus.DISMISSED: (f"✅ Alert {updated.transaction.id[-9:].upper()} dismissed.", "positive"),
            }
            msg, kind = msgs.get(status, ("Updated.", "info"))
            ui.notify(msg, position="bottom-right", timeout=3500, type=kind)
        alerts_body.refresh()
        drawer_body.refresh()
        drawer_status_badge.refresh()
        kpi_strip.refresh()
        header_counters.refresh()

    def save_note() -> None:
        if not filters.drawer_txn_id:
            return
        alert = ensure_alert_for(filters.drawer_txn_id)
        if not alert:
            return
        alert.note = refs["note"].value if refs["note"] else ""
        alert.log("Case notes updated by investigator")
        state.version += 1
        drawer_body.refresh()
        ui.notify("📝 Investigator case notes saved.", position="bottom-right", timeout=3500)

    def export_csv() -> None:
        csv_text = state.alerts_csv(limit=500)
        ui.download(csv_text.encode("utf-8"), filename="riskpulse_alerts.csv", media_type="text/csv")
        ui.notify(f"📥 Exported {len(state.alerts)} flagged alerts to CSV.", position="bottom-right", timeout=3500, type="positive")

    def toggle_running() -> None:
        state.sim.running = not state.sim.running
        run_controls.refresh()
        live_indicator.refresh()
        ui.notify(
            "▶️ Live transaction ingestion active." if state.sim.running else "⏸️ Ingestion stream paused.",
            position="bottom-right", timeout=3000,
        )

    def on_speed_change(e) -> None:
        state.sim.base_rate = float(e.value)
        rate_label.refresh()

    def on_policy_toggle(e) -> None:
        state.policy.auto_freeze_enabled = bool(e.value)
        ui.notify(f"Policy: Auto-Freeze is {'ACTIVE' if e.value else 'DISABLED'}.", position="bottom-right", timeout=3000)

    def on_threshold_change(e) -> None:
        try:
            state.policy.auto_freeze_threshold = max(0.0, min(1.0, float(e.value)))
            ui.notify(f"Policy threshold set to {state.policy.auto_freeze_threshold:.2f}.", position="bottom-right", timeout=3000)
        except (TypeError, ValueError):
            pass

    def inject(scenario_key: str) -> None:
        label, _fn = simulator.SCENARIOS[scenario_key]
        n = simulator.inject_scenario(scenario_key)
        emoji = SCENARIO_EMOJI.get(scenario_key, "⚠️")
        ui.notify(f"{emoji} {label}: {n} events queued", position="bottom-right", timeout=3500, type="warning")

    def toggle_hiccup() -> None:
        filters.hiccup = not filters.hiccup
        live_indicator.refresh()
        hiccup_banner.refresh()
        if filters.hiccup:
            ui.notify("⚠️ Network hiccup: latency spiked to 342ms.", position="bottom-right", timeout=3500, type="warning")
        else:
            ui.notify("🟢 Stream latency normalized (18ms).", position="bottom-right", timeout=3500, type="positive")

    def emergency_freeze() -> None:
        frozen = state.emergency_freeze(min_score=0.80)
        alerts_body.refresh()
        kpi_strip.refresh()
        header_counters.refresh()
        ui.notify(f"🚨 Emergency Freeze: blocked {len(frozen)} high-risk cards immediately!", position="bottom-right", timeout=4000, type="negative")

    def clear_error_banner() -> None:
        state.stream_error = None
        error_banner.refresh()

    # -- refreshables --------------------------------------------------------------
    @ui.refreshable
    def error_banner() -> None:
        if state.stream_error:
            with ui.element("div").classes(f'w-full bg-amber-50 border-b border-amber-200 px-6 py-2 flex items-center justify-between'):
                raw_html(
                    f'<div class="flex items-center gap-2.5">{icon("warning", "text-amber-700 text-[18px]")}'
                    f'<span class="font-bold text-amber-900 text-[12px]">BACKEND ERROR:</span>'
                    f'<span class="text-[12px] text-amber-800">{escape(state.stream_error)} — showing last known state.</span></div>'
                )
                ui.button("Dismiss", on_click=clear_error_banner).props("flat dense").classes("text-[12px] font-semibold text-[#b8431e]")

    @ui.refreshable
    def hiccup_banner() -> None:
        if filters.hiccup:
            with ui.element("div").classes("w-full bg-amber-50 border-b border-amber-200 px-6 py-2 flex items-center justify-between"):
                raw_html(
                    f'<div class="flex items-center gap-2.5">{icon("warning", "text-amber-700 text-[18px]")}'
                    '<span class="font-bold text-amber-900 text-[12px]">STREAM DEGRADED:</span>'
                    '<span class="text-[12px] text-amber-800">WebSocket heartbeat delayed (~342ms). Displaying cached telemetry without packet drop.</span></div>'
                    '<span class="font-mono text-[10px] bg-amber-100 text-amber-900 px-2 py-0.5 rounded-full font-bold">FALLBACK BUFFER</span>'
                )
                ui.button("Dismiss", on_click=toggle_hiccup).props("flat dense").classes("text-[12px] font-semibold text-[#b8431e]")

    @ui.refreshable
    def live_indicator() -> None:
        if filters.hiccup:
            raw_html(
                f'<div class="flex items-center gap-2 {bg("surface_low")} px-3 py-1 rounded-full border {bd("outline_variant")} text-[12px]">'
                '<span class="relative flex h-2 w-2"><span class="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span></span>'
                '<span class="font-bold text-amber-800 uppercase tracking-wide text-[10px]">STREAM DEGRADED</span>'
                f'<span class="{tx("muted")} text-[10px]">·</span>'
                '<span class="text-[11px] text-amber-900 font-bold">342ms</span></div>'
            )
        elif state.sim.running:
            raw_html(
                f'<div class="flex items-center gap-2 {bg("surface_low")} px-3 py-1 rounded-full border {bd("outline_variant")} text-[12px]">'
                '<span class="relative flex h-2 w-2"><span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75"></span>'
                '<span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span></span>'
                '<span class="font-bold text-emerald-700 uppercase tracking-wide text-[10px]">Stream Active</span>'
                f'<span class="{tx("muted")} text-[10px]">·</span>'
                f'<span class="text-[11px] {tx("muted_dark")} font-medium">18ms</span></div>'
            )
        else:
            raw_html(
                f'<div class="flex items-center gap-2 {bg("surface_low")} px-3 py-1 rounded-full border {bd("outline_variant")} text-[12px]">'
                f'<span class="relative inline-flex rounded-full h-2 w-2 {bg("surface_high")}"></span>'
                f'<span class="font-bold {tx("muted")} uppercase tracking-wide text-[10px]">Stream Paused</span></div>'
            )

    @ui.refreshable
    def header_counters() -> None:
        raw_html(
            f'<div class="flex items-center gap-2 {bg("surface_low")} px-3.5 py-1 rounded-full border {bd("outline_variant")} text-[11px]">'
            f'<div class="flex items-center gap-1"><span class="{tx("muted")} text-[10px] uppercase">Processed:</span>'
            f'<span class="{tx("on_surface")} font-semibold">{state.events_total:,}</span></div>'
            f'<span class="{tx("outline_variant")}">/</span>'
            f'<div class="flex items-center gap-1"><span class="text-rose-600 font-semibold">{len(state.alerts)}</span>'
            '<span class="text-rose-700 text-[10px] uppercase">Alerts</span></div>'
            f'<span class="{tx("outline_variant")}">/</span>'
            f'<div class="flex items-center gap-1"><span class="{tx("primary")} font-semibold">{state.frozen_total}</span>'
            f'<span class="{tx("muted")} text-[10px] uppercase">Frozen</span></div></div>'
        )

    @ui.refreshable
    def rate_label() -> None:
        raw_html(f'<span class="font-semibold {tx("on_surface")} w-14 text-right text-[11px]">{state.sim.base_rate:.0f} tx/s</span>')

    @ui.refreshable
    def run_controls() -> None:
        label = "Pause Stream" if state.sim.running else "Resume Stream"
        ic = "pause" if state.sim.running else "play_arrow"
        cls = (
            f'flex items-center gap-1.5 px-3.5 py-1.5 {bg("primary")} hover:bg-[{C["primary_hover"]}] text-white rounded-full font-semibold text-[12px] shadow-sm transition-all active:scale-[0.98]'
            if state.sim.running else
            f'flex items-center gap-1.5 px-3.5 py-1.5 {bg("surface_high")} hover:{bg("surface_container")} {tx("on_surface")} rounded-full font-semibold text-[12px] shadow-sm transition-all active:scale-[0.98]'
        )
        raw_html(f'<button class="{cls}">{icon(ic, "text-[15px]")}<span>{label}</span></button>').on("click", lambda e: toggle_running())

    @ui.refreshable
    def kpi_strip() -> None:
        k = state.kpis()
        filters.throughput_history.append(k["events_per_min"])
        if len(filters.throughput_history) > 24:
            filters.throughput_history.pop(0)
        prev = filters.prev_events_per_min or k["events_per_min"]
        pct = 0.0 if prev == 0 else (k["events_per_min"] - prev) / prev * 100
        filters.prev_events_per_min = k["events_per_min"]
        trend_icon = "arrow_upward" if pct >= 0 else "arrow_downward"
        trend_cls = "text-emerald-700 bg-emerald-50" if pct >= 0 else "text-rose-700 bg-rose-50"

        open_alerts = [a for a in state.alerts.values() if a.status.value in ("new", "investigating")]
        critical_open = sum(1 for a in open_alerts if a.score.severity == Severity.CRITICAL)
        high_n = sum(1 for a in open_alerts if a.score.severity == Severity.HIGH)
        med_n = sum(1 for a in open_alerts if a.score.severity == Severity.MEDIUM)
        crit_n = sum(1 for a in open_alerts if a.score.severity == Severity.CRITICAL)
        total_sev = max(1, crit_n + high_n + med_n)

        var_pct = min(100, round(k["dollars_at_risk"] / max(filters.max_at_risk_seen, 1) * 100))
        filters.max_at_risk_seen = max(filters.max_at_risk_seen, k["dollars_at_risk"], 1.0)
        top_detector = "MONITORING"
        recent_alerts = state.recent_alerts(900)
        if recent_alerts:
            from collections import Counter
            counts = Counter(r.detector for a in recent_alerts for r in a.score.reasons[:1])
            if counts:
                top_detector = counts.most_common(1)[0][0].replace("_", " ")

        with ui.element("div").classes("grid grid-cols-4 gap-3.5 p-4 pb-2.5 shrink-0"):
            # Throughput
            with ui.element("div").classes(f'{bg("surface_lowest")} border {bd("outline_variant")} p-3.5 rounded-2xl shadow-sm flex flex-col justify-between'):
                raw_html(
                    f'<div class="flex items-center justify-between"><span class="text-[10px] font-bold uppercase tracking-wider {tx("muted")}">THROUGHPUT</span>'
                    f'<span class="flex items-center {trend_cls} px-2 py-0.5 rounded-full text-[10px] font-bold">{icon(trend_icon, "text-[11px] mr-0.5")} {pct:+.1f}%</span></div>'
                    f'<div class="my-2"><div class="text-2xl font-extrabold tracking-tight {tx("on_surface")} flex items-baseline gap-1">'
                    f'{k["events_per_min"]:.0f}<span class="text-xs font-normal {tx("muted")}">events/min</span></div></div>'
                    f'<svg class="w-full h-4 {tx("primary")} stroke-current fill-none opacity-75" preserveAspectRatio="none" viewBox="0 0 100 20">'
                    f'<path d="{sparkline_path(filters.throughput_history)}" stroke-linecap="round" stroke-width="2"></path></svg>'
                )
            # Open alerts
            with ui.element("div").classes(f'{bg("surface_lowest")} border {bd("outline_variant")} p-3.5 rounded-2xl shadow-sm flex flex-col justify-between'):
                raw_html(
                    f'<div class="flex items-center justify-between"><span class="text-[10px] font-bold uppercase tracking-wider {tx("muted")}">OPEN ALERTS</span>'
                    f'<span class="text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full text-[10px] font-bold flex items-center">{icon("warning", "text-[11px] mr-0.5")} Critical: {critical_open}</span></div>'
                    f'<div class="my-2"><div class="text-2xl font-extrabold tracking-tight {tx("on_surface")} flex items-baseline gap-1">'
                    f'{len(open_alerts)}<span class="text-xs font-normal {tx("muted")}">queued</span></div></div>'
                    f'<div class="w-full {bg("surface_high")} h-2 rounded-full overflow-hidden flex">'
                    f'<div class="bg-rose-500 h-full" style="width:{crit_n / total_sev * 100:.0f}%"></div>'
                    f'<div class="bg-amber-500 h-full" style="width:{high_n / total_sev * 100:.0f}%"></div>'
                    f'<div class="bg-emerald-500 h-full" style="width:{med_n / total_sev * 100:.0f}%"></div></div>'
                )
            # Frozen
            with ui.element("div").classes(f'{bg("surface_lowest")} border {bd("outline_variant")} p-3.5 rounded-2xl shadow-sm flex flex-col justify-between'):
                raw_html(
                    f'<div class="flex items-center justify-between"><span class="text-[10px] font-bold uppercase tracking-wider {tx("muted")}">FROZEN (15M)</span>'
                    f'<span class="{tx("primary")} {bg("primary_container", "80")} px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider">BLOCKED</span></div>'
                    f'<div class="my-2"><div class="text-2xl font-extrabold tracking-tight {tx("on_surface")} flex items-baseline gap-1">'
                    f'{k["frozen_count"]}<span class="text-xs font-normal {tx("muted")}">cards halted</span></div></div>'
                    f'<div class="text-[11px] font-semibold {tx("primary")} flex items-center justify-between">'
                    f'<span>{fmt_money0(state.prevented_total)} prevented</span>{icon("shield", "text-[14px]")}</div>'
                )
            # Value at risk
            with ui.element("div").classes(f'{bg("surface_lowest")} border {bd("outline_variant")} p-3.5 rounded-2xl shadow-sm flex flex-col justify-between'):
                raw_html(
                    f'<div class="flex items-center justify-between"><span class="text-[10px] font-bold uppercase tracking-wider {tx("muted")}">VALUE AT RISK (15M)</span>'
                    f'<span class="text-amber-800 bg-amber-50 px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider">{escape(top_detector)}</span></div>'
                    f'<div class="my-2"><div class="text-2xl font-extrabold tracking-tight {tx("on_surface")} flex items-baseline gap-1">{fmt_money0(k["dollars_at_risk"])}</div></div>'
                    f'<div class="flex items-center gap-2"><div class="flex-1 {bg("surface_high")} h-2 rounded-full overflow-hidden">'
                    f'<div class="{bg("primary")} h-full rounded-full" style="width:{var_pct}%"></div></div>'
                    f'<span class="text-[10px] font-semibold {tx("muted")}">{var_pct}% MAX</span></div>'
                )

    @ui.refreshable
    def severity_pills() -> None:
        with ui.element("div").classes("flex items-center gap-1 mb-1.5 overflow-x-auto pb-0.5 text-[11px]"):
            raw_html(f'<span class="text-[9px] font-bold {tx("muted")} uppercase mr-1">SEV:</span>')
            for key, label in [("ALL", "All"), ("critical", "Critical"), ("high", "High"), ("medium", "Med")]:
                raw_html(pill(label, filters.severity == key)).on("click", lambda e, k=key: set_severity(k))

    @ui.refreshable
    def status_pills() -> None:
        with ui.element("div").classes("flex items-center gap-1 overflow-x-auto text-[11px]"):
            raw_html(f'<span class="text-[9px] font-bold {tx("muted")} uppercase mr-1">STATUS:</span>')
            for key, label in [("ALL", "All"), ("new", "New"), ("investigating", "In Review"), ("frozen", "Frozen"), ("dismissed", "Dismissed")]:
                raw_html(pill(label, filters.status == key)).on("click", lambda e, k=key: set_status(k))

    @ui.refreshable
    def feed_body() -> None:
        items = state.recent_feed(limit=80)
        items = [it for it in items if it[0].ts >= filters.feed_cleared_at]
        if filters.channel != "ALL":
            items = [it for it in items if it[0].channel.value == ("online" if filters.channel == "ONLINE" else "card_present")]
        if filters.search:
            q = filters.search.lower()
            items = [it for it in items if q in it[0].id.lower() or q in it[0].card_token.lower() or q in it[0].merchant.lower() or q in it[0].country.lower()]
        items = items[:40]
        buffer_pill.refresh(len(items))
        if not items:
            with ui.element("div").classes(f"p-8 text-center {tx('muted')}"):
                ui.label("No matching transactions — press Resume Stream.")
        else:
            for i, (t, s) in enumerate(items):
                raw_html(feed_row_html(t, s, flash=(i == 0))).on(
                    "click", lambda e, tid=t.id: open_drawer(tid)
                )

    @ui.refreshable
    def buffer_pill(n: int = 0) -> None:
        raw_html(f'<span class="text-[10px] font-medium px-2 py-0.5 {bg("surface_container")} rounded-full {tx("muted")} shrink-0">BUFFER: {n} TX</span>')

    @ui.refreshable
    def alerts_body() -> None:
        alerts = [state.alerts[aid] for aid in state.alert_order if aid in state.alerts]
        if filters.status != "ALL":
            alerts = [a for a in alerts if a.status.value == filters.status]
        if filters.severity != "ALL":
            alerts = [a for a in alerts if a.score.severity.value == filters.severity]
        if filters.search:
            q = filters.search.lower()
            alerts = [a for a in alerts if q in a.transaction.id.lower() or q in a.transaction.card_token.lower() or q in a.transaction.merchant.lower()]
        alerts = alerts[:80]
        alerts_count_badge.refresh(len(alerts))
        rail_alert_badge.refresh()
        if not alerts:
            with ui.element("div").classes(f"p-8 text-center {tx('muted')}"):
                raw_html(icon("verified_user", "text-[32px] mb-2 block") + '<div class="text-[12px] font-semibold">No alerts match current filters.</div>')
        else:
            for alert in alerts:
                raw_html(alert_card_html(alert)).on("click", lambda e, tid=alert.transaction.id: open_drawer(tid))

    @ui.refreshable
    def alerts_count_badge(n: int = 0) -> None:
        raw_html(f'<span class="px-2 py-0.5 rounded-full bg-rose-100 text-rose-700 text-[10px] font-bold">{n} Active</span>')

    @ui.refreshable
    def rail_alert_badge() -> None:
        n = sum(1 for a in state.alerts.values() if a.status.value in ("new", "investigating"))
        raw_html(f'<span class="bg-rose-100 text-rose-700 px-2 py-0.5 rounded-full text-[10px] font-bold">{n}</span>')

    @ui.refreshable
    def rule_engine_load() -> None:
        k = state.kpis()
        ops = k["events_per_min"] / 60
        cap = max(state.sim.base_rate, state.sim.burst_rate, 1)
        pct = min(100, round(ops / cap * 100))
        raw_html(
            f'<div class="flex justify-between items-center text-[10px] font-semibold {tx("muted")} mb-1.5 uppercase tracking-wider">'
            f'<span>RULE ENGINE LOAD</span><span class="{tx("on_surface")} font-bold">{ops:.1f} OPS/S</span></div>'
            f'<div class="w-full {bg("surface_high")} h-1.5 rounded-full overflow-hidden">'
            f'<div class="{bg("primary")} h-full rounded-full transition-all duration-300" style="width:{pct}%"></div></div>'
            f'<div class="text-[10px] {tx("muted")} mt-1.5 text-right">Pipeline: {pct}% capacity</div>'
        )

    @ui.refreshable
    def drawer_status_badge() -> None:
        txn_id = filters.drawer_txn_id
        if not txn_id:
            return
        alert = find_alert_by_txn(txn_id)
        status = alert.status.value if alert else "new"
        raw_html(f'<span class="px-2 py-0.5 text-[9px] font-bold rounded-full {STATUS_BADGE[status]}">{STATUS_LABEL[status]}</span>')

    @ui.refreshable
    def drawer_body() -> None:
        txn_id = filters.drawer_txn_id
        alert = find_alert_by_txn(txn_id) if txn_id else None
        feed_item = find_feed_item(txn_id) if txn_id else None
        if not txn_id or (alert is None and feed_item is None):
            with ui.element("div").classes(f"p-8 text-center {tx('muted')}"):
                ui.label("Select a transaction or alert to open its case dossier.")
            return

        t = alert.transaction if alert else feed_item[0]
        score = alert.score if alert else feed_item[1]

        with ui.element("div").classes("flex-1 overflow-y-auto p-4 space-y-3.5"):
            # Hero summary
            with ui.element("div").classes(f'{bg("surface_low")} border {bd("outline_subtle")} p-3.5 rounded-2xl'):
                raw_html(
                    '<div class="flex justify-between items-start mb-2">'
                    f'<div><span class="text-[9px] font-bold uppercase tracking-wider {tx("muted")}">TRANSACTION ID</span>'
                    f'<div class="text-[13px] font-bold {tx("on_surface")}">{escape(t.id)}</div></div>'
                    f'<div class="text-right"><span class="text-[9px] font-bold uppercase tracking-wider {tx("muted")}">AUTHORIZED AMOUNT</span>'
                    f'<div class="text-lg font-extrabold {tx("on_surface")}">{fmt_money(t.amount, t.currency)}</div></div></div>'
                    f'<div class="mt-2.5 pt-2.5 border-t {bd("outline_subtle")}">'
                    f'<div class="flex justify-between items-center text-[11px] mb-1"><span class="{tx("muted")} font-medium">Composite Risk Score</span>'
                    f'<span class="font-bold {tx("primary")} text-[13px]">{score.risk_score:.2f} / 1.00</span></div>'
                    f'<div class="w-full {bg("surface_high")} h-2 rounded-full overflow-hidden">'
                    f'<div class="{bg("primary")} h-full rounded-full transition-all duration-500" style="width:{min(100, round(score.risk_score * 100))}%"></div></div></div>'
                )
            # Entity metadata
            with ui.element("div").classes(f'{bg("surface_low")} border {bd("outline_subtle")} p-3.5 rounded-2xl space-y-2'):
                raw_html(f'<div class="text-[10px] font-bold {tx("primary")} tracking-wider uppercase">Entity Metadata</div>')
                fields = [
                    ("CARD TOKEN", f"•••• {t.card_token[-4:]}"), ("USER ID", t.user_id),
                    ("MERCHANT", t.merchant), ("MCC / CATEGORY", t.mcc),
                    ("CHANNEL", t.channel.value.upper()), ("IP & GEOLOCATION", f"{t.ip} ({t.country})"),
                ]
                grid = "".join(
                    f'<div><span class="{tx("muted")} text-[9px] block">{k}</span><span class="{tx("on_surface")} font-semibold text-[11px]">{escape(str(v))}</span></div>'
                    for k, v in fields
                )
                grid += (
                    f'<div class="col-span-2"><span class="{tx("muted")} text-[9px] block">DEVICE FINGERPRINT</span>'
                    f'<span class="{tx("on_surface")} text-[10px]">{escape(t.device_fp)}</span></div>'
                    f'<div class="col-span-2"><span class="{tx("muted")} text-[9px] block">TIMESTAMP</span>'
                    f'<span class="{tx("on_surface")} text-[10px]">{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t.ts))}</span></div>'
                )
                raw_html(f'<div class="grid grid-cols-2 gap-x-3 gap-y-2 text-[11px]">{grid}</div>')
            # Detector explainability
            with ui.element("div").classes(f'{bg("surface_low")} border {bd("outline_subtle")} p-3.5 rounded-2xl'):
                raw_html(f'<div class="text-[10px] font-bold text-rose-700 tracking-wider uppercase mb-2">Rule Explainability Weights</div>')
                if score.reasons:
                    items_html = "".join(
                        f'<div class="flex items-start justify-between {bg("surface_lowest")} p-2 rounded-xl border {bd("outline_subtle")} text-[11px]">'
                        f'<div class="flex items-center gap-1.5">{icon("policy", "text-rose-600 text-[13px]")}<span class="{tx("on_surface")}">{escape(r.text)}</span></div>'
                        f'<span class="text-rose-700 font-bold shrink-0 ml-2">+{score.contributions.get(r.detector, 0.0):.2f}</span></div>'
                        for r in score.reasons
                    )
                else:
                    items_html = f'<div class="text-[11px] {tx("muted")} p-2">No detectors fired — this transaction scored within expected variance.</div>'
                raw_html(f'<div class="space-y-1.5">{items_html}</div>')
            # Same-card recent activity
            with ui.element("div").classes(f'{bg("surface_low")} border {bd("outline_subtle")} p-3.5 rounded-2xl'):
                profile = state.profile_for(t.card_token)
                raw_html(
                    f'<div class="flex justify-between items-center mb-2"><span class="text-[11px] font-bold {tx("on_surface")}">Card Recent Velocity Baseline</span>'
                    f'<span class="text-[9px] {tx("muted")}">Baseline: ${profile.mean_amount:,.0f}</span></div>'
                )
                similar = [it for it in state.recent_feed(card_token=t.card_token, limit=6) if it[0].id != t.id][:4]
                if similar:
                    rows = "".join(
                        f'<div class="flex justify-between items-center {tx("muted_dark")} py-1 border-b {bd("outline_subtle")} text-[10px]">'
                        f'<span>{time_ago(st.ts)} · {escape(st.merchant)} ({escape(st.channel.value.upper())})</span>'
                        f'<span class="{"text-emerald-700" if sr.risk_score < 0.4 else "text-rose-700"} font-bold">{fmt_money(st.amount, st.currency)} · {"OK" if sr.risk_score < 0.4 else "ALERT"} ({sr.risk_score:.2f})</span></div>'
                        for st, sr in similar
                    )
                else:
                    rows = f'<div class="text-[10px] {tx("muted")} py-1">No other recent activity on this card.</div>'
                rows += (
                    f'<div class="flex justify-between items-center py-1 {tx("primary")} font-bold text-[10px]">'
                    f'<span>CURRENT · {escape(t.merchant)}</span><span>{fmt_money(t.amount, t.currency)} · SCORE {score.risk_score:.2f}</span></div>'
                )
                raw_html(f'<div class="space-y-1.5 text-[10px]">{rows}</div>')
            # Notes
            with ui.element("div").classes(f'{bg("surface_low")} border {bd("outline_subtle")} p-3.5 rounded-2xl'):
                raw_html(f'<div class="text-[11px] font-bold {tx("on_surface")} mb-1.5">Investigator Case Notes</div>')
                refs["note"] = ui.textarea(value=(alert.note if alert else ""), placeholder="Add observations, syndicate tags, or cardholder contact notes...") \
                    .props("outlined dense").classes("w-full text-[11px]")
                with ui.element("div").classes("flex justify-end mt-1.5"):
                    raw_html(
                        f'<button class="px-3 py-1 {bg("surface_container")} hover:{bg("surface_high")} border {bd("outline_variant")} text-[11px] font-semibold {tx("on_surface")} rounded-full transition-all active:scale-95">Save Note</button>'
                    ).on("click", lambda e: save_note())
            # Audit trail
            with ui.element("div").classes(f'{bg("surface_low")} border {bd("outline_subtle")} p-3.5 rounded-2xl'):
                raw_html(f'<div class="text-[10px] font-bold {tx("muted")} uppercase tracking-wider mb-2">Enforcement Audit Trail</div>')
                history = alert.history if alert else []
                if history:
                    rows = "".join(
                        f'<div class="flex items-center gap-1.5 py-1 border-b {bd("outline_subtle")}">{icon("history", "text-[12px] text-[" + C["muted"] + "]")}'
                        f'<span class="{tx("muted_dark")} text-[10px]">{time_ago(h.ts)} — {escape(h.text)}</span></div>'
                        for h in reversed(history)
                    )
                else:
                    rows = f'<div class="text-[10px] {tx("muted")} py-1">No enforcement actions yet.</div>'
                raw_html(f'<div class="space-y-1">{rows}</div>')

        # Action bar
        with ui.element("div").classes(f'p-3 {bg("surface_low")} border-t {bd("outline_variant")} flex items-center justify-between gap-2'):
            raw_html(
                f'<button class="flex-1 py-1.5 {bg("surface_lowest")} hover:{bg("surface_container")} border {bd("outline_variant")} {tx("on_surface")} text-[11px] font-semibold rounded-full shadow-sm transition-all active:scale-[0.98]">Review</button>'
            ).on("click", lambda e: do_action(AlertStatus.INVESTIGATING))
            raw_html(
                f'<button class="flex-1 py-1.5 {bg("primary")} hover:bg-[{C["primary_hover"]}] text-white text-[11px] font-semibold rounded-full shadow-sm transition-all active:scale-[0.98]">Freeze Card</button>'
            ).on("click", lambda e: do_action(AlertStatus.FROZEN))
            raw_html(
                '<button class="flex-1 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white text-[11px] font-semibold rounded-full shadow-sm transition-all active:scale-[0.98]">Allow</button>'
            ).on("click", lambda e: do_action(AlertStatus.DISMISSED))

    # -- layout --------------------------------------------------------------
    with ui.element("div").classes(f'{bg("background")} {tx("on_surface")} antialiased h-screen flex flex-col overflow-hidden'):
        # Top app bar
        with ui.element("header").classes(f'flex flex-nowrap items-center justify-between px-6 h-16 {bg("surface_lowest")} border-b {bd("outline_variant")} z-40 shrink-0 gap-3 overflow-x-auto'):
            with ui.element("div").classes("flex items-center gap-3 min-w-0"):
                raw_html(
                    f'<div class="flex items-center gap-2.5 shrink-0"><div class="w-8 h-8 rounded-xl {bg("primary")} text-white flex items-center justify-center font-bold text-sm shadow-sm">R</div>'
                    f'<div class="flex flex-col"><span class="text-[16px] font-bold tracking-tight {tx("on_surface")} leading-tight">RiskPulse</span>'
                    f'<span class="text-[10px] font-medium {tx("muted")} tracking-tight">Fraud Operations</span></div></div>'
                    f'<div class="h-5 w-px {bg("outline_variant")} shrink-0"></div>'
                )
                live_indicator()
                raw_html(
                    f'<button class="flex items-center gap-1.5 px-3 py-1 {bg("surface_low")} hover:{bg("surface_container")} border {bd("outline_variant")} {tx("muted_dark")} hover:text-[{C["on_surface"]}] text-[11px] font-medium rounded-full transition-all active:scale-[0.98] shrink-0">'
                    f'{icon("wifi_off", "text-[13px]")}<span>Simulate Hiccup</span></button>'
                ).on("click", lambda e: toggle_hiccup())
                raw_html(
                    f'<nav class="flex items-center gap-1 shrink-0">'
                    f'<button class="{tx("primary")} font-semibold text-[13px] px-3.5 py-1 rounded-full {bg("primary_container", "70")} border border-[{C["primary"]}]/20">Console</button>'
                    f'<button class="{tx("muted_dark")} hover:text-[{C["on_surface"]}] hover:{bg("surface_low")} font-medium text-[13px] px-3 py-1 rounded-full transition-colors">Simulation</button>'
                    f'<button class="{tx("muted_dark")} hover:text-[{C["on_surface"]}] hover:{bg("surface_low")} font-medium text-[13px] px-3 py-1 rounded-full transition-colors">Policies</button>'
                    f'<button class="{tx("muted_dark")} hover:text-[{C["on_surface"]}] hover:{bg("surface_low")} font-medium text-[13px] px-3 py-1 rounded-full transition-colors">Audit Logs</button></nav>'
                )
            with ui.element("div").classes("flex items-center gap-3 shrink-0"):
                header_counters()
                raw_html(
                    f'<button class="flex items-center gap-1.5 px-3.5 py-1.5 {bg("surface_lowest")} hover:{bg("surface_container")} border {bd("outline_variant")} {tx("on_surface")} text-[12px] font-semibold rounded-full shadow-sm transition-all active:scale-[0.98]">'
                    f'{icon("download", "text-[15px]")}<span class="inline">Export CSV</span></button>'
                ).on("click", lambda e: export_csv())
                raw_html(
                    f'<button class="flex items-center gap-1.5 px-3.5 py-1.5 {bg("primary")} hover:bg-[{C["primary_hover"]}] text-white text-[12px] font-semibold rounded-full shadow-sm transition-all active:scale-[0.98]">'
                    f'{icon("lock_clock", "text-[15px]")}<span class="inline">Emergency Freeze</span></button>'
                ).on("click", lambda e: emergency_freeze())
                raw_html(
                    f'<div class="h-5 w-px {bg("outline_variant")}"></div>'
                    f'<div class="w-8 h-8 rounded-full {bg("surface_high")} border {bd("outline_variant")} flex items-center justify-center font-bold text-[11px] {tx("on_surface")}" title="Investigator SOC Profile">SOC</div>'
                )

        hiccup_banner()
        error_banner()

        with ui.element("div").classes("flex flex-1 overflow-hidden min-h-0"):
            # Left rail
            with ui.element("aside").classes(f'w-56 h-full min-h-0 shrink-0 {bg("surface_lowest")} border-r {bd("outline_variant")} flex flex-col justify-between p-3.5 overflow-y-auto'):
                with ui.element("div"):
                    raw_html(
                        f'<div class="{bg("surface_low")} p-3 rounded-xl border {bd("outline_subtle")} mb-3.5 flex items-center justify-between">'
                        f'<div><div class="text-[12px] font-bold {tx("on_surface")}">SOC-US-EAST</div>'
                        '<div class="text-[10px] font-semibold text-emerald-700 flex items-center gap-1.5 mt-0.5">'
                        '<span class="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>CLUSTER HEALTHY</div></div>'
                        f'{icon("dns", tx("muted") + " text-[18px]")}</div>'
                    )
                    raw_html(
                        f'<nav class="space-y-1">'
                        f'<button class="w-full flex items-center gap-2.5 px-3 py-2 {bg("primary_container", "60")} {tx("primary")} font-semibold text-[13px] rounded-xl">{icon("stream", "text-[17px]")}<span>Live Stream</span></button>'
                        f'<button class="w-full flex items-center justify-between px-3 py-2 {tx("muted_dark")} font-medium text-[13px] rounded-xl"><div class="flex items-center gap-2.5">{icon("warning", "text-[17px]")}<span>Alerts Queue</span></div></button>'
                        f'<button class="w-full flex items-center gap-2.5 px-3 py-2 {tx("muted_dark")} font-medium text-[13px] rounded-xl">{icon("travel_explore", "text-[17px]")}<span>Investigation</span></button>'
                        f'<button class="w-full flex items-center gap-2.5 px-3 py-2 {tx("muted_dark")} font-medium text-[13px] rounded-xl">{icon("shield", "text-[17px]")}<span>Policy Rules</span></button>'
                        f'<button class="w-full flex items-center gap-2.5 px-3 py-2 {tx("muted_dark")} font-medium text-[13px] rounded-xl">{icon("monitoring", "text-[17px]")}<span>Telemetry</span></button>'
                        f'</nav>'
                    )
                    with ui.element("div").classes("mt-1"):
                        pass
                    rail_alert_badge()
                    with ui.element("div").classes(f'mt-5 p-3 {bg("surface_low")} rounded-xl border {bd("outline_subtle")}'):
                        rule_engine_load()
                with ui.element("div").classes(f'space-y-1 border-t {bd("outline_variant")} pt-3'):
                    raw_html(
                        f'<button class="w-full flex items-center gap-2 px-2 py-1.5 {tx("muted")} text-[12px] font-medium">{icon("help", "text-[16px]")}<span>Documentation</span></button>'
                        f'<button class="w-full flex items-center gap-2 px-2 py-1.5 {tx("muted")} text-[12px] font-medium">{icon("dns", "text-[16px]")}<span>Diagnostics</span></button>'
                        f'<div class="text-[10px] {tx("muted")} text-center pt-1">v1.0.0-DEMO · PY-E1</div>'
                    )

            # Main workspace
            with ui.element("main").classes(f'flex-1 flex flex-col min-w-0 min-h-0 h-full {bg("background")} overflow-hidden'):
                kpi_strip()

                # Control bar
                with ui.element("section").classes(f'mx-4 mb-3 px-4 py-2 {bg("surface_lowest")} border {bd("outline_variant")} rounded-2xl flex flex-wrap items-center justify-between gap-3 shrink-0 shadow-sm'):
                    with ui.element("div").classes("flex items-center gap-2.5"):
                        run_controls()
                        with ui.element("div").classes(f'flex items-center gap-2 px-3 py-1 {bg("surface_low")} rounded-full border {bd("outline_variant")} text-[11px]'):
                            raw_html(f'<span class="{tx("muted")} font-bold text-[10px] uppercase">Rate</span>')
                            ui.slider(min=1, max=50, value=state.sim.base_rate, step=1, on_change=on_speed_change) \
                                .props(f'thumb-color="#b8431e" track-color="#e5e1d6" color="#b8431e"').classes("w-20")
                            rate_label()
                    with ui.element("div").classes("flex items-center gap-1.5 flex-wrap"):
                        raw_html(f'<span class="text-[10px] font-bold {tx("muted")} uppercase tracking-wider mr-1">Inject Attack:</span>')
                        for key, (label, _fn) in simulator.SCENARIOS.items():
                            emoji = SCENARIO_EMOJI.get(key, "⚠️")
                            raw_html(
                                f'<button class="px-2.5 py-1 {bg("surface_low")} hover:{bg("surface_container")} border {bd("outline_variant")} hover:border-[{C["primary"]}] {tx("on_surface")} text-[11px] font-semibold rounded-full transition-all active:scale-95">{emoji} {escape(label)}</button>'
                            ).on("click", lambda e, k=key: inject(k))
                    with ui.element("div").classes(f'flex items-center gap-2 px-3 py-1 {bg("surface_low")} rounded-full border {bd("outline_variant")}'):
                        ui.switch(value=state.policy.auto_freeze_enabled, on_change=on_policy_toggle).props('color="#b8431e" dense')
                        raw_html(f'<span class="text-[11px] font-bold {tx("on_surface")}">Auto-Freeze ≥</span>')
                        ui.number(value=state.policy.auto_freeze_threshold, min=0.0, max=1.0, step=0.05, on_change=on_threshold_change) \
                            .props("dense borderless").classes(f'w-12 {bg("surface_lowest")} border {bd("outline_variant")} rounded px-1 text-[11px] {tx("primary")} font-bold text-center')

                # Split workspace
                with ui.element("div").classes("flex-1 flex overflow-hidden px-4 pb-4 gap-3.5 min-h-0"):
                    # Live feed
                    with ui.element("div").classes(f'flex-1 flex flex-col min-w-0 {bg("surface_lowest")} border {bd("outline_variant")} rounded-2xl shadow-sm overflow-hidden'):
                        with ui.element("div").classes(f'flex items-center justify-between px-4 py-2.5 border-b {bd("outline_variant")} {bg("surface_low", "40")} shrink-0 gap-3'):
                            with ui.element("div").classes("flex items-center gap-2 min-w-0"):
                                raw_html(f'{icon("dataset", tx("primary") + " text-[17px] shrink-0")}<span class="font-bold text-[13px] {tx("on_surface")} truncate">Live Ingestion Stream</span>')
                                buffer_pill()
                            with ui.element("div").classes("flex items-center gap-2 shrink-0"):
                                ui.input(placeholder="Search Tx, Card, Geo...", on_change=on_search_change) \
                                    .props(f'dense outlined color="#b8431e"').classes("w-56 text-[11px]")
                                ui.select({"ALL": "Channel: All", "ONLINE": "Online (CNP)", "POS": "In-Store / POS"},
                                          value=filters.channel, on_change=on_channel_change) \
                                    .props('dense outlined').classes("text-[11px]")
                                raw_html(f'<button class="text-[11px] font-semibold {tx("muted")} hover:text-[{C["primary"]}] underline ml-1">Clear</button>') \
                                    .on("click", lambda e: clear_feed_display())
                        raw_html(
                            f'<div class="grid sticky top-0 {bg("surface_low", "95")} backdrop-blur border-b {bd("outline_variant")} z-10 '
                            f'text-[10px] font-bold {tx("muted")} uppercase tracking-wider" style="{FEED_GRID}">'
                            '<div class="px-4 py-1.5">TIME</div><div class="px-2 py-1.5">TX ID</div>'
                            '<div class="px-2 py-1.5">MERCHANT</div><div class="px-2 py-1.5">CARD TOKEN</div>'
                            '<div class="px-2 py-1.5 text-center">GEO</div><div class="px-2 py-1.5 text-center">CHANNEL</div>'
                            '<div class="px-2 py-1.5">RISK SCORE</div><div class="px-4 py-1.5 text-right">AMOUNT</div>'
                            '</div>'
                        )
                        with ui.element("div").classes("flex-1 overflow-y-auto"):
                            feed_body()

                    # Alerts queue
                    with ui.element("div").classes(f'w-[420px] shrink-0 flex flex-col {bg("surface_lowest")} border {bd("outline_variant")} rounded-2xl shadow-sm overflow-hidden'):
                        with ui.element("div").classes(f'p-3 border-b {bd("outline_variant")} shrink-0 {bg("surface_low", "40")}'):
                            with ui.element("div").classes("flex items-center justify-between mb-2"):
                                raw_html(f'<div class="flex items-center gap-2">{icon("notification_important", "text-rose-600 text-[17px]")}<span class="font-bold text-[13px] {tx("on_surface")}">Flagged Alerts Queue</span></div>')
                                alerts_count_badge()
                            severity_pills()
                            status_pills()
                        with ui.element("div").classes(f'flex-1 overflow-y-auto p-3 space-y-2.5 {bg("surface_lowest")}'):
                            alerts_body()

            # Investigation drawer — a row-sibling of the rail and main (not
            # a sibling of this whole row), so it opens as a third column
            # rather than stacking as a new row underneath everything.
            with ui.element("aside").classes(f'w-0 h-full min-h-0 overflow-hidden shrink-0 {bg("surface_lowest")} border-l {bd("outline_variant")} flex flex-col z-50 shadow-2xl') \
                    .style("width:0px") as drawer:
                with ui.element("div").classes("w-[420px] h-full flex flex-col min-h-0"):
                    with ui.element("div").classes(f'flex items-center justify-between px-5 py-3.5 {bg("surface_low", "70")} border-b {bd("outline_variant")} shrink-0'):
                        with ui.element("div").classes("flex items-center gap-2"):
                            raw_html(
                                f'<div class="w-7 h-7 rounded-full {bg("primary_container")} {tx("primary")} flex items-center justify-center">{icon("travel_explore", "text-[15px]")}</div>'
                                f'<span class="font-bold text-[14px] {tx("on_surface")}">Case Dossier</span>'
                            )
                            drawer_status_badge()
                        raw_html(f'<button class="p-1 {tx("muted")} hover:text-[{C["on_surface"]}] rounded-full hover:{bg("surface_high")} transition-colors">{icon("close", "text-[18px]")}</button>') \
                            .on("click", lambda e: close_drawer())
                    drawer_body()

    def periodic_refresh() -> None:
        # Always-cheap, time-derived bits redraw every tick.
        kpi_strip.refresh()
        error_banner.refresh()
        live_indicator.refresh()
        header_counters.refresh()
        rail_alert_badge.refresh()
        rule_engine_load.refresh()
        # The feed/alert lists tear down and rebuild their whole DOM subtree
        # on every .refresh() — only pay for that when data actually changed
        # (new transaction, status change, ...), not on a fixed clock tick.
        if state.version != filters.last_seen_version:
            filters.last_seen_version = state.version
            feed_body.refresh()
            alerts_body.refresh()

    ui.timer(0.4, periodic_refresh)

    def on_key(e) -> None:
        if not e.action.keydown:
            return
        k = str(e.key).lower()
        if k == "escape":
            close_drawer()
        elif filters.drawer_txn_id:
            if k == "i":
                do_action(AlertStatus.INVESTIGATING)
            elif k == "f":
                do_action(AlertStatus.FROZEN)
            elif k == "a":
                do_action(AlertStatus.DISMISSED)

    ui.keyboard(on_key=on_key)
