package com.zenpay.app

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/** One simulated payment result — mirrors app/portal.py's `PayResponse`. */
data class PayResult(
    val ok: Boolean,
    val error: String = "",
    val txnId: String = "",
    val vpa: String = "",
    val uri: String = "",
    val amount: Double = 0.0,
    val payee: String = "",
    val score: Double = 0.0,
    val severity: String = "",
    val outcome: String = "",
    val qrModules: List<List<Boolean>> = emptyList(),
)

/** Result of a Settings-screen "Test Connection" check. */
data class PingResult(val ok: Boolean, val message: String)

/** Result of a synced P2P transfer — mirrors app/portal.py's `TransferResponse`. */
data class SyncTransferResult(
    val ok: Boolean,
    val error: String = "",
    val fromBalance: Double = 0.0,
    val toBalance: Double = 0.0,
)

/** A wallet's authoritative server-side balance — mirrors `WalletResponse`. */
data class WalletBalanceResult(val ok: Boolean, val balance: Double = 0.0)

/** One completed transfer credited to this wallet by ANOTHER device —
 * mirrors app/portal.py's `IncomingTransfer`. */
data class IncomingTransfer(
    val txnId: String, val fromId: String, val amount: Double, val ts: Double,
    val score: Double, val severity: String, val outcome: String,
)

/**
 * Optional bridge to app/portal.py in the Python backend, used only for the
 * "sync test payments to analyst console" toggle in Settings (on by default,
 * but purely opportunistic) — LocalPortal.kt does the real work (validation,
 * scoring, QR) entirely on-device, so nothing in the app's core Pay flow
 * depends on this class or on the backend being reachable at all. `baseUrl`
 * should be this machine's LAN IP (phone and computer on the same Wi-Fi);
 * 127.0.0.1 also works if you'd rather tunnel over USB with
 * `adb reverse tcp:8080 tcp:8080`.
 */
class PortalApi(private val baseUrl: String) {

    private val client = OkHttpClient.Builder()
        .connectTimeout(6, TimeUnit.SECONDS)
        .readTimeout(6, TimeUnit.SECONDS)
        .build()

