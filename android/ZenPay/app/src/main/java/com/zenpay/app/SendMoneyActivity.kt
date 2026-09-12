package com.zenpay.app

import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.zenpay.app.databinding.ActivitySendMoneyBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private val QUICK_AMOUNTS = listOf(50.0, 100.0, 500.0, 1000.0)

/**
 * Sends fake money to a ZenPay ID that ScanActivity already validated as a
 * genuine ZenPay user (never a real UPI handle — see QrValidator.kt). The
 * send itself is instant and fully local (LocalWallet.kt); if "sync to
 * analyst console" is on and the backend is reachable, the transfer is also
 * mirrored there so the *other* device's balance actually reflects it.
 */
class SendMoneyActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySendMoneyBinding
    private lateinit var wallet: WalletStore
    private lateinit var historyStore: HistoryStore
    private lateinit var targetId: String

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySendMoneyBinding.inflate(layoutInflater)
        setContentView(binding.root)

        targetId = intent.getStringExtra(EXTRA_SCANNED_ZENPAY_ID).orEmpty()
        if (targetId.length != 15) {
            Toast.makeText(this, "No valid ZenPay ID to send to.", Toast.LENGTH_LONG).show()
            finish()
            return
        }

        wallet = WalletStore(this)
        historyStore = HistoryStore(this)

        binding.targetIdText.text = targetId.chunked(3).joinToString(" ")
        refreshBalance()
        buildQuickAmountChips()

        binding.backButton.setOnClickListener { finish() }
        binding.sendButton.setOnClickListener { submit() }
    }

    private fun refreshBalance() {
        binding.yourBalanceText.text = "Your balance: ₹${"%,.2f".format(wallet.balance())}"
    }

    private fun buildQuickAmountChips() {
        binding.quickAmountContainer.removeAllViews()
        val marginPx = (6 * resources.displayMetrics.density).toInt()
        for (amount in QUICK_AMOUNTS) {
            val chip = Button(this).apply {
                text = "₹${"%,.0f".format(amount)}"
                textSize = 11.5f
                isAllCaps = false
                setTextColor(ContextCompat.getColor(context, R.color.primary))
                background = ContextCompat.getDrawable(context, R.drawable.chip_bg)
                setPadding(marginPx * 3, marginPx, marginPx * 3, marginPx)
                minWidth = 0
                minimumWidth = 0
                val lp = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
                lp.marginEnd = marginPx
                layoutParams = lp
                setOnClickListener { binding.amountInput.setText(amount.toInt().toString()) }
            }
            binding.quickAmountContainer.addView(chip)
        }
    }

    private fun submit() {
        val amount = binding.amountInput.text?.toString()?.toDoubleOrNull()
        if (amount == null || amount <= 0.0) {
            Toast.makeText(this, "Enter an amount greater than ₹0.", Toast.LENGTH_SHORT).show()
            return
        }

        setLoading(true)
        lifecycleScope.launch {
            val myId = UserIdentity.getOrCreate(this@SendMoneyActivity)
            val result = withContext(Dispatchers.Default) {
                LocalWallet.send(applicationContext, myId, targetId, amount)
            }
            setLoading(false)
            if (!result.ok) {
                Toast.makeText(this@SendMoneyActivity, result.error.ifBlank { "Transfer failed." }, Toast.LENGTH_LONG).show()
                return@launch
            }

            historyStore.add(
                HistoryEntry(
                    txnId = result.txnId, ts = System.currentTimeMillis(),
                    payee = "Sent to •••${targetId.takeLast(4)}", amount = result.amount,
                    vpa = targetId, score = result.score, severity = result.severity,
                    outcome = result.outcome, suspicious = false,
                )
            )
            val baseOutcome = "${result.outcome}\nRisk score ${"%.2f".format(result.score)} · ${result.severity.uppercase()}"
            showResult(result, baseOutcome)
            maybeSyncTransfer(myId, targetId, amount, baseOutcome)
        }
    }

    /** Mirrors the already-completed local transfer to the shared backend
     * wallet so the OTHER device sees it land over cellular or Wi-Fi. */
    private fun maybeSyncTransfer(myId: String, toId: String, amount: Double, baseOutcome: String) {
        if (!SyncSettings.isEnabled(this)) {
            binding.outcomeText.text = "$baseOutcome\n• Offline mode (local only)"
            return
        }
        lifecycleScope.launch {
            val result = runCatching { PortalApi(SyncSettings.url(this@SendMoneyActivity)).transfer(myId, toId, amount) }.getOrNull()
            if (result?.ok == true) {
                wallet.set(result.fromBalance)
                refreshBalance()
                binding.outcomeText.text = "$baseOutcome\n✓ Cloud synced · Recipient credited"
            } else {
                binding.outcomeText.text = "$baseOutcome\n• Saved locally (offline)"
            }
        }
    }

    private fun setLoading(loading: Boolean) {
        binding.progressBar.visibility = if (loading) View.VISIBLE else View.GONE
        binding.sendButton.isEnabled = !loading
    }

    private fun showResult(r: TransferResult, baseOutcome: String) {
        binding.resultCard.visibility = View.VISIBLE
        binding.resultCard.alpha = 0f
        binding.resultCard.animate().alpha(1f).setDuration(220).start()

        binding.resultTxnText.text = "Transaction ID: ${r.txnId}"
        val (bg, fg) = when {
            r.outcome.startsWith("Blocked") -> R.color.frozen_bg to R.color.frozen_text
            r.outcome.startsWith("Flagged") -> R.color.alert_bg to R.color.alert_text
            else -> R.color.success_bg to R.color.success_text
        }
        binding.outcomeText.text = baseOutcome
        binding.outcomeText.background = GradientDrawable().apply {
            setColor(ContextCompat.getColor(this@SendMoneyActivity, bg))
            cornerRadius = 12 * resources.displayMetrics.density
        }
        binding.outcomeText.setTextColor(ContextCompat.getColor(this, fg))
    }
}
