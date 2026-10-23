package com.agentetrading.control.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.unit.dp
import com.agentetrading.control.format.Format
import com.agentetrading.control.model.Learning
import com.agentetrading.control.ui.components.LabeledValue
import com.agentetrading.control.ui.components.Note
import com.agentetrading.control.ui.components.SectionCard

@Composable
fun LearningScreen(
    learning: Learning,
    demo: Boolean,
) {
    val suffix = if (demo) " · ejemplo" else ""
    LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            SectionCard("Dónde se gana y se pierde$suffix") {
                learning.tagImpact.forEach {
                    LabeledValue(it.tag, "${it.count} · ${Format.r(it.totalR)}")
                }
            }
        }
        items(learning.trades) { trade ->
            SectionCard("${trade.symbol} · ${trade.side} · ${trade.strategy}$suffix") {
                LabeledValue("Resultado", Format.r(trade.rMultiple))
                LabeledValue("Slippage entrada / salida", "${Format.bps(trade.entrySlippageBps)} / ${Format.bps(trade.exitSlippageBps)}")
                LabeledValue("MAE / MFE", "${Format.r(trade.maeR)} / ${Format.r(trade.mfeR)}")
                Text("Razonamiento: ${trade.rationale}", style = MaterialTheme.typography.bodyMedium)
                Note("Etiquetas: ${trade.tags.joinToString(" · ")}")
            }
        }
        item {
            SectionCard("Línea de tiempo") {
                learning.timeline.forEach { Note(it) }
            }
        }
    }
}
