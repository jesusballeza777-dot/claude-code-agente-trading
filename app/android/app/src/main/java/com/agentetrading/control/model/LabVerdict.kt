package com.agentetrading.control.model

/** El mensaje de Brújula sobre el laboratorio, calculado con los resultados (nada escrito a mano sobre H2). */
object LabVerdict {
    fun text(hipotesis: List<HipotesisLab>): String {
        val evaluadas = hipotesis.filter { it.evaluada && it.resumen != null }
        if (evaluadas.isEmpty()) return "Aún no hay hipótesis evaluadas."
        val pasan = evaluadas.filter { it.gate?.pasa == true }
        if (pasan.isNotEmpty()) {
            return "${pasan.size} hipótesis pasan los criterios 1-8. Falta el holdout, que se abre una sola vez y con tu autorización."
        }
        val cercana = evaluadas.filter { it.gate != null }.maxByOrNull { it.gate?.cumplidos ?: 0 }
        val cerca = cercana?.gate?.let { " ${cercana.id} es la que más se acerca: cumple ${it.cumplidos} de ${it.criterios.size} criterios." }.orEmpty()
        return "Ninguna de las ${evaluadas.size} hipótesis evaluadas pasa el examen.$cerca " +
            "No es un fracaso: es el sistema evitando que arriesgues dinero sin evidencia."
    }
}
