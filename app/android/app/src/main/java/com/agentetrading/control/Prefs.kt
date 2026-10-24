package com.agentetrading.control

import android.content.Context
import com.agentetrading.control.net.NoteStore
import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject

/** Preferencias locales. No guardan secretos: la dirección del servidor y dos interruptores. */
class Prefs(context: Context) {
    private val store = context.getSharedPreferences("brujula", Context.MODE_PRIVATE)

    var serverUrl: String?
        get() = store.getString(KEY_URL, null)
        set(value) {
            store.edit().putString(KEY_URL, value).apply()
        }

    /** Modo sin servidor: la app usa los datos que lleva dentro (ADR-018). Conectar un servidor lo apaga. */
    var useLocal: Boolean
        get() = store.getBoolean(KEY_LOCAL, false)
        set(value) {
            store.edit().putBoolean(KEY_LOCAL, value).apply()
        }

    /** Pedir huella, rostro o PIN al abrir y al volver tras un minuto fuera. */
    var lockEnabled: Boolean
        get() = store.getBoolean(KEY_LOCK, true)
        set(value) {
            store.edit().putBoolean(KEY_LOCK, value).apply()
        }

    /** Ocultar la app en apps recientes y bloquear capturas de pantalla. */
    var secureScreen: Boolean
        get() = store.getBoolean(KEY_SECURE, true)
        set(value) {
            store.edit().putBoolean(KEY_SECURE, value).apply()
        }

    private companion object {
        const val KEY_URL = "server_url"
        const val KEY_LOCAL = "use_local"
        const val KEY_LOCK = "lock_enabled"
        const val KEY_SECURE = "secure_screen"
    }
}

/** Notas del diario sin servidor: se quedan en este teléfono, en el almacenamiento privado de la app. */
class PrefsNoteStore(context: Context) : NoteStore {
    private val store = context.getSharedPreferences("brujula_notas", Context.MODE_PRIVATE)

    override fun all(): List<JSONObject> = read().let { array -> (0 until array.length()).map { array.getJSONObject(it) } }

    override fun add(note: JSONObject) {
        store.edit().putString(KEY, read().put(note).toString()).apply()
    }

    private fun read(): JSONArray =
        try {
            JSONArray(store.getString(KEY, "[]"))
        } catch (_: JSONException) {
            JSONArray()
        }

    private companion object {
        const val KEY = "notas"
    }
}
