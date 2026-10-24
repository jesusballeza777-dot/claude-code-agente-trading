package com.agentetrading.control.model

import org.json.JSONArray
import org.json.JSONObject

/**
 * Lee las respuestas de la API del Centro de Mando. Si falta un campo obligatorio lanza
 * `JSONException`: el cliente lo trata como "respuesta inesperada" y no inventa nada.
 */
object Parsers {
    fun hoy(json: JSONObject): Hoy =
        Hoy(
            estado = estado(json.getJSONObject("estado")),
            parte = json.getJSONObject("parte_del_dia").let { Parte(it.getString("autor"), it.getString("texto"), it.getBoolean("validado")) },
            cuenta = cuenta(json.getJSONObject("cuenta")),
            posiciones = lista(json.getJSONObject("posiciones")),
            eventosMacro = lista(json.getJSONObject("eventos_macro")),
        )

    fun estado(json: JSONObject): Estado {
        val datos = json.getJSONObject("datos")
        val disponible = datos.getBoolean("disponible")
        return Estado(
            origen = origen(json),
            faseActual = json.getString("fase_actual"),
            fases = json.getJSONArray("fases").objects().map { Fase(it.getString("id"), it.getString("nombre"), it.getString("estado")) },
            liveTrading = json.getBoolean("live_trading"),
            holdoutDesde = json.getJSONObject("holdout").getString("desde"),
            holdoutSellado = json.getJSONObject("holdout").getBoolean("sellado"),
            datosDisponible = disponible,
            ultimaVela = if (disponible) datos.optString("ultima_vela").ifEmpty { null } else null,
            completitud = if (datos.has("completitud")) datos.getDouble("completitud") else null,
            motorEstado = json.getJSONObject("motor_de_riesgo").getString("estado"),
            versionLimites = json.getJSONObject("motor_de_riesgo").getString("version_limites"),
            intentosPrincipales = json.getJSONObject("intentos").getInt("principales"),
            intentosTotal = json.getJSONObject("intentos").getInt("total"),
            pendientes = json.getJSONArray("pendientes_propietario").objects().map { Pendiente(it.getString("tarea"), it.getString("documento")) },
        )
    }

    fun enVivo(json: JSONObject): EnVivo {
        val decisiones = json.getJSONObject("decisiones")
        return EnVivo(
            origen = origen(json),
            horaUtc = json.getString("hora_utc"),
            liveTrading = json.getBoolean("live_trading"),
            motores = json.getJSONArray("motores").objects().map { Motor(it.getString("id"), it.getString("nombre"), it.getString("estado"), it.getString("detalle")) },
            eventos = json.getJSONArray("eventos").objects().map { Evento(it.getString("t"), it.getString("tipo"), it.getString("texto")) },
            totalEventos = json.getInt("total_eventos"),
            decisionesOrigen = origen(decisiones),
            decisionesAviso = decisiones.getString("aviso"),
            decisiones =
                decisiones.getJSONArray("items").objects().map {
                    Decision(
                        t = it.getString("t"),
                        accion = it.getString("accion"),
                        nivel = it.getString("nivel"),
                        motivo = it.getString("motivo"),
                        veto = if (it.isNull("veto")) null else it.getString("veto"),
                    )
                },
        )
    }

    private fun cuenta(json: JSONObject): Cuenta {
        val presupuesto = json.getJSONObject("presupuesto")
        val diario = presupuesto.getJSONObject("diario")
        val semanal = presupuesto.getJSONObject("semanal")
        val umbrales = json.getJSONObject("umbrales")
        return Cuenta(
            origen = origen(json),
            capital = json.getString("capital"),
            maximo = json.getString("maximo"),
            drawdown = json.getDouble("drawdown"),
            parada = umbrales.getDouble("parada"),
            corteDuro = umbrales.getDouble("corte_duro"),
            diario = Presupuesto(diario.getDouble("usado"), diario.getDouble("limite")),
            textoDiario = diario.getString("texto"),
            semanal = Presupuesto(semanal.getDouble("usado"), semanal.getDouble("limite")),
            curva = json.getJSONArray("curva").objects().map { PuntoCurva(it.getString("t"), it.getDouble("capital")) },
        )
    }

    private fun lista(json: JSONObject): Lista = Lista(origen(json), json.getJSONArray("items").length(), json.getString("vacio"))

    private fun origen(json: JSONObject): Origen =
        when (json.getString("origen")) {
            "real" -> Origen.REAL
            "backtest" -> Origen.BACKTEST
            else -> Origen.DEMO // lo desconocido se trata como demostración, nunca como real
        }

    private fun JSONArray.objects(): List<JSONObject> = (0 until length()).map { getJSONObject(it) }
}
