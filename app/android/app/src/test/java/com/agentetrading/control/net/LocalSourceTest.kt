package com.agentetrading.control.net

import com.agentetrading.control.model.LabParsers
import com.agentetrading.control.model.PageParsers
import com.agentetrading.control.model.Parsers
import java.time.Instant
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class LocalSourceTest {
    private class MemoryNotes : NoteStore {
        val saved = mutableListOf<JSONObject>()

        override fun all(): List<JSONObject> = saved.toList()

        override fun add(note: JSONObject) {
            saved += note
        }
    }

    /** La instantánea real se llama distinto a las respuestas de ejemplo de los tests: se mapean. */
    private val sample =
        mapOf("laboratorio-h2-v1.json" to "laboratorio-h2.json", "manifest.json" to null)

    private fun asset(name: String): String? {
        if (name == "manifest.json") return """{"generado_utc":"2026-10-24T05:00:00Z","commit":"abc123def456"}"""
        val resource = sample[name] ?: name
        return javaClass.classLoader!!.getResourceAsStream(resource)?.bufferedReader()?.use { it.readText() }
    }

    private val notes = MemoryNotes()
    private val source = LocalSource(::asset, notes, clock = { Instant.parse("2026-10-24T05:30:00.987Z") })

    private fun ok(path: String): JSONObject = (source.get(path) as ApiClient.Result.Ok).json

    @Test
    fun everyPageThatDoesNotNeedAServerIsServedAndParses() {
        Parsers.hoy(ok("/api/hoy"))
        Parsers.enVivo(ok("/api/en-vivo"))
        PageParsers.limites(ok("/api/riesgo/limites"))
        PageParsers.vetos(ok("/api/riesgo/vetos"))
        PageParsers.decisiones(ok("/api/decisiones"))
        PageParsers.diario(ok("/api/diario"))
        PageParsers.proyecto(ok("/api/proyecto"))
        PageParsers.reportes(ok("/api/reportes"))
        assertEquals(5, LabParsers.laboratorio(ok("/api/laboratorio")).hipotesis.size)
        assertEquals("H2-v1", LabParsers.detalle(ok("/api/laboratorio/H2-v1")).id)
    }

    @Test
    fun queryStringsAreIgnored() {
        assertTrue(source.get("/api/laboratorio?x=1") is ApiClient.Result.Ok)
    }

    @Test
    fun whatNeedsAServerSaysSoInsteadOfInventingNumbers() {
        val calculator = source.get("/api/riesgo/calculadora?simbolo=BTCUSDT&entrada=60000&stop=58800")
        assertEquals(LocalSource.NEEDS_ENGINE, (calculator as ApiClient.Result.NeedsServer).message)
        assertTrue(source.get("/api/mercado/velas?simbolo=BTCUSDT") is ApiClient.Result.NeedsServer)
        assertTrue(source.get("/api/mercado/simbolos") is ApiClient.Result.NeedsServer)
        assertTrue(source.post("/api/sesion", JSONObject()) is ApiClient.Result.NeedsServer)
    }

    @Test
    fun unknownRoutesAndUnsafeIdsAreRefused() {
        assertTrue(source.get("/api/nada") is ApiClient.Result.Failed)
        assertTrue(source.get("/api/laboratorio/../hoy") is ApiClient.Result.Failed)
        assertTrue(source.get("/api/laboratorio/H9-v9") is ApiClient.Result.Failed) // sin archivo
    }

    @Test
    fun aBuildWithoutTheSnapshotSaysSo() {
        val empty = LocalSource({ null }, notes)
        val result = empty.get("/api/hoy")
        assertTrue((result as ApiClient.Result.Failed).message.contains("no incluye"))
        assertNull(empty.manifest())
    }

    @Test
    fun notesStayOnThePhoneAndAppearInTheJournalAfterTheSnapshotOnes() {
        val saved = source.post("/api/diario/notas", JSONObject().put("referencia", " H2-v1 ").put("texto", "  Revisar el PBO  "))
        val note = (saved as ApiClient.Result.Ok).json
        assertEquals("Revisar el PBO", note.getString("texto"))
        assertEquals("H2-v1", note.getString("referencia"))
        assertEquals("2026-10-24T05:30:00Z", note.getString("fecha_utc"))
        assertEquals(12, note.getString("id").length)
        source.post("/api/diario/notas", JSONObject().put("texto", "Segunda"))
        val diario = PageParsers.diario(ok("/api/diario"))
        assertEquals(listOf("Revisar el PBO", "Segunda"), diario.notas.map { it.texto }.takeLast(2))
        assertEquals(2, notes.saved.size)
    }

    @Test
    fun invalidNotesAreRejectedAndNotStored() {
        assertTrue(source.post("/api/diario/notas", JSONObject().put("texto", "   ")) is ApiClient.Result.Failed)
        assertTrue(source.post("/api/diario/notas", JSONObject().put("texto", "x".repeat(2_001))) is ApiClient.Result.Failed)
        assertTrue(source.post("/api/diario/notas", JSONObject().put("texto", "ok").put("referencia", "r".repeat(81))) is ApiClient.Result.Failed)
        assertTrue(notes.saved.isEmpty())
    }

    @Test
    fun manifestSaysWhenAndFromWhichCommit() {
        assertEquals("2026-10-24T05:00:00Z" to "abc123def456", source.manifest())
    }
}
