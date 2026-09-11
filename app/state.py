"""In-memory application state.

Everything here lives in one process / one asyncio event loop (NiceGUI's),
so a plain module-level singleton with no locks is safe — there is exactly
one writer (the simulator tick) and readers only ever run between awaits.

This intentionally is not a database: it's a hackathon demo of a live
pipeline, and the PRD explicitly scopes out persistence.
"""
from __future__ import annotations

import csv
import io
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from app.models import Alert, AlertStatus, OPEN_STATUSES, ScoreResult, Transaction

KPI_WINDOW_SECONDS = 15 * 60
THROUGHPUT_WINDOW_SECONDS = 60
MAX_TRANSACTIONS = 500
MAX_ALERTS = 300


@dataclass
class CardProfile:
    """Rolling behavioural baseline for one card token, updated on every txn."""

    card_token: str
    n: int = 0
    mean_amount: float = 0.0
    m2: float = 0.0  # Welford's running sum of squared deviations (raw $ — for display only)
    mean_log: float = 0.0
    m2_log: float = 0.0  # Welford in log-space — amounts are right-skewed, so this is what scoring uses
    seen_devices: set[str] = field(default_factory=set)
    seen_mccs: set[str] = field(default_factory=set)
    last_country: Optional[str] = None
    last_ts: Optional[float] = None
    recent_txn_times: deque[float] = field(default_factory=lambda: deque(maxlen=50))
    # (ts, merchant, amount) — used for velocity + mule-burst detectors
    recent_events: deque[tuple[float, str, float]] = field(default_factory=lambda: deque(maxlen=50))

    @property
    def std_amount(self) -> float:
        if self.n < 2:
            return 0.0
        return (self.m2 / (self.n - 1)) ** 0.5

    @property
    def std_log(self) -> float:
        if self.n < 2:
            return 0.0
        return (self.m2_log / (self.n - 1)) ** 0.5

    def amount_zscore(self, amount: float) -> float:
        """Z-score in log-space: robust to the natural right-skew of transaction
        amounts (a card that mixes $15 coffees with $900 hotel stays shouldn't
        look "anomalous" on every coffee)."""
        if self.n < 5 or self.std_log < 1e-6:
            return 0.0
        import math
        return (math.log(max(amount, 0.01)) - self.mean_log) / self.std_log

    def observe(self, txn: Transaction) -> None:
        """Update rolling stats. Must be called AFTER scoring reads the profile,
        so the profile scoring sees reflects history strictly before this event."""
        import math
        self.n += 1
        delta = txn.amount - self.mean_amount
        self.mean_amount += delta / self.n
        delta2 = txn.amount - self.mean_amount
        self.m2 += delta * delta2

        log_amt = math.log(max(txn.amount, 0.01))
        delta_l = log_amt - self.mean_log
        self.mean_log += delta_l / self.n
        delta2_l = log_amt - self.mean_log
        self.m2_log += delta_l * delta2_l
        self.seen_devices.add(txn.device_fp)
        self.seen_mccs.add(txn.mcc)
        self.last_country = txn.country
        self.last_ts = txn.ts
        self.recent_txn_times.append(txn.ts)
        self.recent_events.append((txn.ts, txn.merchant, txn.amount))


@dataclass
class Policy:
    auto_freeze_enabled: bool = True
    auto_freeze_threshold: float = 0.90


@dataclass
class SimulatorControls:
    running: bool = False
    base_rate: float = 15.0  # events/sec, normal traffic
    burst_rate: float = 40.0  # events/sec, during an injected attack
    burst_until: float = 0.0  # timestamp; while now < this, use burst_rate
    tick_seconds: float = 0.2


