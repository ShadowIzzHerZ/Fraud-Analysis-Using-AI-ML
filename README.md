# Zen — Real-Time Anomaly Detection for Fraud Prevention

A hackathon demo (originally named "RiskPulse" in [`docs/PRD.md`](docs/PRD.md),
now shipped as **Zen**) that ingests a simulated live
transaction stream, scores every event on ingest with an explainable rules +
statistical engine, and gives a fraud analyst an ops console to triage and act
on what fires. The UI follows a "Warm Civic Minimal" visual system generated
with Google Stitch ([`docs/stitch/DESIGN.md`](docs/stitch/DESIGN.md),
[`docs/stitch/reference.html`](docs/stitch/reference.html) — the original
static mockup, wired here to the real backend instead of its fake JS data);
an earlier dark-ops variant is documented in [`docs/design.md`](docs/design.md).

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
- [`app/geo.py`](app/geo.py) — Indian city centroids + haversine distance, for the impossible-travel detector.
- [`app/state.py`](app/state.py) — the in-memory `AppState` singleton: the live feed, alerts, per-card rolling behavioural profiles (Welford mean/std in log-space), policy, simulator controls, KPIs, CSV export.
- [`app/simulator.py`](app/simulator.py) — the transaction firehose: a population of 1,000 synthetic cards generating plausible baseline traffic, plus four attack-injection scenarios (velocity spike, amount outlier, impossible travel, mule burst).
- [`app/scoring.py`](app/scoring.py) — the detection engine: six named detectors (`AMOUNT`, `VELOCITY`, `GEO_JUMP`, `NEW_DEVICE`, `MULE_BURST`, `UNUSUAL_MCC`), each producing a human-readable reason. Weights are additive and capped at 1.0 — no black-box model, every alert cites its detectors.
- [`app/ui_dashboard.py`](app/ui_dashboard.py) — the NiceGUI page: top bar with live/processed/alert counters, a left rail, a KPI strip (with a real sparkline and a rule-engine-load gauge), a live feed + alerts queue split view, an investigation ("Case Dossier") drawer, simulator/policy controls, Simulate Hiccup, Emergency Freeze, CSV export. Styled with Tailwind utility classes (NiceGUI bundles the Tailwind Play CDN) using arbitrary-value colors (`bg-[#hex]`) from the Stitch palette rather than a `tailwind.config` extension, since NiceGUI's bundled runtime doesn't generate responsive-prefix (`sm:`/`md:`/`lg:`) media queries — this is a fixed desktop layout by design, not a bug.
- [`app/static/theme.css`](app/static/theme.css) — the handful of things Tailwind utility classes can't cover: font-loading glue, the Material Symbols icon font sizing, scrollbars, and the new-row/new-alert flash keyframes.
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
scope for this pass; the "Card Recent Velocity Baseline" panel in the
investigation drawer covers the most common reason an analyst would want that
(spotting a pattern across the same card) without full case objects.

**Added beyond the PRD** (from the Stitch mockup's own feature set, wired to
the real backend): an **Emergency Freeze** button that immediately freezes
every open alert at or above a score of 0.80, independent of the configured
auto-freeze threshold; a **Simulate Hiccup** toggle that demos the "stream
degrades without crashing the UI" resilience requirement on demand; and IP +
geolocation fields on every transaction, shown in the investigation drawer.
Clicking a plain feed row (one that never crossed the alert threshold) opens
the same drawer read-only-ish — taking an action on it promotes it into a
real, tracked alert on the spot.

