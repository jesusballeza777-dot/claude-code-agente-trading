package com.agentetrading.control.ui

import android.app.DownloadManager
import android.content.Context
import android.net.Uri
import android.os.Environment
import android.webkit.CookieManager
import android.widget.Toast

/** Guarda un reporte en Descargas con la sesión de la app (la cookie que dejó el inicio de sesión). */
fun downloadFile(context: Context, url: String, fileName: String, mimeType: String?, userAgent: String? = null) {
    try {
        val request =
            DownloadManager.Request(Uri.parse(url))
                .setTitle(fileName)
                .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, fileName)
        userAgent?.let { request.addRequestHeader("User-Agent", it) }
        mimeType?.let { request.setMimeType(it) }
        CookieManager.getInstance().getCookie(url)?.let { request.addRequestHeader("Cookie", it) }
        (context.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager).enqueue(request)
        Toast.makeText(context, "Descargando $fileName…", Toast.LENGTH_SHORT).show()
    } catch (_: SecurityException) {
        Toast.makeText(context, "No se pudo guardar el archivo en Descargas.", Toast.LENGTH_LONG).show()
    } catch (_: IllegalArgumentException) {
        Toast.makeText(context, "No se pudo descargar el archivo.", Toast.LENGTH_LONG).show()
    }
}
