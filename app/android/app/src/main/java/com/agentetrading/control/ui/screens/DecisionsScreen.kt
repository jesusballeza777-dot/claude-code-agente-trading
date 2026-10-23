package com.agentetrading.control.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.runtime.Composable
import androidx.compose.ui.unit.dp
import com.agentetrading.control.format.Format
import com.agentetrading.control.model.Decisions
import com.agentetrading.control.ui.components.LabeledValue
import com.agentetrading.control.ui.components.Note
import com.agentetrading.control.ui.components.ProportionBar
import com.agentetrading.control.ui.components.SectionCard

@Composable
fun DecisionsScreen(
    decisions: Decisions,
    demo: Boolean,
) {
    val suffix = if (demo) " · ejemplo" else ""
    val top = decisions.funnel.maxOfOrNull { it.count }?.coerceAtLeast(1) ?: 1
    LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            SectionCard("Embudo de decisiones$suffix") {
                decisions.funnel.forEach { step ->
                    LabeledValue(step.label, step.count.toString())
                    ProportionBar(step.count.toFloat() / top)
                }
            }
        }
        item {
            SectionCard("Vetos del motor de riesgo$suffix") {
                decisions.vetoReasons.forEach { LabeledValue(it.label, it.count.toString()) }
            }
        }
        item {
            SectionCard("Valor añadido$suffix") {
                Note("Resultado medio en R de lo ejecutado frente a lo descartado, medido en sombra.")
                decisions.valueAdded.forEach {
                    LabeledValue(it.label, "${Format.r(it.meanR)} · ${it.measured} casos")
                }
                Note("Si lo descartado rinde igual que lo ejecutado, ese filtro no aporta.")
            }
        }
    }
}
