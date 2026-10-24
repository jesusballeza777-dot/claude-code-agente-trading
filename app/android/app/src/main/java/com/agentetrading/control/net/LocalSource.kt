package com.agentetrading.control.net

import java.time.Instant
import java.time.temporal.ChronoUnit
import java.util.UUID
import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject

/** Dónde se guardan las notas del diario cuando no hay servidor: solo en este teléfono. */
interface NoteStore {
    fun all(): List<JSONObject>

    fun add(note: JSONObject)
}

/**
 * Modo sin servidor (ADR-018): responde con la instantánea que lleva la app (los resultados
 * reales de la F4, el estado del proyecto, los límites y los documentos, generados por la CI con
 * la misma API) y guarda las notas en el teléfono.
 *
 * Lo que de verdad necesita un servidor (el motor de riesgo, los 200 MB de datos de mercado y los
 * reportes) devuelve `NeedsServer`: nunca inventa cifras.
 */
class LocalSource(
    private val readAsset: (String) -> String?,
    private val notes: NoteStore,
    private val clock: () -> Instant = { Instant.now() },
) : DataSource {
    /** Cuándo y con qué commit se generó la instantánea, o null si esta compilación no la incluye. */
    fun manifest(): Pair<String, String>? = read("manifest")?.let { it.optString("generado_utc") to it.optString("commit") }

    override fun get(path: String): ApiClient.Result {
        val route = path.substringBefore('?')
        return when {
            route.startsWith("/api/riesgo/calculadora") -> ApiClient.Result.NeedsServer(NEEDS_ENGINE)
            route.startsWith("/api/mercado/") -> ApiClient.Result.NeedsServer(NEEDS_MARKET)
            else -> {
                val file = fileFor(route) ?: return ApiClient.Result.Failed("Esta pantalla no tiene datos incluidos en la app.")
                val json = read(file) ?: return ApiClient.Result.Failed("Esta compilación de la app no incluye los datos del modo sin servidor.")
                ApiClient.Result.Ok(if (route == "/api/diario") withLocalNotes(json) else json)
            }
        }
    }

    override fun post(path: String, body: JSONObject): ApiClient.Result {
        if (path != "/api/diario/notas") return ApiClient.Result.NeedsServer(NEEDS_SERVER)
        val text = body.optString("texto").trim()
        val reference = body.optString("referencia").trim()
        if (text.isEmpty() || text.length > MAX_NOTE || reference.length > MAX_REFERENCE) {
            return ApiClient.Result.Failed("La nota debe tener entre 1 y 2,000 caracteres.")
        }
        val note =
            JSONObject()
                .put("id", UUID.randomUUID().toString().replace("-", "").take(12))
                .put("fecha_utc", clock().truncatedTo(ChronoUnit.SECONDS).toString())
                .put("referencia", reference)
                .put("texto", text)
        notes.add(note)
        return ApiClient.Result.Ok(note)
    }

    private fun fileFor(route: String): String? =
        when {
            route in FILES -> FILES.getValue(route)
            route.startsWith("/api/laboratorio/") -> route.removePrefix("/api/laboratorio/").takeIf { SAFE_ID.matches(it) }?.let { "laboratorio-${it.lowercase()}" }
            else -> null
        }

    private fun withLocalNotes(diario: JSONObject): JSONObject {
        val merged = JSONArray()
        diario.optJSONArray("notas")?.let { existing -> for (i in 0 until existing.length()) merged.put(existing.get(i)) }
        notes.all().forEach { merged.put(it) }
        return diario.put("notas", merged)
    }

    private fun read(name: String): JSONObject? =
        readAsset("$name.json")?.let {
            try {
                JSONObject(it)
            } catch (_: JSONException) {
                null
            }
        }

    companion object {
        const val NEEDS_SERVER = "Esto necesita tu servidor. Conéctalo en Ajustes → Servidor."
        const val NEEDS_ENGINE = "La calculadora usa el motor de riesgo, que corre en tu servidor. Conéctalo en Ajustes → Servidor."
        const val NEEDS_MARKET = "Los datos de mercado (unos 200 MB) viven en tu servidor. Conéctalo en Ajustes → Servidor para ver las velas."
        const val NEEDS_REPORTS = "Los reportes se generan en tu servidor. Conéctalo en Ajustes → Servidor para descargarlos."
        private const val MAX_NOTE = 2_000
        private const val MAX_REFERENCE = 80
        private val SAFE_ID = Regex("[A-Za-z0-9-]{1,30}")
        private val FILES =
            mapOf(
                "/api/hoy" to "hoy",
                "/api/en-vivo" to "en-vivo",
                "/api/riesgo/limites" to "limites",
                "/api/riesgo/vetos" to "vetos",
                "/api/decisiones" to "decisiones",
                "/api/diario" to "diario",
                "/api/proyecto" to "proyecto",
                "/api/reportes" to "reportes",
                "/api/laboratorio" to "laboratorio",
            )
    }
}
