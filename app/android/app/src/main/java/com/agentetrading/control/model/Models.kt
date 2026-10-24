package com.agentetrading.control.model

/** De dónde salen los datos que se muestran: nunca se mezcla demostración con realidad sin rotular. */
enum class Origen {
    REAL,
    BACKTEST,
    DEMO,
}

data class Fase(val id: String, val nombre: String, val estado: String)

data class Pendiente(val tarea: String, val documento: String)

data class Estado(
    val origen: Origen,
    val faseActual: String,
    val fases: List<Fase>,
    val liveTrading: Boolean,
    val holdoutDesde: String,
    val holdoutSellado: Boolean,
    val datosDisponible: Boolean,
    val ultimaVela: String?,
    val completitud: Double?,
    val motorEstado: String,
    val versionLimites: String,
    val intentosPrincipales: Int,
    val intentosTotal: Int,
    val pendientes: List<Pendiente>,
)

data class PuntoCurva(val t: String, val capital: Double)

data class Presupuesto(val usado: Double, val limite: Double)

data class Cuenta(
    val origen: Origen,
    /** Decimales como texto: se muestran tal cual los entrega el servidor. */
    val capital: String,
    val maximo: String,
    val drawdown: Double,
    val parada: Double,
    val corteDuro: Double,
    val diario: Presupuesto,
    val textoDiario: String,
    val semanal: Presupuesto,
    val curva: List<PuntoCurva>,
)

data class Parte(val autor: String, val texto: String, val validado: Boolean)

/** Lista que hoy está vacía (posiciones, eventos macro) con la explicación de por qué. */
data class Lista(val origen: Origen, val cantidad: Int, val vacio: String)

data class Hoy(
    val estado: Estado,
    val parte: Parte,
    val cuenta: Cuenta,
    val posiciones: Lista,
    val eventosMacro: Lista,
)

data class Motor(val id: String, val nombre: String, val estado: String, val detalle: String) {
    val activo: Boolean get() = estado == "activo"
}

data class Evento(val t: String, val tipo: String, val texto: String)

data class Decision(val t: String, val accion: String, val nivel: String, val motivo: String, val veto: String?)

data class EnVivo(
    val origen: Origen,
    val horaUtc: String,
    val liveTrading: Boolean,
    val motores: List<Motor>,
    val eventos: List<Evento>,
    val totalEventos: Int,
    val decisionesOrigen: Origen,
    val decisionesAviso: String,
    val decisiones: List<Decision>,
)
