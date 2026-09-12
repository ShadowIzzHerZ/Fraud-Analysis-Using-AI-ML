package com.zenpay.app

import android.content.Context
import org.json.JSONArray

private const val PREFS = "zenpay_history"
private const val KEY_ENTRIES = "entries"
private const val MAX_ENTRIES = 100

/** Local, on-device log of every simulated payment — newest first. This is
 * the app's only source of truth for "past transactions" (see MainActivity
 * / HistoryActivity); nothing here ever depends on a backend being up. */
class HistoryStore(context: Context) {
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun add(entry: HistoryEntry) {
        val all = loadAll().toMutableList()
        all.add(0, entry)
        while (all.size > MAX_ENTRIES) all.removeAt(all.size - 1)
        val arr = JSONArray()
        all.forEach { arr.put(it.toJson()) }
        prefs.edit().putString(KEY_ENTRIES, arr.toString()).apply()
    }

    fun loadAll(): List<HistoryEntry> {
        val raw = prefs.getString(KEY_ENTRIES, null) ?: return emptyList()
        return try {
            val arr = JSONArray(raw)
            (0 until arr.length()).map { HistoryEntry.fromJson(arr.getJSONObject(it)) }
        } catch (e: Exception) {
            emptyList()
        }
    }

    fun clear() {
        prefs.edit().remove(KEY_ENTRIES).apply()
    }
}
