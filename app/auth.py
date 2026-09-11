"""Analyst authentication, backed by Supabase Auth.

Zen shares its Supabase project (and therefore its `auth.users` pool) with
another app on the same account. To keep the two cleanly separated, every
signup from here passes `app: "zen"` in the auth metadata, and a DB trigger
on the project routes those into `public.zen_analysts` instead of that
other app's own profile table — see the migration `add_zen_analysts_table`.
Nothing here ever touches that other table.

Session state lives in NiceGUI's per-browser `app.storage.user` (a signed
cookie-backed store — see `storage_secret` in main.py), keyed under
`SESSION_KEY`. This module only wraps the Supabase calls; storing/reading
`app.storage.user` is left to the caller (the auth UI) so this stays
testable without a NiceGUI request context.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from supabase import Client, create_client

SUPABASE_URL = "https://mpduaztlanucevfbpaip.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_rDXMQ1jB-V2RGPhcWqPbEg_dIpxKZBl"

SESSION_KEY = "zen_session"


def _client() -> Client:
    # A fresh client per call avoids sharing mutable auth state across
    # concurrent NiceGUI browser sessions (this module is imported once,
    # process-wide, but each login/signup is a separate visitor).
    return create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)


@dataclass
class AuthResult:
    access_token: str
    refresh_token: str
    user_id: str
    email: str
    display_name: str


class AuthError(Exception):
    """Raised with a message that's safe (and useful) to show an analyst."""


def _friendly(err: Exception) -> str:
    msg = str(err)
    low = msg.lower()
    if "invalid login credentials" in low:
        return "Incorrect email or password."
    if "already registered" in low or "already exists" in low or "user_already_exists" in low:
        return "That email is already registered — try logging in instead."
    if "password should be at least" in low or "password" in low and "6" in low:
        return "Password must be at least 6 characters."
    if "invalid email" in low:
        return "That doesn't look like a valid email address."
    if "rate limit" in low:
        return "Too many attempts — wait a moment and try again."
    return "Something went wrong. Please try again."


def sign_up(email: str, password: str, display_name: str) -> AuthResult:
    client = _client()
    try:
        res = client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"app": "zen", "display_name": display_name or None}},
        })
    except Exception as exc:  # supabase raises AuthApiError subclasses
        raise AuthError(_friendly(exc)) from exc

    if res.session is None or res.user is None:
        # Email confirmation is required on this project — no session yet.
        raise AuthError(
            "Account created — check your email to confirm it, then log in."
        )
    return AuthResult(
        access_token=res.session.access_token,
        refresh_token=res.session.refresh_token,
        user_id=res.user.id,
        email=res.user.email or email,
        display_name=display_name or (res.user.email or email).split("@")[0],
    )


def sign_in(email: str, password: str) -> AuthResult:
    client = _client()
    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as exc:
        raise AuthError(_friendly(exc)) from exc

    user = res.user
    meta = (user.user_metadata or {}) if user else {}
    display_name = meta.get("display_name") or (user.email or email).split("@")[0]
    return AuthResult(
        access_token=res.session.access_token,
        refresh_token=res.session.refresh_token,
        user_id=user.id,
        email=user.email or email,
        display_name=display_name,
    )


def sign_out(access_token: Optional[str]) -> None:
    if not access_token:
        return
    client = _client()
    try:
        client.auth.sign_out()
    except Exception:
        pass  # best-effort — the local session is cleared regardless