**Multi-screen navigation**: the top bar (Console/Simulation/Policies/Audit
Logs) and left rail (Live Stream/Alerts Queue/Investigation/Policy Rules/
Telemetry) both switch a shared `filters.view` in `app/ui_dashboard.py` — every
nav button actually navigates, with the active one highlighted in both bars.
Console is the original KPI+feed+alerts dashboard; the other six are
full-width screens built from the same underlying data (a full-page Alerts
Queue, an Investigation queue of in-review/resolved cases, a Policy Rules
reference table of all six detectors with their max weights, a Telemetry
screen with a bigger throughput chart and all-time severity/detector
breakdowns, a Simulation screen with a log of recent injections, and an Audit
Logs screen aggregating every alert's enforcement history). Clicking an
"Inject Attack" button now stays visibly pressed/checked (and logs itself to
the Simulation screen's injection log) so it's clear which scenario was just
fired. `main`'s overflow changed from clipped to scrollable, so a screen with
more content than fits (or a short browser window) scrolls instead of losing
content off the bottom.

**Locale**: the whole simulation — vendors, cities, currency — is India/INR.
Merchant names are fictional but India-flavored (e.g. "Sabzi Mandi Grocers",
"Garuda Airways"); the 16 simulated "countries" are Indian cities (Mumbai,
Delhi, Bengaluru, ...) so the impossible-travel detector still has real
geographic spread to work with; every amount renders through `fmt_inr()`,
which does Indian digit grouping (lakh/crore: ₹12,34,567) rather than Western
thousands-grouping. Category price ranges and the few absolute-₹ detector
thresholds (the amount-outlier cold-start fallback, the new-device amount
gate, the mule-burst average-ticket cap) were rescaled to realistic Indian
price levels — the log-space z-score itself is scale-invariant, so it didn't
need retuning, but the flat thresholds did.

**Auth**: [`app/auth.py`](app/auth.py) and [`app/auth_ui.py`](app/auth_ui.py)
add real analyst accounts via [Supabase Auth](https://supabase.com/docs/guides/auth)
(email + password) — `/login` and `/signup` gate `/`, and the header's avatar
shows the signed-in analyst's initials with a logout action. Zen shares its
Supabase project's `auth.users` pool with another app on the same account, so
every Zen signup carries an `app: "zen"` flag in its auth metadata; a DB
trigger on that project (see migration `add_zen_analysts_table`) routes
those into their own `public.zen_analysts` table instead of that other app's
profile table, so the two never cross-contaminate. Session tokens live in
NiceGUI's `app.storage.user` (`storage_secret` in `main.py` — currently a
hardcoded demo value; move it to an env var before any real deploy).

**Ambient anomalies**: by default, a plain run of the stream — nobody
touching the Inject Attack buttons — still produces some alerts on its own.
`state.sim.ambient_fraud_pct` (Simulation screen: the "Bad txns" −/+
stepper, 0–25%, default 4%) is the % chance each ambient transaction is
`simulator.generate_ambient_anomaly()` instead of a plain normal one. It
prefers a same-tick country flip on a card that just transacted (GEO_JUMP,
weight 0.50, needs only one prior event on that card — the only signal that
can reliably alert on a single isolated transaction before any card has
enough history for the others) and falls back to an elevated amount on an
unrecognized device (AMOUNT + NEW_DEVICE stacked) once cards are seasoned
enough for that combo to clear the 0.40 alert floor on its own.

## Notes on the layout

The three-column shell (rail / main / investigation drawer) is a `flex` row
inside a `flex-col` page. Every flex item in that chain needs an explicit
`min-h-0` (or it silently grows to its content's natural height instead of
respecting `flex: 1` / `overflow: hidden`) — the classic nested-flexbox
`min-height: auto` trap. If a future change to the drawer or rail makes
content spill past the viewport again, check for a missing `min-h-0` before
anything else.

The header is a second flexbox gotcha, of a different kind: `flex-wrap`
isn't inherited, and a `flex-nowrap` on an ancestor only stops *that*
container's own direct children from wrapping — it says nothing about
whether a nested flex container wraps its own. The header's left group
(logo + nav) and right group (counters + actions) are each their own
nested flex row; neither originally set its own `flex-nowrap`, so once its
content stopped fitting, the left group silently wrapped the nav onto a
second line *inside itself* — invisibly, no visible seam — and that second
line got cut off against the header's fixed `h-16`. This is what was
clipping the active top-nav pill off at the bottom. Every flex container in
the header now sets `flex-nowrap` explicitly instead of relying on an
ancestor's. (`header` itself also splits scrolling and centering across
two inner divs rather than doing both on one element — not the cause of
this particular bug, but a container that's simultaneously the thing
centering an overflowing child *and* the thing scrolling it is a real,
separately-known source of inconsistent sizing, so it's cheap insurance
to keep them apart regardless.)

## Notes on the detection engine

Amounts are scored against each card's own history in **log-space** (not raw
dollars) — transaction amounts are naturally right-skewed (a card mixing $15
coffees with $900 hotel stays isn't "anomalous" on every coffee), and a plain
z-score over raw amounts produced a noticeably noisier baseline in testing.
Calibrated against a 1,000-card population at the PRD's default 15 events/sec:
baseline (no injected attack) false-positive rate is well under 1%, and all
four attack scenarios reliably cross the alert threshold within their burst
window.
