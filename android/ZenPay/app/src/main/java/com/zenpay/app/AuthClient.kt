package com.zenpay.app

import android.util.Base64
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.security.MessageDigest
import java.security.SecureRandom
import java.util.concurrent.TimeUnit

/**
 * Google sign-in for ZenPay, via the SAME Supabase project (and therefore
 * the same already-configured Google OAuth consent screen) the Zen analyst
 * web console uses — see app/auth.py's `SUPABASE_URL`/`SUPABASE_PUBLISHABLE_KEY`,
 * copied here verbatim since they're the publishable, client-safe values
 * that module itself embeds directly.
 *
 * One-time setup this app CANNOT do for you: the redirect URI below
 * (`zenpay://auth-callback`) must be added to this Supabase project's
 * Authentication → URL Configuration → Redirect URLs allow-list, or Google
 * will bounce back with "requested path is invalid" even though everything
 * else here is correct — same gotcha app/auth.py's OAUTH_CALLBACK_PATH
 * comment already documents for the web app's own callback path.
 *
 * Flow: open Supabase's PKCE-protected /authorize URL in a Custom Tab (real
 * browser, not a WebView, so saved Google sessions/passkeys work) ->
 * Google's consent screen redirects to `zenpay://auth-callback?code=...` ->
 * LoginActivity's intent-filter catches that -> this class exchanges the
 * code for a session via a plain REST call to Supabase's GoTrue token
 * endpoint (no Supabase Android SDK needed for one endpoint).
 */
object AuthClient {
    const val SUPABASE_URL = "https://mpduaztlanucevfbpaip.supabase.co"
    const val SUPABASE_PUBLISHABLE_KEY = "sb_publishable_rDXMQ1jB-V2RGPhcWqPbEg_dIpxKZBl"
    const val REDIRECT_URI = "zenpay://auth-callback"

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .build()

    data class OAuthStart(val url: String, val codeVerifier: String)

    data class AuthResult(
        val ok: Boolean,
        val error: String = "",
        val accessToken: String = "",
        val refreshToken: String = "",
        val userId: String = "",
        val email: String = "",
        val displayName: String = "",
    )

    /** Builds the Google consent-screen URL and the PKCE verifier the
     * caller must hold onto (LoginActivity stashes it via SessionStore)
     * until the redirect comes back. */
    fun startGoogleOAuth(): OAuthStart {
        val verifier = randomUrlSafe(64)
        val challenge = base64Url(MessageDigest.getInstance("SHA-256").digest(verifier.toByteArray()))
        val url = "$SUPABASE_URL/auth/v1/authorize" +
            "?provider=google" +
            "&redirect_to=${java.net.URLEncoder.encode(REDIRECT_URI, "UTF-8")}" +
            "&code_challenge=$challenge" +
            "&code_challenge_method=s256"
        return OAuthStart(url, verifier)
    }

    suspend fun completeOAuth(authCode: String, codeVerifier: String): AuthResult = withContext(Dispatchers.IO) {
        Log.i("ZenPayAuth", "Posting token exchange to $SUPABASE_URL/auth/v1/token?grant_type=pkce")
        val body = JSONObject().apply {
            put("auth_code", authCode)
            put("code_verifier", codeVerifier)
        }.toString().toRequestBody("application/json; charset=utf-8".toMediaType())

        val request = Request.Builder()
            .url("$SUPABASE_URL/auth/v1/token?grant_type=pkce")
            .addHeader("apikey", SUPABASE_PUBLISHABLE_KEY)
            .post(body)
            .build()

        try {
            client.newCall(request).execute().use { response ->
                val text = response.body?.string().orEmpty()
                Log.i("ZenPayAuth", "Supabase token endpoint returned HTTP ${response.code}")
                if (!response.isSuccessful || text.isEmpty()) {
                    val msg = runCatching { JSONObject(text).optString("error_description") }.getOrNull()
                    Log.e("ZenPayAuth", "Supabase token exchange failed: HTTP ${response.code}, body=$text")
                    return@withContext AuthResult(ok = false, error = msg?.ifBlank { null } ?: "Sign-in failed (HTTP ${response.code}).")
                }
                val json = JSONObject(text)
                val user = json.optJSONObject("user")
                val meta = user?.optJSONObject("user_metadata")
                val email = user?.optString("email").orEmpty()
                val displayName = meta?.optString("display_name")?.ifBlank { null }
                    ?: meta?.optString("full_name")?.ifBlank { null }
                    ?: meta?.optString("name")?.ifBlank { null }
                    ?: email.substringBefore("@").ifBlank { null }
                    ?: "ZenPay user"
                Log.i("ZenPayAuth", "Token exchange successful for user $displayName ($email)")
                AuthResult(
                    ok = true,
                    accessToken = json.optString("access_token"),
                    refreshToken = json.optString("refresh_token"),
                    userId = user?.optString("id").orEmpty(),
                    email = email,
                    displayName = displayName,
                )
            }
        } catch (e: java.io.IOException) {
            Log.e("ZenPayAuth", "IOException during Supabase token exchange: ${e.message}", e)
            AuthResult(ok = false, error = e.message ?: "Couldn't reach Supabase.")
        }
    }

    private fun randomUrlSafe(byteLength: Int): String =
        base64Url(ByteArray(byteLength).also { SecureRandom().nextBytes(it) })

    private fun base64Url(bytes: ByteArray): String =
        Base64.encodeToString(bytes, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)
}
