package com.agentetrading.control.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

/** Mismos colores que el tema oscuro del Centro de Mando web (app/web/src/styles/index.css). */
private val Scheme =
    darkColorScheme(
        primary = Color(0xFF2DD4BF),
        onPrimary = Color(0xFF04161B),
        secondary = Color(0xFFF5B54A),
        background = Color(0xFF04161B),
        onBackground = Color(0xFFE4F1F1),
        surface = Color(0xFF0A242C),
        onSurface = Color(0xFFE4F1F1),
        surfaceVariant = Color(0xFF0F3039),
        onSurfaceVariant = Color(0xFF9DB7BA),
        outline = Color(0xFF1D4652),
        error = Color(0xFFFB8B8B),
    )

/** Colores con significado, iguales a los de la web: ganancia, pérdida, alerta, neutral y demostración. */
object Palette {
    val Gain = Color(0xFF4ADE9B)
    val Loss = Color(0xFFFB8B8B)
    val Warn = Color(0xFFF5C35A)
    val Demo = Color(0xFFF5B54A)
    val DemoSoft = Color(0xFF3A2A10)
    val Neutral = Color(0xFF9AABB1)
    val AccentSoft = Color(0xFF0D3D3D)
}

@Composable
fun BrujulaTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = Scheme, content = content)
}
