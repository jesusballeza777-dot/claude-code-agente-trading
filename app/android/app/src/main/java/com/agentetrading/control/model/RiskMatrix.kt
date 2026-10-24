package com.agentetrading.control.model

/** Matriz de riesgos probabilidad × impacto del registro de riesgos. */
object RiskMatrix {
    /** El registro escribe la probabilidad en femenino (Alta) y el impacto en masculino (Alto). */
    fun level(text: String): Int =
        when (text.trim().substringBefore(' ')) {
            "Baja", "Bajo" -> 0
            "Media", "Medio" -> 1
            "Alta", "Alto" -> 2
            else -> -1
        }

    class Result(
        /** Filas de probabilidad alta a baja; columnas de impacto bajo a alto. */
        val cells: List<List<List<Riesgo>>>,
        /** Riesgos sin nivel reconocible (por ejemplo "Ocurrido"): se listan aparte, no se descartan. */
        val outside: List<Riesgo>,
    )

    fun build(riesgos: List<Riesgo>): Result =
        Result(
            cells = (2 downTo 0).map { p -> (0..2).map { i -> riesgos.filter { level(it.probabilidad) == p && level(it.impacto) == i } } },
            outside = riesgos.filter { level(it.probabilidad) < 0 || level(it.impacto) < 0 },
        )
}
