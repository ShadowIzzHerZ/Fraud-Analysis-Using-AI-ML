# RiskPulse — Real-Time Anomaly Detection for Fraud Prevention

A hackathon demo (per [`docs/PRD.md`](docs/PRD.md)) that ingests a simulated live
transaction stream, scores every event on ingest with an explainable rules +
statistical engine, and gives a fraud analyst a dark "ops" dashboard
([`docs/design.md`](docs/design.md)) to triage and act on what fires.

Stack is deliberately all-Python — FastAPI + [NiceGUI](https://nicegui.io) (which
NiceGUI is built on FastAPI + Vue) for a real-time, WebSocket-driven UI with no
separate frontend build step. No database: everything lives in an in-memory
`AppState` singleton for the life of the process, per the PRD's scope.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Then open **http://localhost:8080**. Click **Start Stream** in the left rail to
begin the simulated transaction firehose.

## How it's organized

- [`app/models.py`](app/models.py) — `Transaction`, `Alert`, `ScoreResult`, etc.
- [`app/geo.py`](app/geo.py) — country centroids + haversine distance, for the impossible-travel detector.
- [`app/state.py`](app/state.py) — the in-memory `AppState` singleton: the live feed, alerts, per-card rolling behavioural profiles (Welford mean/std in log-space), policy, simulator controls, KPIs, CSV export.
- [`app/simulator.py`](app/simulator.py) — the transaction firehose: a population of 1,000 synthetic cards generating plausible baseline traffic, plus four attack-injection scenarios (velocity spike, amount outlier, impossible travel, mule burst).
- [`app/scoring.py`](app/scoring.py) — the detection engine: six named detectors (`AMOUNT`, `VELOCITY`, `GEO_JUMP`, `NEW_DEVICE`, `MULE_BURST`, `UNUSUAL_MCC`), each producing a human-readable reason. Weights are additive and capped at 1.0 — no black-box model, every alert cites its detectors.
- [`app/ui_dashboard.py`](app/ui_dashboard.py) — the NiceGUI page: KPI strip, live feed, alerts list with severity/status filters, an investigation drawer (transaction detail, reasons, similar recent activity, note, Investigate/Freeze/Allow-Dismiss actions), simulator + policy controls, CSV export.
- [`app/static/theme.css`](app/static/theme.css) — the dark-ops design system from `docs/design.md`, implemented as plain CSS custom properties.
- `main.py` — wires up a single background asyncio loop that ticks the simulator independent of how many browser tabs are open, then starts NiceGUI.

## What's implemented vs. the PRD

**P0 (must have):** live transaction stream with all specified fields, rules +
statistical scoring on ingest, severity/status-filterable alert list,
transaction/alert detail with reasons and similar recent card activity,
analyst actions (Investigate/Freeze/Allow-Dismiss + note), simulator controls
(start/stop, speed, inject each of the four attack scenarios).

**P1 (should have):** KPI strip (throughput, open alerts, freeze count, $ at
risk in the last 15 min), auto-freeze policy toggle + threshold, search by
transaction id / card token / merchant, reason chips mapped 1:1 to detectors.

**P2 (nice to have):** CSV export of alerts is implemented. Session replay and
case grouping (multiple alerts on one card) are **not** implemented — out of
scope for this pass; the "Recent activity — same card" panel in the
investigation drawer covers the most common reason an analyst would want that
(spotting a pattern across the same card) without full case objects.

## Notes on the detection engine

Amounts are scored against each card's own history in **log-space** (not raw
dollars) — transaction amounts are naturally right-skewed (a card mixing $15
coffees with $900 hotel stays isn't "anomalous" on every coffee), and a plain
z-score over raw amounts produced a noticeably noisier baseline in testing.
Calibrated against a 1,000-card population at the PRD's default 15 events/sec:
baseline (no injected attack) false-positive rate is well under 1%, and all
four attack scenarios reliably cross the alert threshold within their burst
window.
