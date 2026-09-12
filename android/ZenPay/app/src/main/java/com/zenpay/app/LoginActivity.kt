package com.zenpay.app

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.browser.customtabs.CustomTabsIntent
import androidx.lifecycle.lifecycleScope
import com.zenpay.app.databinding.ActivityLoginBinding
import kotlinx.coroutines.launch

/**
 * Google sign-in, launched by MainActivity when there's no session
 * (SessionStore.isSignedIn). Also the target of the `zenpay://auth-callback`
 * intent-filter Google/Supabase redirects back to once sign-in completes —
 * see AuthClient.kt for the full flow and the one manual setup step it
 * needs (adding that redirect URI to the Supabase project).
 */
class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding

    companion object {
        private const val TAG = "ZenPayAuth"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Log.i(TAG, "LoginActivity created, checking initial intent...")
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.googleSignInButton.setOnClickListener { startSignIn() }
        handleIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        Log.i(TAG, "LoginActivity onNewIntent called: action=${intent.action}, data=${intent.data}")
        setIntent(intent)
        handleIntent(intent)
    }

    private fun handleIntent(intent: Intent) {
        val uri = intent.data ?: run {
            Log.d(TAG, "handleIntent: intent.data is null")
            return
        }
        Log.i(TAG, "handleIntent: received uri=$uri, scheme=${uri.scheme}, host=${uri.host}")
        if (uri.scheme != "zenpay" || uri.host != "auth-callback") {
            Log.w(TAG, "handleIntent: unhandled scheme or host, ignoring")
            return
        }

        val error = uri.getQueryParameter("error_description") ?: uri.getQueryParameter("error")
        if (error != null) {
            Log.e(TAG, "handleIntent: received OAuth error: $error")
            showStatus(error)
            return
        }
        val code = uri.getQueryParameter("code") ?: run {
            Log.e(TAG, "handleIntent: missing 'code' query parameter in $uri")
            showStatus("Sign-in didn't return an authorization code.")
            return
        }
        val verifier = SessionStore.takePkceVerifier(this) ?: run {
            Log.e(TAG, "handleIntent: no PKCE verifier stored in SessionStore")
            showStatus("Sign-in session expired — try again.")
            return
        }

        Log.i(TAG, "handleIntent: valid code and verifier found. Exchanging code for Supabase session...")
        setLoading(true)
        lifecycleScope.launch {
            val result = AuthClient.completeOAuth(code, verifier)
            setLoading(false)
            if (!result.ok) {
                Log.e(TAG, "completeOAuth failed: ${result.error}")
                showStatus(result.error.ifBlank { "Sign-in failed." })
                return@launch
            }
            Log.i(TAG, "completeOAuth success: user=${result.displayName} (${result.email}), saving session...")
            SessionStore.save(this@LoginActivity, result)
            startActivity(Intent(this@LoginActivity, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK))
            finish()
        }
    }

    private fun startSignIn() {
        binding.statusText.visibility = View.GONE
        val start = AuthClient.startGoogleOAuth()
        Log.i(TAG, "startSignIn: launching Custom Tab to ${start.url}")
        SessionStore.stashPkceVerifier(this, start.codeVerifier)
        CustomTabsIntent.Builder().build().launchUrl(this, Uri.parse(start.url))
    }

    private fun setLoading(loading: Boolean) {
        binding.progressBar.visibility = if (loading) View.VISIBLE else View.GONE
        binding.googleSignInButton.isEnabled = !loading
    }

    private fun showStatus(message: String) {
        binding.statusText.text = message
        binding.statusText.visibility = View.VISIBLE
    }
}

