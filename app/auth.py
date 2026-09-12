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
from urllib.parse import urlencode

from supabase import Client, create_client
from supabase_auth.helpers import generate_pkce_challenge, generate_pkce_verifier

SUPABASE_URL = "https://mpduaztlanucevfbpaip.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_rDXMQ1jB-V2RGPhcWqPbEg_dIpxKZBl"

SESSION_KEY = "zen_session"

# Where Google sends the browser back to after consent. Must be added to
# this Supabase project's Authentication > URL Configuration > Redirect
# URLs allow-list, or the exchange below fails with "requested path is
# invalid" even though everything else is configured correctly.
OAUTH_CALLBACK_PATH = "/auth/callback"


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


@dataclass
class OAuthStart:
    url: str
    code_verifier: str


def start_google_oauth(redirect_to: str) -> OAuthStart:
    """Build the Google consent-screen URL for the PKCE flow.

    Built by hand (not via `client.auth.sign_in_with_oauth`) because that
    call stashes its generated `code_verifier` in the client's own
    in-memory storage — fine for a long-lived browser SDK, useless here
    since this whole client is thrown away right after this function
    returns and a *different* one handles the callback once Google's
    redirect lands, seconds to minutes later. `generate_pkce_verifier` /
    `_challenge` are the same public helpers that call uses internally;
    the caller here is on the hook for carrying `code_verifier` across
    that gap themselves (the auth UI puts it in `app.storage.user`).
    """
    verifier = generate_pkce_verifier()
    challenge = generate_pkce_challenge(verifier)
    params = {
        "provider": "google",
        "redirect_to": redirect_to,
        "code_challenge": challenge,
        "code_challenge_method": "s256",
    }
    url = f"{SUPABASE_URL}/auth/v1/authorize?{urlencode(params)}"
    return OAuthStart(url=url, code_verifier=verifier)


def complete_oauth(auth_code: str, code_verifier: str) -> AuthResult:
    client = _client()
    try:
        res = client.auth.exchange_code_for_session({
            "auth_code": auth_code,
            "code_verifier": code_verifier,
        })
    except Exception as exc:
        raise AuthError(_friendly(exc)) from exc

    user = res.user
    meta = (user.user_metadata or {}) if user else {}
    display_name = (
        meta.get("display_name") or meta.get("full_name") or meta.get("name")
        or (user.email or "").split("@")[0] or "Analyst"
    )
    return AuthResult(
        access_token=res.session.access_token,
        refresh_token=res.session.refresh_token,
        user_id=user.id,
        email=user.email or "",
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