    suspend fun ping(): PingResult = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder().url("$baseUrl/api/portal/ping").get().build()
            client.newCall(request).execute().use { response ->
                if (response.isSuccessful) {
                    PingResult(true, "Connected — backend is reachable at $baseUrl.")
                } else {
                    PingResult(false, "Backend responded with HTTP ${response.code}.")
                }
            }
        } catch (e: IOException) {
            PingResult(false, "Couldn't reach $baseUrl — ${e.message ?: "connection failed"}.")
        }
    }

    suspend fun pay(card: String, amount: Double, payee: String, suspicious: Boolean): PayResult =
        withContext(Dispatchers.IO) {
            val body = JSONObject().apply {
                put("card", card)
                put("amount", amount)
                put("payee", payee)
                put("suspicious", suspicious)
            }.toString().toRequestBody("application/json; charset=utf-8".toMediaType())

            val request = Request.Builder()
                .url("$baseUrl/api/portal/pay")
                .post(body)
                .build()

            try {
                client.newCall(request).execute().use { response ->
                    val text = response.body?.string().orEmpty()
                    if (!response.isSuccessful || text.isEmpty()) {
                        return@withContext PayResult(ok = false, error = "Server error (HTTP ${response.code}). Is the backend running?")
                    }
                    parse(text)
                }
            } catch (e: IOException) {
                PayResult(ok = false, error = "Couldn't reach the backend at $baseUrl — check your phone and computer are on the same Wi-Fi, or use Settings to test the connection.")
            }
        }

    /** Mirrors a completed local transfer to the shared backend wallet
     * ledger — best-effort, only meaningful when both the sender's and
     * receiver's devices have sync on and point at the same backend. */
    suspend fun transfer(fromId: String, toId: String, amount: Double): SyncTransferResult =
        withContext(Dispatchers.IO) {
            val body = JSONObject().apply {
                put("from_id", fromId)
                put("to_id", toId)
                put("amount", amount)
            }.toString().toRequestBody("application/json; charset=utf-8".toMediaType())

            val request = Request.Builder().url("$baseUrl/api/portal/transfer").post(body).build()
            try {
                client.newCall(request).execute().use { response ->
                    val text = response.body?.string().orEmpty()
                    if (!response.isSuccessful || text.isEmpty()) {
                        return@withContext SyncTransferResult(ok = false, error = "HTTP ${response.code}")
                    }
                    val json = JSONObject(text)
                    SyncTransferResult(
                        ok = json.optBoolean("ok", false),
                        error = json.optString("error", ""),
                        fromBalance = json.optDouble("from_balance", 0.0),
                        toBalance = json.optDouble("to_balance", 0.0),
                    )
                }
            } catch (e: IOException) {
                SyncTransferResult(ok = false, error = e.message ?: "connection failed")
            }
        }

    /** This device's authoritative shared balance, when sync is on and the
     * backend is reachable — lets an *incoming* transfer from another
     * synced device actually show up here on refresh. */
    suspend fun walletBalance(id: String): WalletBalanceResult = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder().url("$baseUrl/api/portal/wallet/$id").get().build()
            client.newCall(request).execute().use { response ->
                val text = response.body?.string().orEmpty()
                if (!response.isSuccessful || text.isEmpty()) return@withContext WalletBalanceResult(ok = false)
                WalletBalanceResult(ok = true, balance = JSONObject(text).optDouble("balance", 0.0))
            }
        } catch (e: IOException) {
            WalletBalanceResult(ok = false)
        }
    }

    /** Transfers credited to `id` after `sinceTs` — what actually lets the
     * receiving device add a "Received from •••XXXX" entry to its own Past
     * Transactions instead of just seeing a balance number change with no
     * explanation. Returns an empty list (never throws) on any failure, so
     * a flaky connection just means "nothing new yet," not a crash. */
    suspend fun incoming(id: String, sinceTs: Double): List<IncomingTransfer> = withContext(Dispatchers.IO) {
        try {
            val url = "$baseUrl/api/portal/wallet/$id/incoming?since_ts=$sinceTs"
            val request = Request.Builder().url(url).get().build()
            client.newCall(request).execute().use { response ->
                val text = response.body?.string().orEmpty()
                if (!response.isSuccessful || text.isEmpty()) return@withContext emptyList()
                val arr = JSONObject(text).optJSONArray("transfers") ?: JSONArray()
                (0 until arr.length()).map { i ->
                    val o = arr.getJSONObject(i)
                    IncomingTransfer(
                        txnId = o.optString("txn_id"), fromId = o.optString("from_id"),
                        amount = o.optDouble("amount"), ts = o.optDouble("ts"),
                        score = o.optDouble("score"), severity = o.optString("severity"),
                        outcome = o.optString("outcome"),
                    )
                }
            }
        } catch (e: IOException) {
            emptyList()
        }
    }

    private fun parse(text: String): PayResult {
        val json = JSONObject(text)
        val modulesJson: JSONArray = json.optJSONArray("qr_modules") ?: JSONArray()
        val modules = (0 until modulesJson.length()).map { r ->
            val row = modulesJson.getJSONArray(r)
            (0 until row.length()).map { c -> row.getBoolean(c) }
        }
        return PayResult(
            ok = json.optBoolean("ok", false),
            error = json.optString("error", ""),
            txnId = json.optString("txn_id", ""),
            vpa = json.optString("vpa", ""),
            uri = json.optString("uri", ""),
            amount = json.optDouble("amount", 0.0),
            payee = json.optString("payee", ""),
            score = json.optDouble("score", 0.0),
            severity = json.optString("severity", ""),
            outcome = json.optString("outcome", ""),
            qrModules = modules,
        )
    }
}
