package com.zenpay.app

import android.content.Context

private const val PREFS = "zenpay_session"
private const val KEY_ACCESS_TOKEN = "access_token"
private const val KEY_REFRESH_TOKEN = "refresh_token"
private const val KEY_USER_ID = "user_id"
private const val KEY_EMAIL = "email"
private const val KEY_DISPLAY_NAME = "display_name"
private const val KEY_PENDING_PKCE_VERIFIER = "pending_pkce_verifier"

/** Where a signed-in Google session lives — analogous to app.storage.user's
 * SESSION_KEY on the web app (app/auth_ui.py), just SharedPreferences here
 * since there's no server-side session to mirror. */
object SessionStore {
    private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun isSignedIn(context: Context): Boolean = prefs(context).contains(KEY_ACCESS_TOKEN)

    fun save(context: Context, result: AuthClient.AuthResult) {
        prefs(context).edit()
            .putString(KEY_ACCESS_TOKEN, result.accessToken)
            .putString(KEY_REFRESH_TOKEN, result.refreshToken)
            .putString(KEY_USER_ID, result.userId)
            .putString(KEY_EMAIL, result.email)
            .putString(KEY_DISPLAY_NAME, result.displayName)
            .apply()
    }

    fun email(context: Context): String = prefs(context).getString(KEY_EMAIL, "") ?: ""
    fun displayName(context: Context): String = prefs(context).getString(KEY_DISPLAY_NAME, "") ?: ""

    fun signOut(context: Context) {
        prefs(context).edit()
            .remove(KEY_ACCESS_TOKEN).remove(KEY_REFRESH_TOKEN)
            .remove(KEY_USER_ID).remove(KEY_EMAIL).remove(KEY_DISPLAY_NAME)
            .apply()
    }

    /** Carries the PKCE verifier across the trip out to the browser and
     * back — an in-memory field wouldn't reliably survive that round-trip
     * if the OS reclaims the process while the browser's in front. */
    fun stashPkceVerifier(context: Context, verifier: String) {
        prefs(context).edit().putString(KEY_PENDING_PKCE_VERIFIER, verifier).apply()
    }

    fun takePkceVerifier(context: Context): String? {
        val p = prefs(context)
        val v = p.getString(KEY_PENDING_PKCE_VERIFIER, null)
        p.edit().remove(KEY_PENDING_PKCE_VERIFIER).apply()
        return v
    }
}
