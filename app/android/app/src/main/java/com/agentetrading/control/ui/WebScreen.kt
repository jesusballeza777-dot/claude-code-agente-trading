package com.agentetrading.control.ui

import android.annotation.SuppressLint
import android.app.DownloadManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.net.http.SslError
import android.os.Environment
import android.webkit.CookieManager
import android.webkit.SslErrorHandler
import android.webkit.URLUtil
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.background
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import com.agentetrading.control.BuildConfig
import com.agentetrading.control.net.NavigationPolicy

private const val CANVAS = 0xFF04161B.toInt()
private const val ACCENT = 0xFF2DD4BF.toInt()
private const val SURFACE = 0xFF0A242C.toInt()

/**
 * El Centro de Mando dentro de la app: el mismo sitio que en el navegador, con arrastrar para
 * actualizar, botón atrás, descargas de reportes y sin salir nunca del servidor propio.
 * No hay puente JavaScript: la página no puede llamar a código nativo.
 */
@Composable
fun WebScreen(baseUrl: String, lifecycle: Lifecycle, path: String, onOpenSettings: () -> Unit) {
    val context = LocalContext.current
    var progress by remember { mutableFloatStateOf(0f) }
    var failure by remember(baseUrl) { mutableStateOf<String?>(null) }
    var canGoBack by remember(baseUrl) { mutableStateOf(false) }

    val views =
        remember(baseUrl) {
            val refresh = SwipeRefreshLayout(context)
            val web = WebView(context)
            configure(web)
            web.webViewClient =
                object : WebViewClient() {
                    override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean =
                        when (NavigationPolicy.decide(baseUrl, request.url.toString())) {
                            NavigationPolicy.Decision.STAY -> false
                            NavigationPolicy.Decision.SETTINGS -> {
                                onOpenSettings()
                                true
                            }
                            NavigationPolicy.Decision.EXTERNAL -> {
                                openInBrowser(context, request.url)
                                true
                            }
                            NavigationPolicy.Decision.BLOCK -> true
                        }

                    override fun onPageFinished(view: WebView, url: String?) {
                        refresh.isRefreshing = false
                    }

                    override fun doUpdateVisitedHistory(view: WebView, url: String?, isReload: Boolean) {
                        canGoBack = view.canGoBack()
                    }

                    override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
                        if (request.isForMainFrame) failure = "No se pudo cargar el Centro de Mando: ${error.description}."
                    }

                    override fun onReceivedHttpError(view: WebView, request: WebResourceRequest, errorResponse: WebResourceResponse) {
                        if (request.isForMainFrame && errorResponse.statusCode >= 500) {
                            failure = "El servidor respondió con el código ${errorResponse.statusCode}."
                        }
                    }

                    override fun onReceivedSslError(view: WebView, handler: SslErrorHandler, error: SslError) {
                        handler.cancel()
                        failure = "El certificado del servidor no es de confianza."
                    }
                }
            web.webChromeClient =
                object : WebChromeClient() {
                    override fun onProgressChanged(view: WebView, newProgress: Int) {
                        progress = newProgress / 100f
                    }
                }
            web.setDownloadListener { url, userAgent, contentDisposition, mimeType, _ ->
                if (NavigationPolicy.decide(baseUrl, url) == NavigationPolicy.Decision.STAY) {
                    download(context, url, userAgent, contentDisposition, mimeType)
                }
            }
            refresh.setColorSchemeColors(ACCENT)
            refresh.setProgressBackgroundColorSchemeColor(SURFACE)
            refresh.setOnRefreshListener {
                failure = null
                web.reload()
            }
            refresh.addView(web)
            refresh to web
        }
    val (refreshLayout, webView) = views

    LaunchedEffect(baseUrl, path) { webView.loadUrl(baseUrl + path) }
    BackHandler(enabled = canGoBack && failure == null) { webView.goBack() }
    DisposableEffect(webView, lifecycle) {
        // En segundo plano la página se detiene (y con ella el sondeo de En vivo).
        val observer =
            LifecycleEventObserver { _, event ->
                when (event) {
                    Lifecycle.Event.ON_RESUME -> webView.onResume()
                    Lifecycle.Event.ON_PAUSE -> webView.onPause()
                    else -> Unit
                }
            }
        lifecycle.addObserver(observer)
        onDispose {
            lifecycle.removeObserver(observer)
            webView.destroy()
        }
    }

    Box(modifier = Modifier.fillMaxSize()) {
        AndroidView(factory = { refreshLayout }, modifier = Modifier.fillMaxSize())
        if (progress in 0.01f..0.99f && failure == null) {
            LinearProgressIndicator(progress = { progress }, modifier = Modifier.fillMaxWidth())
        }
        failure?.let { message ->
            Column(
                modifier = Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background).padding(32.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp, Alignment.CenterVertically),
            ) {
                Icon(Icons.Filled.Warning, contentDescription = null, tint = MaterialTheme.colorScheme.secondary, modifier = Modifier.size(48.dp))
                Text("Sin conexión con el servidor", style = MaterialTheme.typography.titleLarge)
                Text(
                    message,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                )
                Button(
                    onClick = {
                        failure = null
                        webView.loadUrl(baseUrl + path)
                    },
                ) {
                    Text("Reintentar")
                }
                TextButton(onClick = onOpenSettings) { Text("Servidor y seguridad") }
            }
        }
    }
}

@SuppressLint("SetJavaScriptEnabled")
private fun configure(webView: WebView) {
    webView.setBackgroundColor(CANVAS)
    with(webView.settings) {
        javaScriptEnabled = true // el Centro de Mando es una app React
        domStorageEnabled = true
        allowFileAccess = false
        allowContentAccess = false
        mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
        javaScriptCanOpenWindowsAutomatically = false
        setSupportMultipleWindows(false)
        setGeolocationEnabled(false)
        // La página lo usa para mostrar el enlace a los ajustes de la app.
        userAgentString = "$userAgentString BrujulaAndroid/${BuildConfig.VERSION_NAME}"
    }
}

private fun openInBrowser(context: Context, uri: Uri) {
    try {
        context.startActivity(Intent(Intent.ACTION_VIEW, uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    } catch (_: android.content.ActivityNotFoundException) {
        Toast.makeText(context, "No hay un navegador para abrir el enlace.", Toast.LENGTH_SHORT).show()
    }
}

/** Los reportes (PDF, Excel, CSV) se guardan en Descargas con la sesión de la app. */
private fun download(context: Context, url: String, userAgent: String, contentDisposition: String?, mimeType: String?) {
    val name = URLUtil.guessFileName(url, contentDisposition, mimeType)
    try {
        val request =
            DownloadManager.Request(Uri.parse(url))
                .setTitle(name)
                .addRequestHeader("User-Agent", userAgent)
                .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, name)
        mimeType?.let { request.setMimeType(it) }
        CookieManager.getInstance().getCookie(url)?.let { request.addRequestHeader("Cookie", it) }
        (context.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager).enqueue(request)
        Toast.makeText(context, "Descargando $name…", Toast.LENGTH_SHORT).show()
    } catch (_: SecurityException) {
        Toast.makeText(context, "No se pudo guardar el archivo en Descargas.", Toast.LENGTH_LONG).show()
    } catch (_: IllegalArgumentException) {
        Toast.makeText(context, "No se pudo descargar el archivo.", Toast.LENGTH_LONG).show()
    }
}
