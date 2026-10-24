package com.agentetrading.control.net

import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import kotlin.concurrent.thread

/**
 * Servidor HTTP mínimo para los tests, solo con `java.net`: el `android.jar` con el que se
 * compilan los tests de Android no incluye `com.sun.net.httpserver`.
 */
class MiniServer(private val handler: (Request) -> Response) : AutoCloseable {
    class Request(val method: String, val path: String, val headers: Map<String, String>, val body: String)

    class Response(val code: Int, val body: String = "", val headers: List<Pair<String, String>> = emptyList())

    private val socket = ServerSocket(0, 10, InetAddress.getByName("127.0.0.1"))
    val port: Int get() = socket.localPort
    val baseUrl: String get() = "http://127.0.0.1:$port"

    @Volatile
    var lastRequest: Request? = null
        private set

    init {
        thread(isDaemon = true, name = "mini-server") {
            while (!socket.isClosed) {
                try {
                    serve(socket.accept())
                } catch (_: java.io.IOException) {
                    // cerrado
                }
            }
        }
    }

    private fun serve(client: Socket) {
        client.use {
            val input = BufferedReader(InputStreamReader(it.getInputStream(), Charsets.ISO_8859_1))
            val (method, path) = (input.readLine() ?: return).split(" ").let { parts -> parts[0] to parts[1] }
            val headers = mutableMapOf<String, String>()
            while (true) {
                val line = input.readLine()
                if (line.isNullOrEmpty()) break
                headers[line.substringBefore(':').trim().lowercase()] = line.substringAfter(':').trim()
            }
            val length = headers["content-length"]?.toIntOrNull() ?: 0
            val body = CharArray(length).also { buffer -> input.read(buffer, 0, length) }.concatToString()
            val request = Request(method, path, headers, body)
            lastRequest = request
            val response = handler(request)
            val payload = response.body.toByteArray(Charsets.UTF_8)
            val head =
                buildString {
                    append("HTTP/1.1 ${response.code} X\r\n")
                    append("Content-Type: application/json\r\nContent-Length: ${payload.size}\r\nConnection: close\r\n")
                    response.headers.forEach { (k, v) -> append("$k: $v\r\n") }
                    append("\r\n")
                }
            it.getOutputStream().apply {
                write(head.toByteArray(Charsets.ISO_8859_1))
                write(payload)
                flush()
            }
        }
    }

    override fun close() = socket.close()
}
