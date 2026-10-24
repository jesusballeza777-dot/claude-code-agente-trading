package com.agentetrading.control.ui

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.scale
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentetrading.control.model.Origen

/** Franjas diagonales: lo que es demostración se distingue sin depender del color (igual que la web). */
fun Modifier.demoStripes(): Modifier =
    drawBehind {
        val step = 28.dp.toPx()
        val color = Palette.Demo.copy(alpha = 0.10f)
        var x = -size.height
        while (x < size.width) {
            drawLine(color, Offset(x, size.height), Offset(x + size.height, 0f), strokeWidth = 8.dp.toPx())
            x += step
        }
    }

/** Tarjeta con título, el sello de origen de los datos y, si es demostración, franjas. */
@Composable
fun InfoCard(
    title: String,
    modifier: Modifier = Modifier,
    subtitle: String? = null,
    origin: Origen? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
    ) {
        Column(
            modifier = (if (origin == Origen.DEMO) Modifier.demoStripes() else Modifier).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    if (subtitle != null) {
                        Text(subtitle, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                if (origin != null) OriginChip(origin)
            }
            content()
        }
    }
}

@Composable
fun OriginChip(origin: Origen) {
    val (label, color) =
        when (origin) {
            Origen.REAL -> "Datos reales" to MaterialTheme.colorScheme.primary
            Origen.BACKTEST -> "Backtest 2020-2024" to MaterialTheme.colorScheme.onSurfaceVariant
            Origen.DEMO -> "DATOS DE DEMOSTRACIÓN" to Palette.Demo
        }
    Row(
        modifier =
            Modifier
                .clip(RoundedCornerShape(50))
                .background(if (origin == Origen.DEMO) Palette.DemoSoft else Color.Transparent)
                .padding(horizontal = 8.dp, vertical = 3.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        if (origin == Origen.DEMO) Icon(Icons.Filled.Warning, contentDescription = null, tint = color, modifier = Modifier.size(12.dp))
        Text(label, color = color, fontSize = 10.sp, fontWeight = FontWeight.Bold)
    }
}

/** Fila de estado: etiqueta pequeña, valor y un punto de color (nunca solo color: el texto lo dice). */
@Composable
fun StatusRow(label: String, value: String, tone: Tone) {
    Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Box(modifier = Modifier.size(10.dp).clip(CircleShape).background(tone.color()))
        Column(modifier = Modifier.weight(1f)) {
            Text(label.uppercase(), fontSize = 10.sp, letterSpacing = 0.8.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

enum class Tone {
    GOOD,
    WARN,
    BAD,
    NEUTRAL,
}

@Composable
fun Tone.color(): Color =
    when (this) {
        Tone.GOOD -> Palette.Gain
        Tone.WARN -> Palette.Warn
        Tone.BAD -> Palette.Loss
        Tone.NEUTRAL -> Palette.Neutral
    }

@Composable
fun BigStat(label: String, value: String, modifier: Modifier = Modifier, tone: Color = MaterialTheme.colorScheme.onSurface) {
    Column(modifier = modifier) {
        Text(label.uppercase(), fontSize = 10.sp, letterSpacing = 0.8.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, fontSize = 20.sp, fontWeight = FontWeight.SemiBold, color = tone)
    }
}

/** Curva de capital: línea con relleno degradado. Sin ejes: la cifra exacta está en el texto. */
@Composable
fun Sparkline(values: List<Double>, modifier: Modifier = Modifier) {
    val line = MaterialTheme.colorScheme.primary
    Canvas(modifier = modifier.fillMaxWidth().height(96.dp)) {
        if (values.size < 2) return@Canvas
        val min = values.min()
        val span = (values.max() - min).takeIf { it > 0 } ?: 1.0
        val dx = size.width / (values.size - 1)
        fun y(v: Double) = (size.height * (1 - (v - min) / span)).toFloat()
        val path = Path().apply { values.forEachIndexed { i, v -> if (i == 0) moveTo(0f, y(v)) else lineTo(i * dx, y(v)) } }
        val fill = Path().apply {
            addPath(path)
            lineTo(size.width, size.height)
            lineTo(0f, size.height)
            close()
        }
        drawPath(fill, Brush.verticalGradient(listOf(line.copy(alpha = 0.35f), Color.Transparent)))
        drawPath(path, line, style = Stroke(width = 2.5.dp.toPx(), cap = StrokeCap.Round))
    }
}

/** Medidor de drawdown con las marcas de parada y corte duro. */
@Composable
fun DrawdownGauge(value: Double, halt: Double, hard: Double, scale: Double = 0.25) {
    val animated by animateFloatAsState((value / scale).coerceIn(0.0, 1.0).toFloat(), tween(700), label = "drawdown")
    Column {
        Box(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .height(14.dp)
                    .clip(RoundedCornerShape(50))
                    .background(MaterialTheme.colorScheme.surfaceVariant)
                    .drawBehind {
                        drawRect(Color(0xFF2DD4BF), size = androidx.compose.ui.geometry.Size(size.width * animated, size.height))
                        drawRect(Palette.Warn, Offset(size.width * (halt / scale).toFloat(), 0f), androidx.compose.ui.geometry.Size(2.dp.toPx(), size.height))
                        drawRect(Palette.Loss, Offset(size.width * (hard / scale).toFloat(), 0f), androidx.compose.ui.geometry.Size(2.dp.toPx(), size.height))
                    },
        )
        Row(modifier = Modifier.fillMaxWidth().padding(top = 4.dp), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("0%", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text("parada ${(halt * 100).toInt()}%", fontSize = 11.sp, color = Palette.Warn)
            Text("corte ${(hard * 100).toInt()}%", fontSize = 11.sp, color = Palette.Loss)
        }
    }
}

@Composable
fun BudgetBar(label: String, used: Double, limit: Double, usedText: String, limitText: String) {
    val share = if (limit > 0) (used / limit).coerceIn(0.0, 1.0).toFloat() else 0f
    val animated by animateFloatAsState(share, tween(700), label = "presupuesto")
    val color = if (share < 0.5f) MaterialTheme.colorScheme.primary else if (share < 0.9f) Palette.Warn else Palette.Loss
    Column {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(label, style = MaterialTheme.typography.bodyMedium)
            Text("$usedText de $limitText", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Box(modifier = Modifier.padding(top = 4.dp).fillMaxWidth().height(10.dp).clip(RoundedCornerShape(50)).background(MaterialTheme.colorScheme.surfaceVariant)) {
            Box(modifier = Modifier.fillMaxWidth(animated).height(10.dp).clip(RoundedCornerShape(50)).background(color))
        }
    }
}

/** Punto que late: el sistema responde. Con la pausa del teléfono se queda quieto. */
@Composable
fun PulseDot(active: Boolean, color: Color) {
    val transition = rememberInfiniteTransition(label = "pulso")
    val ring by transition.animateFloat(1f, 2.6f, infiniteRepeatable(tween(1800), RepeatMode.Restart), label = "anillo")
    val fade by transition.animateFloat(0.6f, 0f, infiniteRepeatable(tween(1800), RepeatMode.Restart), label = "desvanece")
    Box(contentAlignment = Alignment.Center, modifier = Modifier.size(28.dp)) {
        if (active) Box(modifier = Modifier.size(12.dp).scale(ring).alpha(fade).clip(CircleShape).background(color))
        Box(modifier = Modifier.size(12.dp).clip(CircleShape).background(color))
    }
}

@Composable
fun LoadingBox() {
    Box(modifier = Modifier.fillMaxWidth().padding(48.dp), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
}

@Composable
fun ErrorBox(message: String, onRetry: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Icon(Icons.Filled.Warning, contentDescription = null, tint = Palette.Warn, modifier = Modifier.size(40.dp))
        Text("Sin conexión con el servidor", style = MaterialTheme.typography.titleMedium)
        Text(message, textAlign = TextAlign.Center, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Button(onClick = onRetry) { Text("Reintentar") }
    }
}

/** Aviso cuando se pierde la conexión pero aún hay datos que mostrar. */
@Composable
fun OfflineBanner(message: String) {
    Row(
        modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(Palette.DemoSoft).padding(12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Icon(Icons.Filled.Warning, contentDescription = null, tint = Palette.Demo, modifier = Modifier.size(18.dp))
        Text("Sin conexión. Mostrando lo último recibido. $message", style = MaterialTheme.typography.bodySmall)
    }
}

/** Aviso de una función que solo existe con servidor: dice por qué y lleva a conectarlo. */
@Composable
fun NeedsServerBox(message: String) {
    val openSettings = LocalOpenSettings.current
    Column(
        modifier = Modifier.fillMaxWidth().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Necesita tu servidor", style = MaterialTheme.typography.titleMedium)
        Text(message, textAlign = TextAlign.Center, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Button(onClick = openSettings) { Text("Conectar mi servidor") }
    }
}

/** Franja fija del modo sin servidor: de dónde salen los datos que se ven. */
@Composable
fun LocalBanner(text: String, onConnect: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().background(Palette.DemoSoft).padding(horizontal = 14.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(text, fontSize = 11.sp, modifier = Modifier.weight(1f))
        androidx.compose.material3.TextButton(onClick = onConnect) { Text("Conectar", fontSize = 12.sp) }
    }
}
