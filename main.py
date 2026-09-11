"""Entry point: wires up the background simulation loop and starts NiceGUI.

Run with:  python main.py   (inside the .venv)
"""
from __future__ import annotations

import asyncio

from nicegui import app, ui

from app import simulator
from app.state import state
from app import ui_dashboard  # noqa: F401  (import registers the @ui.page('/') route)


async def _simulation_loop() -> None:
    """Single global tick loop — independent of how many browser tabs are
    connected, so opening a second dashboard tab never doubles the event rate."""
    while True:
        await asyncio.sleep(state.sim.tick_seconds)
        try:
            simulator.tick(state)
            state.stream_error = None
        except Exception as exc:  # keep the last known state, surface a banner
            state.stream_error = str(exc)


app.on_startup(_simulation_loop)

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="RiskPulse — Fraud Ops", dark=True, reload=False, port=8080, show=False)
