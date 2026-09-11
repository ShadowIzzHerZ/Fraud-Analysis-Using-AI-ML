# Prd

# Product Requirements Document

**Project:** Real-Time Anomaly Detection for Fraud Prevention

**Context:** 24–48 hour hackathon

**Goal:** Ship a demo that ingests a live transaction stream, flags anomalies in under a second, and lets an analyst act on them.

## Problem

Payment fraud is decided in milliseconds. Batch scoring after the fact is too late. Analysts also drown in false positives when every spike is treated as fraud.

This product shows a **live risk picture**: incoming transactions, scored immediately, with explainable reasons, so a human can freeze, allow, or escalate before the money leaves.

## What to build

A single web app with:

1. A **transaction firehose** (simulator that behaves like a payment gateway).
2. A **detection engine** that scores each event in real time (rules + statistical / ML anomaly score).
3. A **operations dashboard** for fraud analysts (live feed, alerts, case detail).
4. A thin **investigation workflow**: open a case, see why it fired, mark true/false positive.

Out of scope for the hackathon: production KYC, bank integrations, multi-tenant SaaS billing, model training pipelines, and mobile apps.

## Targeted users

| Persona | Role in demo | Needs |
| --- | --- | --- |
| **Fraud analyst** (primary) | Lives on the dashboard | Fast triage, clear reasons, freeze/allow |
| **Risk lead** | Watches metrics | Volume, catch rate, false-positive rate, $ at risk |
| **Hackathon judge** | 3-minute walkthrough | Visibly live data, a fake fraud burst, one investigation |

Secondary (do not build dedicated UIs unless time remains): merchant ops, cardholder support.

## Success criteria (demo)

- New transactions appear on the dashboard without a page refresh.
- A planted fraud burst (stolen-card pattern, velocity spike, or geo jump) is flagged within ~1s.
- Each alert shows **score, severity, and 2–4 human-readable reasons**.
- Analyst can freeze or dismiss an alert; the feed updates.
- One screen shows rolling KPIs (events/min, alerts, estimated $ blocked).

## Features

### Must have (P0)

- **Live transaction stream** with fields: id, timestamp, amount, currency, merchant, MCC, channel (card-present / online), country, device/ip fingerprint (simulated), user/card token.
- **Scoring on ingest**: combine a rules engine and an anomaly model (or robust statistical baseline if ML is too heavy).
- **Alert list** filtered by severity (critical / high / medium) and status (new / investigating / frozen / dismissed).
- **Transaction + alert detail**: raw event, feature contributions, similar recent events for the same card/user.
- **Analyst actions**: Investigate, Freeze, Allow/Dismiss, with an optional short note.
- **Simulator controls**: start/stop stream, speed, inject attack scenario (velocity, amount outlier, impossible travel, mule burst).

### Should have (P1)

- Risk KPI strip: throughput, open alerts, freeze count, $ at risk in last 15 minutes.
- Simple allow/block **policy toggle** (e.g. auto-freeze above score 0.9).
- Search by transaction id, card token, merchant.
- Alert reason chips that map 1:1 to detectors (not a black-box “model said so”).

### Nice to have (P2)

- Replay a saved session for judges if the live stream glitches.
- Lightweight “case” grouping (multiple alerts on one card).
- Export a CSV of the last N alerts.
- Dark/light theme (dark is default; see `design.md`).

## Non-functional requirements

- **Latency:** score + push to UI in under 1 second on a laptop for ~20–50 events/sec.
- **Explainability:** every alert must cite detectors, not only a numeric score.
- **Resilience:** stream or model failure must not crash the UI; show a banner and keep last known state.
- **Demo safety:** no real card numbers; use tokens. No production secrets in the repo.

## Explicitly not this hackathon

- Real PCI-DSS card data or production payment APIs.
- Training a custom deep model from scratch.
- Kafka / Kubernetes / multi-region unless already set up and needed.
- Full RBAC, SSO, or audit-log compliance products.

## Open questions (defaults if unanswered)

- Default currency: USD; amounts may still vary by merchant country.
- Default auto-freeze threshold: 0.90.
- Default stream rate: 15 events/sec, burst to 40 during attack injection.