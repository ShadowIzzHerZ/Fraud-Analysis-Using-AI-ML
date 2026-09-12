package com.zenpay.app

import android.content.Context

private const val PREFS = "zenpay_prefs"
private const val KEY_SYNC_ENABLED = "sync_enabled"
private const val KEY_SYNC_URL = "sync_url"

// Points at the backend permanently deployed on an EC2 instance in
// ap-south-1 (see scripts/ — it's not a Cloudflare quick tunnel or a
// `adb reverse` loopback anymore, both of which die the moment the process
// that created them exits, which is exactly what made every sync silently
// fail before: LocalWallet still worked, nothing ever reached the analyst
// console). This URL is stable — a real EC2 instance with an Elastic IP,
// running the backend under systemd (auto-restarts on crash and reboot) —
// so both devices reach the same backend over plain internet, no USB/LAN
// dependency at all. Override in Settings if you're pointing at a
// different backend (e.g. 127.0.0.1 over `adb reverse` for local dev).
const val DEFAULT_SYNC_URL = "http://13.207.109.247:8080"

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
