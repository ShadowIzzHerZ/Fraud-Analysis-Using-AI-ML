package com.zenpay.app

import android.content.Context

private const val PREFS = "zenpay_prefs"
private const val KEY_SYNC_ENABLED = "sync_enabled"
private const val KEY_SYNC_URL = "sync_url"

// 127.0.0.1:8080 is reached over USB via `adb reverse tcp:8080 tcp:8080` (run
// once per device) — the most reliable path for two phones on a laptop's
// desk, no Wi-Fi/tunnel dependency. This used to default to a Cloudflare
// "quick tunnel" URL, but those are single-use and die the moment the
// `cloudflared` process that created them exits, which is exactly what made
// every sync silently fail (LocalWallet still worked, nothing ever reached
// the analyst console). A LAN IP (e.g. http://10.0.0.5:8080) also works and
// is the better choice once both devices are actually off USB.
const val DEFAULT_SYNC_URL = "http://127.0.0.1:8080"

/** Shared reader/writer for the "sync to analyst console" setting (Settings
 * screen in MainActivity) — SendMoneyActivity needs the same values to
 * decide whether to mirror a P2P transfer, so this lives in one place
 * instead of two copies of the SharedPreferences keys drifting apart. */
object SyncSettings {
    private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun isEnabled(context: Context): Boolean = prefs(context).getBoolean(KEY_SYNC_ENABLED, true)
    fun url(context: Context): String {
        val saved = prefs(context).getString(KEY_SYNC_URL, null)
        if (saved.isNullOrBlank()) return DEFAULT_SYNC_URL
        return saved
    }

    fun setEnabled(context: Context, enabled: Boolean) = prefs(context).edit().putBoolean(KEY_SYNC_ENABLED, enabled).apply()
    fun setUrl(context: Context, url: String) = prefs(context).edit().putString(KEY_SYNC_URL, url).apply()
}
