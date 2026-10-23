package com.agentetrading.control.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.unit.dp
import com.agentetrading.control.model.TaxReportInfo
import com.agentetrading.control.ui.components.LabeledValue
import com.agentetrading.control.ui.components.Note
import com.agentetrading.control.ui.components.SectionCard

@Composable
fun ReportsScreen(report: TaxReportInfo) {
    LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            SectionCard("Reporte fiscal ${report.year}") {
                LabeledValue("Operaciones reales", report.liveTrades.toString())
                Button(onClick = {}, enabled = false) { Text("Descargar CSV") }
                Note("Disponible cuando el backend esté en marcha (F6).")
                Note(report.note)
            }
        }
        item {
            SectionCard("Columnas del CSV") {
                report.columns.forEach { Note(it) }
            }
        }
    }
}
