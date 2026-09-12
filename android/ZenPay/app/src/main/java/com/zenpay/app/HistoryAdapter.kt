package com.zenpay.app

import android.graphics.drawable.GradientDrawable
import android.text.format.DateUtils
import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.RecyclerView

class HistoryAdapter(private var items: List<HistoryEntry>) : RecyclerView.Adapter<HistoryAdapter.VH>() {

    class VH(view: android.view.View) : RecyclerView.ViewHolder(view) {
        val payee: android.widget.TextView = view.findViewById(R.id.itemPayee)
        val amount: android.widget.TextView = view.findViewById(R.id.itemAmount)
        val meta: android.widget.TextView = view.findViewById(R.id.itemMeta)
        val outcome: android.widget.TextView = view.findViewById(R.id.itemOutcome)
    }

    fun submit(newItems: List<HistoryEntry>) {
        items = newItems
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_history, parent, false)
        return VH(view)
    }

    override fun getItemCount(): Int = items.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        val e = items[position]
        val ctx = holder.itemView.context
        holder.payee.text = e.payee
        val sign = if (e.incoming) "+" else "−"
        holder.amount.text = "$sign₹${"%,.2f".format(e.amount)}"
        holder.amount.setTextColor(
            ContextCompat.getColor(ctx, if (e.incoming) R.color.success_text else R.color.primary)
        )
        val relative = DateUtils.getRelativeTimeSpanString(e.ts, System.currentTimeMillis(), DateUtils.MINUTE_IN_MILLIS)
        val suspiciousTag = if (e.suspicious) " · flagged as suspicious pattern" else ""
        holder.meta.text = "$relative · ${e.txnId.takeLast(9).uppercase()}$suspiciousTag"

        holder.outcome.text = "${e.outcome} · ${"%.2f".format(e.score)}"
        val (bg, fg) = when {
            e.outcome.startsWith("Blocked") -> R.color.frozen_bg to R.color.frozen_text
            e.outcome.startsWith("Flagged") -> R.color.alert_bg to R.color.alert_text
            else -> R.color.success_bg to R.color.success_text
        }
        holder.outcome.background = GradientDrawable().apply {
            setColor(ContextCompat.getColor(ctx, bg))
            cornerRadius = 8 * ctx.resources.displayMetrics.density
        }
        holder.outcome.setTextColor(ContextCompat.getColor(ctx, fg))
    }
}
