"""Core data model for the fraud-detection demo.

Plain dataclasses (not pydantic) — this data never crosses a network boundary
as JSON, it just lives in the in-process AppState, so dataclasses keep things
fast and dependency-light. Pydantic is still used at the edges (CSV export
payloads, future API responses) where validation earns its keep.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


SEVERITY_ORDER = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]


class AlertStatus(str, Enum):
    NEW = "new"
    INVESTIGATING = "investigating"
    FROZEN = "frozen"
    DISMISSED = "dismissed"


OPEN_STATUSES = {AlertStatus.NEW, AlertStatus.INVESTIGATING}


class Channel(str, Enum):
    CARD_PRESENT = "card_present"
    ONLINE = "online"


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


@dataclass
class Transaction:
    id: str
    ts: float
    amount: float
    currency: str
    merchant: str
    mcc: str
    channel: Channel
    country: str
    device_fp: str
    card_token: str
    user_id: str
    scenario: Optional[str] = None  # which injected attack pattern produced this, if any


@dataclass
class Reason:
    detector: str  # short code, e.g. "VELOCITY" — maps 1:1 to a detector, never "model said so"
    text: str  # human-readable explanation


@dataclass
class ScoreResult:
    risk_score: float  # 0..1
    severity: Severity
    reasons: list[Reason] = field(default_factory=list)
    contributions: dict[str, float] = field(default_factory=dict)  # detector -> weight


@dataclass
class HistoryEntry:
    ts: float
    text: str


@dataclass
class Alert:
    id: str
    transaction: Transaction
    score: ScoreResult
    status: AlertStatus = AlertStatus.NEW
    created_at: float = field(default_factory=time.time)
    note: str = ""
    history: list[HistoryEntry] = field(default_factory=list)

    def log(self, text: str) -> None:
        self.history.append(HistoryEntry(ts=time.time(), text=text))
