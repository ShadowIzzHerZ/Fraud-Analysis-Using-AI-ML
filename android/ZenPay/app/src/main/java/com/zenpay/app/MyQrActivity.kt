package com.zenpay.app

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.zenpay.app.databinding.ActivityMyQrBinding

/** Shows this device's own ZenPay ID as a QR (for another device to scan
 * with "Scan & Send") plus its local fake wallet balance. */
class MyQrActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMyQrBinding
    private lateinit var wallet: WalletStore

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMyQrBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val id = UserIdentity.getOrCreate(this)
        wallet = WalletStore(this)

        binding.idText.text = id.chunked(3).joinToString(" ")
        binding.qrView.setModules(QrCodes.modules("zenpay://user/$id"))

        binding.backButton.setOnClickListener { finish() }
        binding.copyButton.setOnClickListener {
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            clipboard.setPrimaryClip(ClipData.newPlainText("ZenPay ID", id))
            Toast.makeText(this, "ID copied.", Toast.LENGTH_SHORT).show()
        }
        binding.resetButton.setOnClickListener {
            AlertDialog.Builder(this)
                .setTitle("Reset fake balance?")
                .setMessage("Sets this device's local wallet back to ₹1,00,000. Doesn't affect anything already sent or received.")
                .setPositiveButton("Reset") { _, _ ->
                    wallet.reset()
                    refreshBalance()
                }
                .setNegativeButton("Cancel", null)
                .show()
        }
    }

    override fun onResume() {
        super.onResume()
        refreshBalance()
    }

    private fun refreshBalance() {
        binding.balanceText.text = "₹${"%,.2f".format(wallet.balance())}"
    }
}
