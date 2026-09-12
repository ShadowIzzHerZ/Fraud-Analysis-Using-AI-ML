package com.zenpay.app

import android.os.Bundle
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.zenpay.app.databinding.ActivityHistoryBinding

class HistoryActivity : AppCompatActivity() {

    private lateinit var binding: ActivityHistoryBinding
    private lateinit var store: HistoryStore
    private lateinit var adapter: HistoryAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityHistoryBinding.inflate(layoutInflater)
        setContentView(binding.root)

        store = HistoryStore(this)
        adapter = HistoryAdapter(emptyList())
        binding.historyRecyclerView.layoutManager = LinearLayoutManager(this)
        binding.historyRecyclerView.adapter = adapter

        binding.backButton.setOnClickListener { finish() }
        binding.clearHistoryButton.setOnClickListener { confirmClear() }

        refresh()
    }

    override fun onResume() {
        super.onResume()
        refresh()
    }

    private fun refresh() {
        val items = store.loadAll()
        adapter.submit(items)
        binding.emptyText.visibility = if (items.isEmpty()) android.view.View.VISIBLE else android.view.View.GONE
        binding.historyRecyclerView.visibility = if (items.isEmpty()) android.view.View.GONE else android.view.View.VISIBLE
    }

    private fun confirmClear() {
        AlertDialog.Builder(this)
            .setTitle("Clear history?")
            .setMessage("This removes every locally saved test payment from this device. It doesn't affect anything already synced to an analyst console.")
            .setPositiveButton("Clear") { _, _ ->
                store.clear()
                refresh()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }
}
