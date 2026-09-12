"""Entry point: wires up the background simulation loop and starts NiceGUI.

Run with:  python main.py   (inside the .venv)
"""
from __future__ import annotations

import asyncio

from nicegui import app, ui

from app import simulator
from app.state import state
from app import ui_dashboard  # noqa: F401  (import registers the @ui.page('/') route)
from app import auth_ui  # noqa: F401  (registers @ui.page('/login') and '/signup')
from app import portal  # noqa: F401  (registers the POST /api/portal/pay endpoint for the Android app)


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
    # dark=False: the UI is the light "Warm Civic Minimal" theme, not the
    # earlier dark-ops design — dark=True left every native Quasar input
    # (search box, Channel select, Auto-Freeze threshold) rendering white
    # text on our light surfaces, i.e. invisible.
    #
    # storage_secret enables app.storage.user (a signed, per-browser cookie
    # store) — that's where the Supabase session lives between page loads.
    # Hardcoded here since this is a single-process hackathon demo with no
    # env-var plumbing yet; rotate/move to an env var before any real deploy.
    ui.run(
        title="Zen — Fraud Ops", dark=False, reload=False, port=8080, show=False,
        storage_secret="zen-demo-storage-secret-change-before-deploying",
    )
