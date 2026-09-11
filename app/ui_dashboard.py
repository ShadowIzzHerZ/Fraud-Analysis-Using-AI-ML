"""The NiceGUI dashboard: dark ops shell, live feed, alerts, investigation
drawer, and simulator controls — all in one page per the PRD ("a single web
app"). Rendering is split into small `@ui.refreshable` regions so a 0.3s
timer can redraw the data-driven parts (feed, alerts, KPIs) without ever
touching in-progress input like the note textarea or an open dropdown.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Optional

from nicegui import app, ui

from app import simulator
from app.models import Alert, AlertStatus, Reason, ScoreResult, Severity, Transaction
from app.state import state

app.add_static_files("/static", str(Path(__file__).parent / "static"))


def raw_html(content: str = ""):
    """ui.html wrapper: all content passed through here is markup we built
    ourselves (with `escape()` already applied to any free-text/user input),
    so it's safe to render unsanitized — sanitizing would strip the class
    attributes the whole design system depends on."""
    return ui.html(content, sanitize=False)


# Quasar's own button color utility classes (bg-primary, text-white, ...) are
# injected at runtime and win any stylesheet specificity fight against our
# theme classes — so button color is enforced with inline !important styles,
# which always outrank stylesheet rules regardless of load order.
_BTN_STYLES = {
    "info": "background: var(--info) !important; color: #fff !important; border: none !important;",
    "danger": "background: var(--danger) !important; color: #fff !important; border: none !important;",
    "ghost": "background: transparent !important; color: var(--text-muted) !important; "
             "border: 1px solid var(--border) !important; box-shadow: none !important;",
}


def style_btn(btn, kind: str):
    return btn.style(_BTN_STYLES[kind])

SEVERITY_OPTIONS = ["critical", "high", "medium", "low"]
STATUS_OPTIONS = ["all", "new", "investigating", "frozen", "dismissed"]
STATUS_LABELS = {"all": "All statuses", "new": "New", "investigating": "Investigating",
                  "frozen": "Frozen", "dismissed": "Dismissed"}


# -- formatting helpers -------------------------------------------------------------

def fmt_money(amount: float, currency: str) -> str:
    return f"{currency} {amount:,.2f}"


def fmt_time(ts: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts))


def time_ago(ts: float) -> str:
    d = max(0, time.time() - ts)
    if d < 60:
        return f"{int(d)}s ago"
    if d < 3600:
        return f"{int(d // 60)}m ago"
    return f"{int(d // 3600)}h ago"


def risk_bar_html(score: float, severity: Severity) -> str:
    pct = max(3, min(100, round(score * 100)))
    return (
        f'<div class="risk-bar-track"><div class="risk-bar-fill {severity.value}" '
        f'style="width:{pct}%"></div></div>'
        f'<div class="risk-score-text mono">{score:.2f}</div>'
    )


def reason_chips_html(reasons: list[Reason]) -> str:
    if not reasons:
        return '<span class="reason-chip">no detectors fired</span>'
    return "".join(
        f'<span class="reason-chip"><code>{escape(r.detector)}</code>{escape(r.text)}</span>'
        for r in reasons
    )


def feed_row_html(txn: Transaction, result: ScoreResult) -> str:
    return (
        '<div class="feed-row">'
        f'<div class="feed-time mono">{fmt_time(txn.ts)}</div>'
        '<div class="feed-main">'
        f'<div class="feed-merchant">{escape(txn.merchant)}</div>'
        f'<div class="feed-sub">{escape(txn.card_token)} · {escape(txn.country)} · {escape(txn.channel.value)}</div>'
        "</div>"
        f"{risk_bar_html(result.risk_score, result.severity)}"
        f'<div class="feed-amount mono">{fmt_money(txn.amount, txn.currency)}</div>'
        "</div>"
    )


def alert_row_html(alert: Alert, selected: bool) -> str:
    t = alert.transaction
    sev = alert.score.severity.value
    selected_cls = " selected" if selected else ""
    return (
        f'<div class="alert-row sev-{sev}{selected_cls}">'
        '<div class="alert-row-main">'
        '<div class="alert-row-top">'
        f'<span class="badge sev-{sev}">{sev}</span>'
        f'<span class="badge status-{alert.status.value}">{alert.status.value}</span>'
        f'<span class="risk-score-text mono">{alert.score.risk_score:.2f}</span>'
        f'<span class="alert-row-meta" style="margin-left:auto">{time_ago(alert.created_at)}</span>'
        "</div>"
        f'<div class="alert-row-merchant">{escape(t.merchant)} · {fmt_money(t.amount, t.currency)}</div>'
        f'<div class="alert-row-meta">{escape(t.card_token)} · {escape(t.country)} · {escape(t.channel.value)}</div>'
        f'<div class="alert-row-reasons">{reason_chips_html(alert.score.reasons)}</div>'
        "</div>"
        "</div>"
    )


# -- per-client UI state -------------------------------------------------------------

@dataclass
class UIFilters:
    search: str = ""
    severity: set = field(default_factory=lambda: set(SEVERITY_OPTIONS))
    status: str = "all"
    selected_alert_id: Optional[str] = None


@ui.page("/")
def dashboard_page() -> None:
    filters = UIFilters()
    refs: dict = {"note": None}

    ui.add_head_html(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600'
        '&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">'
        '<link rel="stylesheet" href="/static/theme.css">'
    )
    ui.page_title("RiskPulse — Fraud Ops")

    # -- filter handlers --------------------------------------------------------------
    def on_search_change(e) -> None:
        filters.search = (e.value or "").strip()
        feed_body.refresh()
        alerts_body.refresh()

    def on_severity_change(e) -> None:
        filters.severity = set(e.value or [])
        alerts_body.refresh()

    def on_status_change(e) -> None:
        filters.status = e.value
        alerts_body.refresh()

    def select_alert(alert_id: str) -> None:
        filters.selected_alert_id = alert_id
        drawer.style("transform: translateX(0)")
        alerts_body.refresh()
        drawer_body.refresh()

    def close_drawer() -> None:
        drawer.style("transform: translateX(105%)")
        filters.selected_alert_id = None
        alerts_body.refresh()

    def do_action(alert_id: str, new_status: AlertStatus) -> None:
        note_val = refs["note"].value if refs["note"] else ""
        updated = state.set_alert_status(alert_id, new_status, note=note_val)
        if updated:
            kind = {"investigating": "ongoing", "frozen": "negative", "dismissed": "warning"}.get(new_status.value, "info")
            ui.notify(
                f"{STATUS_LABELS.get(new_status.value, new_status.value)}: "
                f"{updated.transaction.merchant} · {updated.transaction.id}",
                position="bottom-right", timeout=4000, type=kind,
            )
        alerts_body.refresh()
        drawer_body.refresh()
        kpi_strip.refresh()

    def export_csv() -> None:
        csv_text = state.alerts_csv(limit=500)
        ui.download(csv_text.encode("utf-8"), filename="alerts_export.csv", media_type="text/csv")
        ui.notify("Exported alerts_export.csv", position="bottom-right", timeout=4000)

    def toggle_running() -> None:
        state.sim.running = not state.sim.running
        run_controls.refresh()
        live_pill.refresh()

    def on_speed_change(e) -> None:
        state.sim.base_rate = float(e.value)

    def on_policy_toggle(e) -> None:
        state.policy.auto_freeze_enabled = bool(e.value)

    def on_threshold_change(e) -> None:
        try:
            state.policy.auto_freeze_threshold = max(0.0, min(1.0, float(e.value)))
        except (TypeError, ValueError):
            pass

    def inject(scenario_key: str) -> None:
        label = simulator.SCENARIOS[scenario_key][0]
        n = simulator.inject_scenario(scenario_key)
        ui.notify(f'Injected "{label}" — {n} events queued', position="bottom-right", timeout=4000, type="warning")

    # -- refreshable regions --------------------------------------------------------------
    @ui.refreshable
    def error_banner() -> None:
        if state.stream_error:
            with ui.element("div").style(
                "background: rgba(255,92,92,0.12); border:1px solid var(--danger); color: var(--danger); "
                "border-radius: var(--radius); padding: 10px 14px; margin-bottom: 14px; font-size: 13px; "
                "display:flex; align-items:center; justify-content:space-between; gap: 12px;"
            ):
                ui.label(f"Stream hiccup — showing last known state. ({state.stream_error})")

                def clear_error() -> None:
                    state.stream_error = None
                    error_banner.refresh()

                style_btn(ui.button("Dismiss", on_click=clear_error).props("flat dense"), "ghost")

    @ui.refreshable
    def live_pill() -> None:
        cls = "live-pill" if state.sim.running else "live-pill paused"
        text = "LIVE" if state.sim.running else "PAUSED"
        raw_html(f'<div class="{cls}"><span class="live-dot"></span>{text}</div>')

    @ui.refreshable
    def kpi_strip() -> None:
        k = state.kpis()
        cards = [
            ("Throughput", f"{k['events_per_min']:.0f} /min", ""),
            ("Open Alerts", f"{k['open_alerts']}", "warn" if k["open_alerts"] else ""),
            ("Frozen (15m)", f"{k['frozen_count']}", "danger" if k["frozen_count"] else ""),
            ("$ At Risk (15m)", f"${k['dollars_at_risk']:,.0f}", "danger" if k["dollars_at_risk"] else "accent"),
        ]
        with ui.element("div").classes("kpi-strip"):
            for label, value, cls in cards:
                with ui.element("div").classes("kpi-card"):
                    raw_html(f'<div class="kpi-label">{label}</div><div class="kpi-value {cls}">{value}</div>')

    @ui.refreshable
    def feed_body() -> None:
        items = state.recent_feed(limit=60)
        if filters.search:
            q = filters.search.lower()
            items = [
                it for it in items
                if q in it[0].id.lower() or q in it[0].card_token.lower() or q in it[0].merchant.lower()
            ]
        items = items[:40]
        if not items:
            with ui.element("div").classes("panel-empty"):
                ui.label("No transactions yet — press Start Stream.")
        else:
            raw_html("".join(feed_row_html(t, s) for t, s in items))

    @ui.refreshable
    def alerts_body() -> None:
        alerts = [state.alerts[aid] for aid in state.alert_order if aid in state.alerts]
        if filters.status != "all":
            alerts = [a for a in alerts if a.status.value == filters.status]
        alerts = [a for a in alerts if a.score.severity.value in filters.severity]
        if filters.search:
            q = filters.search.lower()
            alerts = [
                a for a in alerts
                if q in a.transaction.id.lower() or q in a.transaction.card_token.lower()
                or q in a.transaction.merchant.lower()
            ]
        alerts = alerts[:80]
        if not alerts:
            with ui.element("div").classes("panel-empty"):
                ui.label("No alerts match these filters.")
        else:
            for alert in alerts:
                raw_html(alert_row_html(alert, filters.selected_alert_id == alert.id)).on(
                    "click", lambda e, aid=alert.id: select_alert(aid)
                ).style("cursor:pointer")

    @ui.refreshable
    def drawer_body() -> None:
        alert = state.alerts.get(filters.selected_alert_id) if filters.selected_alert_id else None
        with ui.element("div").style("display:flex; align-items:center; justify-content:space-between;"):
            ui.label("Investigation").classes("panel-title")
            raw_html('<span class="drawer-close">✕</span>').on("click", lambda e: close_drawer())
        if alert is None:
            with ui.element("div").classes("panel-empty"):
                ui.label("Select an alert to see the full picture.")
            return

        t = alert.transaction
        raw_html(
            f'<div style="margin-top:10px; display:flex; gap:8px; align-items:center;">'
            f'<span class="badge sev-{alert.score.severity.value}">{alert.score.severity.value}</span>'
            f'<span class="badge status-{alert.status.value}">{alert.status.value}</span>'
            f'<span class="mono" style="color:var(--text-faint); font-size:12px;">score {alert.score.risk_score:.2f}</span>'
            f"</div>"
        )

        raw_html('<div class="drawer-section-label">Why it fired</div>')
        raw_html(f'<div class="alert-row-reasons">{reason_chips_html(alert.score.reasons)}</div>')

        raw_html('<div class="drawer-section-label">Transaction</div>')
        rows = [
            ("Transaction ID", t.id), ("Card token", t.card_token), ("User", t.user_id),
            ("Amount", fmt_money(t.amount, t.currency)), ("Merchant", t.merchant), ("MCC", t.mcc),
            ("Channel", t.channel.value), ("Country", t.country), ("Device", t.device_fp),
            ("Time", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t.ts))),
        ]
        raw_html("".join(
            f'<div class="drawer-kv"><span class="k">{escape(k)}</span><span class="v">{escape(str(v))}</span></div>'
            for k, v in rows
        ))

        similar = [it for it in state.recent_feed(card_token=t.card_token, limit=8) if it[0].id != t.id][:5]
        raw_html('<div class="drawer-section-label">Recent activity — same card</div>')
        if similar:
            raw_html("".join(
                f'<div class="similar-row"><span>{escape(st.merchant)} · {escape(st.country)}</span>'
                f'<span class="mono">{fmt_money(st.amount, st.currency)} · {time_ago(st.ts)}</span></div>'
                for st, sr in similar
            ))
        else:
            raw_html('<div class="similar-row">No other recent activity on this card.</div>')

        raw_html('<div class="drawer-section-label">Analyst note</div>')
        refs["note"] = ui.textarea(value=alert.note, placeholder="Optional note for the case log…") \
            .props("outlined dense").style("width:100%")

        raw_html('<div class="drawer-section-label">Actions</div>')
        with ui.element("div").style("display:flex; gap:8px; flex-wrap:wrap;"):
            style_btn(ui.button("Investigate", on_click=lambda: do_action(alert.id, AlertStatus.INVESTIGATING))
                      .props("unelevated"), "info")
            style_btn(ui.button("Freeze", on_click=lambda: do_action(alert.id, AlertStatus.FROZEN))
                      .props("unelevated"), "danger")
            style_btn(ui.button("Allow / Dismiss", on_click=lambda: do_action(alert.id, AlertStatus.DISMISSED))
                      .props("unelevated"), "ghost")

        if alert.history:
            raw_html('<div class="drawer-section-label">Case history</div>')
            raw_html("".join(
                f'<div class="similar-row"><span>{escape(h.text)}</span>'
                f'<span class="mono">{time_ago(h.ts)}</span></div>'
                for h in reversed(alert.history)
            ))

    @ui.refreshable
    def run_controls() -> None:
        btn = ui.button(
            "Stop Stream" if state.sim.running else "Start Stream",
            on_click=toggle_running,
        ).props("unelevated")
        style_btn(btn, "danger" if state.sim.running else "info")
        btn.style("width:100%")

    @ui.refreshable
    def nav_stats() -> None:
        raw_html(
            f'<div class="drawer-kv"><span class="k">Events</span><span class="v">{state.events_total:,}</span></div>'
            f'<div class="drawer-kv"><span class="k">Alerts</span><span class="v">{state.alerts_total:,}</span></div>'
            f'<div class="drawer-kv"><span class="k">Frozen</span><span class="v">{state.frozen_total:,}</span></div>'
        )

    # -- layout --------------------------------------------------------------
    with ui.element("div").classes("app-shell"):
        with ui.element("div").classes("side-nav"):
            raw_html('<div class="brand"><span class="brand-mark"></span>RiskPulse</div>')
            raw_html('<div class="page-subtitle">Real-time fraud operations</div>')

            raw_html('<div class="nav-section-label">Simulator</div>')
            with ui.element("div").classes("control-card"):
                run_controls()
                ui.slider(min=1, max=50, value=state.sim.base_rate, step=1, on_change=on_speed_change) \
                    .props("label label-always")
                raw_html('<div class="feed-sub">events / sec (baseline)</div>')

            raw_html('<div class="nav-section-label">Inject attack scenario</div>')
            with ui.element("div").classes("control-card"):
                for key, (label, _fn) in simulator.SCENARIOS.items():
                    b = ui.button(label, on_click=lambda e, k=key: inject(k)).props("unelevated")
                    style_btn(b, "ghost")
                    b.style("width:100%; justify-content:flex-start;")

            raw_html('<div class="nav-section-label">Policy</div>')
            with ui.element("div").classes("control-card"):
                ui.switch("Auto-freeze above threshold", value=state.policy.auto_freeze_enabled, on_change=on_policy_toggle)
                ui.number(
                    label="Threshold", value=state.policy.auto_freeze_threshold,
                    min=0.0, max=1.0, step=0.01, on_change=on_threshold_change,
                ).props("dense outlined")

            raw_html('<div class="nav-section-label">Session</div>')
            with ui.element("div").classes("control-card"):
                nav_stats()

        with ui.element("div").classes("main-canvas"):
            error_banner()
            with ui.element("div").classes("page-header"):
                with ui.element("div"):
                    raw_html('<div class="page-title">Live Risk Overview</div>')
                    raw_html('<div class="page-subtitle">Incoming transactions, scored on ingest, explained in plain language.</div>')
                with ui.element("div").style("display:flex; align-items:center; gap:12px;"):
                    live_pill()
                    ui.input(placeholder="Search transaction id, card token, merchant…", on_change=on_search_change) \
                        .props("dense outlined clearable").style("width:280px")

            kpi_strip()

            with ui.element("div").classes("main-columns"):
                with ui.element("div").classes("panel"):
                    with ui.element("div").classes("panel-header"):
                        ui.label("Live Feed").classes("panel-title")
                    with ui.element("div").classes("panel-body"):
                        feed_body()

                with ui.element("div").classes("panel"):
                    with ui.element("div").classes("panel-header"):
                        ui.label("Alerts").classes("panel-title")
                        with ui.element("div").style("display:flex; gap:8px; align-items:center; flex-wrap:wrap;"):
                            ui.select(
                                SEVERITY_OPTIONS, multiple=True, value=sorted(filters.severity),
                                label="Severity", on_change=on_severity_change,
                            ).props("dense outlined options-dense").style("width:190px")
                            ui.select(
                                {k: STATUS_LABELS[k] for k in STATUS_OPTIONS}, value=filters.status,
                                on_change=on_status_change,
                            ).props("dense outlined").style("width:150px")
                            style_btn(ui.button("Export CSV", on_click=export_csv).props("unelevated dense"), "ghost")
                    with ui.element("div").classes("panel-body"):
                        alerts_body()

    with ui.element("div").classes("detail-drawer").style("transform: translateX(105%); transition: transform .18s ease;") as drawer:
        drawer_body()

    ui.timer(0.35, lambda: (
        kpi_strip.refresh(), feed_body.refresh(), alerts_body.refresh(),
        error_banner.refresh(), live_pill.refresh(),
    ))
