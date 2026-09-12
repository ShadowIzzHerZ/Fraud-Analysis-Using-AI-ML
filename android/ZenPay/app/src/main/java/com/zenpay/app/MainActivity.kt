package com.zenpay.app

import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.zenpay.app.databinding.ActivityMainBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private val QUICK_AMOUNTS = listOf(99.0, 499.0, 999.0, 2999.0)

/**
 * ZenPay works fully offline — every payment is validated, scored,
 * and turned into a QR entirely on-device (LocalPortal.kt); nothing here
 * requires the Python backend to be running or even reachable.
 *
 * The only network use is "analyst console sync" in Settings — on by
 * default, but purely opportunistic: a best-effort, fire-and-forget mirror
 * of a completed local result to app/portal.py, tried after every payment
 * and silently skipped if the backend isn't reachable. Its success, failure,
 * or absence never affects the core Pay flow or shows the user an error;
 * it's a bonus for the analyst dashboard, not a requirement.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var historyStore: HistoryStore
    private lateinit var wallet: WalletStore

    private val scanLauncher = registerForActivityResult(androidx.activity.result.contract.ActivityResultContracts.StartActivityForResult()) { result ->
        val id = result.data?.getStringExtra(EXTRA_SCANNED_ZENPAY_ID)
        if (result.resultCode == RESULT_OK && id != null) {
            startActivity(Intent(this, SendMoneyActivity::class.java).putExtra(EXTRA_SCANNED_ZENPAY_ID, id))
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        if (!SessionStore.isSignedIn(this)) {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
            return
        }

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        historyStore = HistoryStore(this)
        wallet = WalletStore(this)

        binding.payeeSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, PAYEES)

        buildTestCardChips()
        buildQuickAmountChips()

        binding.settingsButton.setOnClickListener { showSettingsDialog() }
        binding.historyButton.setOnClickListener { startActivity(Intent(this, HistoryActivity::class.java)) }
        binding.viewAllHistoryText.setOnClickListener { startActivity(Intent(this, HistoryActivity::class.java)) }
        binding.myQrButton.setOnClickListener { startActivity(Intent(this, MyQrActivity::class.java)) }
        binding.scanButton.setOnClickListener { scanLauncher.launch(Intent(this, ScanActivity::class.java)) }

        binding.sendByIdButton.setOnClickListener {
            val raw = binding.idInput.text?.toString().orEmpty()
            val cleanId = raw.filter { it.isDigit() }
            val myId = UserIdentity.getOrCreate(this)
            if (cleanId.length != 15) {
                Toast.makeText(this, "Please enter a valid 15-digit ZenPay ID (entered ${cleanId.length} digits).", Toast.LENGTH_LONG).show()
                return@setOnClickListener
            }
            if (cleanId == myId) {
                Toast.makeText(this, "You cannot send money to your own ZenPay ID.", Toast.LENGTH_LONG).show()
                return@setOnClickListener
            }
            startActivity(Intent(this, SendMoneyActivity::class.java).putExtra(EXTRA_SCANNED_ZENPAY_ID, cleanId))
        }

        binding.idInputLayout.setEndIconOnClickListener {
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
            val clip = clipboard?.primaryClip?.getItemAt(0)?.text?.toString().orEmpty()
            val digits = clip.filter { it.isDigit() }
            if (digits.length >= 15) {
                binding.idInput.setText(digits.take(15))
                Toast.makeText(this, "Pasted ID from clipboard.", Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(this, "Clipboard doesn't contain a 15-digit ID.", Toast.LENGTH_SHORT).show()
            }
        }

        binding.payButton.setOnClickListener { submit(suspicious = false) }
        binding.suspiciousButton.setOnClickListener { submit(suspicious = true) }
    }

    override fun onResume() {
        super.onResume()
        refreshRecentActivity()
        refreshWalletBalance()
    }

    private fun refreshWalletBalance() {
        binding.walletBalanceText.text = "Wallet: ₹${"%,.2f".format(wallet.balance())}"
        if (SyncSettings.isEnabled(this)) {
            val myId = UserIdentity.getOrCreate(this)
            val api = PortalApi(SyncSettings.url(this))
            lifecycleScope.launch {
                val result = runCatching { api.walletBalance(myId) }.getOrNull()
                if (result?.ok == true) {
                    wallet.set(result.balance)
                    binding.walletBalanceText.text = "Wallet: ₹${"%,.2f".format(result.balance)}"
                }
                recordNewIncomingTransfers(api, myId)
            }
        }
    }

    /** The balance poll above tells this device a credit landed; this is
     * what turns that into an actual "Received from •••XXXX" entry in Past
     * Transactions instead of a wallet number that just changed with no
     * explanation (see IncomingSync.kt / app/portal.py's /incoming). */
    private suspend fun recordNewIncomingTransfers(api: PortalApi, myId: String) {
        val since = IncomingSync.lastSeenTs(this)
        val transfers = runCatching { api.incoming(myId, since) }.getOrDefault(emptyList())
        if (transfers.isEmpty()) return

        for (t in transfers) {
            historyStore.add(
                HistoryEntry(
                    txnId = t.txnId, ts = (t.ts * 1000).toLong(),
                    payee = "Received from •••${t.fromId.takeLast(4)}", amount = t.amount,
                    vpa = t.fromId, score = t.score, severity = t.severity,
                    outcome = t.outcome, suspicious = false, incoming = true,
                )
            )
        }
        IncomingSync.markSeen(this, transfers.maxOf { it.ts })
        refreshRecentActivity()
    }

    // -- settings (optional analyst sync only — never required) --------------

    private fun showSettingsDialog() {
        val density = resources.displayMetrics.density
        val pad = (16 * density).toInt()

        val container = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            setPadding(pad, pad / 2, pad, 0)
        }

        val accountText = TextView(this).apply {
            text = "Signed in as ${SessionStore.displayName(this@MainActivity)} (${SessionStore.email(this@MainActivity)})"
            textSize = 12.5f
            setTextColor(ContextCompat.getColor(context, R.color.muted))
            setPadding(0, 0, 0, (12 * density).toInt())
        }
        container.addView(accountText)

        val signOutButton = Button(this).apply {
            text = "Sign out"
            isAllCaps = false
            setOnClickListener {
                SessionStore.signOut(this@MainActivity)
                startActivity(Intent(this@MainActivity, LoginActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK))
                finish()
            }
        }
        container.addView(signOutButton)

        val divider = View(this).apply {
            setBackgroundColor(ContextCompat.getColor(context, R.color.outline_variant))
            layoutParams = android.widget.LinearLayout.LayoutParams(android.widget.LinearLayout.LayoutParams.MATCH_PARENT, (1 * density).toInt()).apply {
                topMargin = (12 * density).toInt()
                bottomMargin = (12 * density).toInt()
            }
        }
        container.addView(divider)

        val switchRow = Switch(this).apply {
            text = "Sync test payments to analyst console"
            isChecked = SyncSettings.isEnabled(this@MainActivity)
        }
        container.addView(switchRow)

        val urlInput = EditText(this).apply {
            inputType = InputType.TYPE_TEXT_VARIATION_URI
            hint = "https://<cloud-url> or http://<LAN-IP>:8080"
            setText(SyncSettings.url(this@MainActivity))
        }
        container.addView(urlInput)

        val statusText = TextView(this).apply {
            setPadding(0, (8 * density).toInt(), 0, 0)
            textSize = 12f
            setTextColor(ContextCompat.getColor(context, R.color.muted))
            text = "ZenPay syncs P2P transfers via Cloud Sync over cellular/any Wi-Fi. It also works fully offline. Enter a custom server URL or leave default."
        }
        container.addView(statusText)

        val buttonRow = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.HORIZONTAL
            val lp = android.widget.LinearLayout.LayoutParams(
                android.widget.LinearLayout.LayoutParams.MATCH_PARENT,
                android.widget.LinearLayout.LayoutParams.WRAP_CONTENT
            )
            layoutParams = lp
        }

        val testButton = Button(this).apply {
            text = "Test Connection"
            isAllCaps = false
            layoutParams = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            setOnClickListener {
                statusText.text = "Checking…"
                lifecycleScope.launch {
                    val result = PortalApi(urlInput.text.toString().trim().ifBlank { DEFAULT_SYNC_URL }).ping()
                    statusText.setTextColor(ContextCompat.getColor(this@MainActivity, if (result.ok) R.color.success_text else R.color.frozen_text))
                    statusText.text = result.message
                }
            }
        }
        buttonRow.addView(testButton)

        val resetButton = Button(this).apply {
            text = "Reset Default"
            isAllCaps = false
            layoutParams = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            setOnClickListener {
                urlInput.setText(DEFAULT_SYNC_URL)
            }
        }
        buttonRow.addView(resetButton)
        container.addView(buttonRow)

        AlertDialog.Builder(this)
            .setTitle("Settings")
            .setView(container)
            .setPositiveButton("Save") { _, _ ->
                val url = urlInput.text.toString().trim().ifBlank { DEFAULT_SYNC_URL }
                SyncSettings.setEnabled(this, switchRow.isChecked)
                SyncSettings.setUrl(this, url)
                Toast.makeText(this, "Settings saved.", Toast.LENGTH_SHORT).show()
                refreshWalletBalance()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    // -- quick actions ---------------------------------------------------------

    private fun buildTestCardChips() {
        binding.testCardsContainer.removeAllViews()
        val marginPx = (6 * resources.displayMetrics.density).toInt()
        for ((pan, label) in TEST_CARDS) {
            val chip = Button(this).apply {
                text = formatCardNumber(pan)
                textSize = 11f
                isAllCaps = false
                setTextColor(ContextCompat.getColor(context, R.color.on_surface))
                background = ContextCompat.getDrawable(context, R.drawable.chip_bg)
                setPadding(marginPx * 2, marginPx, marginPx * 2, marginPx)
                minWidth = 0
                minimumWidth = 0
                contentDescription = label
                val lp = android.widget.LinearLayout.LayoutParams(
                    android.widget.LinearLayout.LayoutParams.WRAP_CONTENT,
                    android.widget.LinearLayout.LayoutParams.WRAP_CONTENT,
                )
                lp.marginEnd = marginPx
                layoutParams = lp
                setOnClickListener { binding.cardInput.setText(pan) }
            }
            binding.testCardsContainer.addView(chip)
        }
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
                val lp = android.widget.LinearLayout.LayoutParams(
                    0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f,
                )
                lp.marginEnd = marginPx
                layoutParams = lp
                setOnClickListener { binding.amountInput.setText(amount.toInt().toString()) }
            }
            binding.quickAmountContainer.addView(chip)
        }
    }

    // -- pay ---------------------------------------------------------------

    private fun submit(suspicious: Boolean) {
        val card = binding.cardInput.text?.toString().orEmpty()
        val amountText = binding.amountInput.text?.toString().orEmpty()
        val amount = amountText.toDoubleOrNull()
        val payee = binding.payeeSpinner.selectedItem as? String ?: PAYEES.first()

        if (card.filter { it.isDigit() }.length < 12) {
            Toast.makeText(this, "Enter a test card number (or tap one below).", Toast.LENGTH_SHORT).show()
            return
        }
        if (amount == null || amount <= 0.0) {
            Toast.makeText(this, "Enter an amount greater than ₹0.", Toast.LENGTH_SHORT).show()
            return
        }

        setLoading(true)
        lifecycleScope.launch {
            val result = withContext(Dispatchers.Default) {
                LocalPortal.pay(applicationContext, card, amount, payee, suspicious)
            }
            setLoading(false)
            if (!result.ok) {
                Toast.makeText(this@MainActivity, result.error.ifBlank { "Payment simulation failed." }, Toast.LENGTH_LONG).show()
                return@launch
            }
            if (!result.outcome.startsWith("Blocked")) {
                wallet.set(maxOf(0.0, wallet.balance() - result.amount))
                binding.walletBalanceText.text = "Wallet: ₹${"%,.2f".format(wallet.balance())}"
            }
            historyStore.add(
                HistoryEntry(
                    txnId = result.txnId, ts = System.currentTimeMillis(), payee = result.payee,
                    amount = result.amount, vpa = result.vpa, score = result.score,
                    severity = result.severity, outcome = result.outcome, suspicious = suspicious,
                )
            )
            showResult(result)
            refreshRecentActivity()
            maybeSyncToAnalystConsole(card, amount, payee, suspicious)
        }
    }

    /** Best-effort only: never shown as an error to the user, never awaited
     * by anything the user is looking at. */
    private fun maybeSyncToAnalystConsole(card: String, amount: Double, payee: String, suspicious: Boolean) {
        if (!SyncSettings.isEnabled(this)) return
        lifecycleScope.launch {
            runCatching { PortalApi(SyncSettings.url(this@MainActivity)).pay(card, amount, payee, suspicious) }
        }
    }

    private fun setLoading(loading: Boolean) {
        binding.progressBar.visibility = if (loading) View.VISIBLE else View.GONE
        binding.payButton.isEnabled = !loading
        binding.suspiciousButton.isEnabled = !loading
    }

    private fun showResult(r: PayResult) {
        binding.resultCardOuter.visibility = View.VISIBLE
        binding.resultGroup.visibility = View.VISIBLE
        binding.resultCardOuter.alpha = 0f
        binding.resultCardOuter.animate().alpha(1f).setDuration(220).start()

        binding.qrView.setModules(r.qrModules)
        binding.vpaText.text = "Fake payee handle ${r.vpa}\n@fakebank is not a real PSP, so this QR cannot resolve or move money on any real UPI app."
        binding.payeeText.text = "Payee: ${r.payee}"
        binding.amountText.text = "Amount: ₹${"%,.2f".format(r.amount)}"
        binding.txnIdText.text = "Transaction ID: ${r.txnId}"

        val (bg, fg) = when {
            r.outcome.startsWith("Blocked") -> R.color.frozen_bg to R.color.frozen_text
            r.outcome.startsWith("Flagged") -> R.color.alert_bg to R.color.alert_text
            else -> R.color.success_bg to R.color.success_text
        }
        binding.outcomeText.text = "${r.outcome}\nRisk score ${"%.2f".format(r.score)} · ${r.severity.uppercase()}"
        binding.outcomeText.background = GradientDrawable().apply {
            setColor(ContextCompat.getColor(this@MainActivity, bg))
            cornerRadius = 12 * resources.displayMetrics.density
        }
        binding.outcomeText.setTextColor(ContextCompat.getColor(this, fg))
        binding.outcomeText.gravity = Gravity.CENTER
    }

    // -- recent activity preview --------------------------------------------

    private fun refreshRecentActivity() {
        val recent = historyStore.loadAll().take(3)
        binding.recentContainer.removeAllViews()
        if (recent.isEmpty()) {
            binding.recentCard.visibility = View.GONE
            return
        }
        binding.recentCard.visibility = View.VISIBLE
        val inflater = layoutInflater
        for (entry in recent) {
            val row = inflater.inflate(R.layout.item_history, binding.recentContainer, false)
            row.findViewById<TextView>(R.id.itemPayee).text = entry.payee
            row.findViewById<TextView>(R.id.itemAmount).text = "₹${"%,.2f".format(entry.amount)}"
            val relative = android.text.format.DateUtils.getRelativeTimeSpanString(entry.ts)
            row.findViewById<TextView>(R.id.itemMeta).text = "$relative · ${entry.txnId.takeLast(9).uppercase()}"
            val outcomeView = row.findViewById<TextView>(R.id.itemOutcome)
            outcomeView.text = "${entry.outcome} · ${"%.2f".format(entry.score)}"
            val (bg, fg) = when {
                entry.outcome.startsWith("Blocked") -> R.color.frozen_bg to R.color.frozen_text
                entry.outcome.startsWith("Flagged") -> R.color.alert_bg to R.color.alert_text
                else -> R.color.success_bg to R.color.success_text
            }
            outcomeView.background = GradientDrawable().apply {
                setColor(ContextCompat.getColor(this@MainActivity, bg))
                cornerRadius = 8 * resources.displayMetrics.density
            }
            outcomeView.setTextColor(ContextCompat.getColor(this, fg))
            row.setOnClickListener { startActivity(Intent(this, HistoryActivity::class.java)) }
            binding.recentContainer.addView(row)
        }
    }
}
