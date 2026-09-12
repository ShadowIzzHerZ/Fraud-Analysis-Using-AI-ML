package com.zenpay.app

import android.content.Context
import org.json.JSONObject

/**
 * Persists one CardProfile per (locally hashed) test-card token, so a
 * card's behavioural baseline survives across app launches — the same way
 * the Python backend keeps per-card profiles in memory for the lifetime of
 * its process (app/state.py), except this one lives in SharedPreferences
 * since the whole point of LocalPortal is not needing that process at all.
 */
class ProfileStore(context: Context) {
    private val prefs = context.getSharedPreferences("zenpay_profiles", Context.MODE_PRIVATE)

    fun load(cardToken: String): CardProfile {
        val raw = prefs.getString(cardToken, null) ?: return CardProfile()
        return try {
            CardProfile.fromJson(JSONObject(raw))
        } catch (e: Exception) {
            CardProfile()
        }
    }

    fun save(cardToken: String, profile: CardProfile) {
        prefs.edit().putString(cardToken, profile.toJson().toString()).apply()
    }
}