class AppState:
    def __init__(self) -> None:
        # every scored event, newest last — the "live feed" (score kept alongside
        # so the UI never has to recompute or guess a risk value for display)
        self.feed: deque[tuple[Transaction, ScoreResult]] = deque(maxlen=MAX_TRANSACTIONS)
        self.alerts: dict[str, Alert] = {}
        self.alert_order: list[str] = []  # most-recent-first alert ids

        self.card_profiles: dict[str, CardProfile] = {}

        self.policy = Policy()
        self.sim = SimulatorControls()

        # scenario bursts are pre-generated and queued with a target emit time
        self.pending_events: list[tuple[float, Transaction]] = []

        self.events_total = 0
        self.alerts_total = 0
        self.frozen_total = 0
        self.started_at = time.time()
        self.stream_error: Optional[str] = None

        # bump on every mutation so the UI can cheaply decide whether to redraw
        self.version = 0

    # -- profiles ---------------------------------------------------------
    def profile_for(self, card_token: str) -> CardProfile:
        prof = self.card_profiles.get(card_token)
        if prof is None:
            prof = CardProfile(card_token=card_token)
            self.card_profiles[card_token] = prof
        return prof

    # -- ingest -------------------------------------------------------------
    def add_transaction(self, txn: Transaction, result: ScoreResult) -> None:
        self.feed.append((txn, result))
        self.events_total += 1
        self.version += 1

    def add_alert(self, alert: Alert) -> None:
        self.alerts[alert.id] = alert
        self.alert_order.insert(0, alert.id)
        if len(self.alert_order) > MAX_ALERTS:
            stale = self.alert_order[MAX_ALERTS:]
            self.alert_order = self.alert_order[:MAX_ALERTS]
            for aid in stale:
                self.alerts.pop(aid, None)
        self.alerts_total += 1
        self.version += 1

    def set_alert_status(self, alert_id: str, status: AlertStatus, note: Optional[str] = None) -> Optional[Alert]:
        alert = self.alerts.get(alert_id)
        if alert is None:
            return None
        old = alert.status
        alert.status = status
        if note is not None:
            alert.note = note
        alert.log(f"{old.value} → {status.value}")
        if status == AlertStatus.FROZEN:
            self.frozen_total += 1
        self.version += 1
        return alert

    # -- derived / KPIs -------------------------------------------------------------
    def recent_feed(self, card_token: Optional[str] = None, limit: Optional[int] = None) -> list[tuple[Transaction, ScoreResult]]:
        items = list(self.feed)
        items.reverse()  # newest first
        if card_token is not None:
            items = [item for item in items if item[0].card_token == card_token]
        if limit is not None:
            items = items[:limit]
        return items

    def recent_transactions(self, seconds: float, now: Optional[float] = None) -> list[Transaction]:
        now = now if now is not None else time.time()
        cutoff = now - seconds
        return [t for t, _ in self.feed if t.ts >= cutoff]

    def recent_alerts(self, seconds: float, now: Optional[float] = None) -> list[Alert]:
        now = now if now is not None else time.time()
        cutoff = now - seconds
        out = []
        for aid in self.alert_order:
            a = self.alerts.get(aid)
            if a and a.created_at >= cutoff:
                out.append(a)
        return out

    def kpis(self, now: Optional[float] = None) -> dict:
        now = now if now is not None else time.time()
        recent_txns = self.recent_transactions(THROUGHPUT_WINDOW_SECONDS, now)
        window_alerts = self.recent_alerts(KPI_WINDOW_SECONDS, now)
        open_alerts = [a for a in window_alerts if a.status in OPEN_STATUSES]
        frozen = [a for a in window_alerts if a.status == AlertStatus.FROZEN]
        at_risk = [a for a in window_alerts if a.status != AlertStatus.DISMISSED]
        dollars_at_risk = sum(a.transaction.amount for a in at_risk)
        return {
            "events_per_min": len(recent_txns) * (60.0 / THROUGHPUT_WINDOW_SECONDS),
            "open_alerts": len(open_alerts),
            "frozen_count": len(frozen),
            "dollars_at_risk": dollars_at_risk,
        }

    # -- export -------------------------------------------------------------
    def alerts_csv(self, limit: int = 200) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "alert_id", "created_at", "status", "severity", "risk_score",
            "transaction_id", "card_token", "amount", "currency", "merchant",
            "mcc", "country", "channel", "reasons", "note",
        ])
        for aid in self.alert_order[:limit]:
            a = self.alerts[aid]
            t = a.transaction
            writer.writerow([
                a.id,
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(a.created_at)),
                a.status.value,
                a.score.severity.value,
                f"{a.score.risk_score:.3f}",
                t.id, t.card_token, f"{t.amount:.2f}", t.currency, t.merchant,
                t.mcc, t.country, t.channel.value,
                "; ".join(r.text for r in a.score.reasons),
                a.note,
            ])
        return buf.getvalue()


state = AppState()
