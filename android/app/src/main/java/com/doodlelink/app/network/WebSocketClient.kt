package com.doodlelink.app.network

import com.doodlelink.app.model.DoodleJson
import com.doodlelink.app.model.Point
import com.doodlelink.app.model.Stroke
import com.doodlelink.app.model.ToolType
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.serialization.encodeToString
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import java.util.concurrent.TimeUnit

class WebSocketClient(
    private val clientScope: CoroutineScope = CoroutineScope(Dispatchers.IO)
) {
    private val okHttpClient = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.MILLISECONDS) // Keep-alive for websockets
        .build()

    private var webSocket: WebSocket? = null
    private var pingJob: Job? = null
    private var reconnectJob: Job? = null

    var host: String = ""
        private set
    var port: Int = 8765
        private set
    var pairingCode: String = ""
        private set
    var sessionId: String? = null
        private set

    var connectionState: ConnectionState = ConnectionState.DISCONNECTED
        private set(value) {
            field = value
            onStateChanged?.invoke(value, statusMessage)
        }

    var statusMessage: String = "Disconnected"
        private set

    private var userDisconnected: Boolean = false
    private var reconnectAttempts: Int = 0

    // Observer Callbacks
    var onStateChanged: ((ConnectionState, String) -> Unit)? = null
    var onRemoteStrokeStart: ((Stroke) -> Unit)? = null
    var onRemoteStrokePoints: ((String, List<Point>) -> Unit)? = null
    var onRemoteStrokeEnd: ((String) -> Unit)? = null
    var onRemoteStrokeCancel: ((String) -> Unit)? = null
    var onRemoteUndo: (() -> Unit)? = null
    var onRemoteRedo: (() -> Unit)? = null
    var onRemoteClear: (() -> Unit)? = null

    fun connect(targetHost: String, targetPort: Int = 8765, code: String) {
        userDisconnected = false
        sessionId = null
        host = targetHost.trim()
        port = targetPort
        pairingCode = code.trim()

        reconnectJob?.cancel()
        reconnectAttempts = 0
        initiateConnection()
    }

    private fun initiateConnection() {
        if (connectionState == ConnectionState.CONNECTED) return

        statusMessage = "Connecting to $host:$port..."
        connectionState = if (reconnectAttempts > 0) ConnectionState.RECONNECTING else ConnectionState.CONNECTING

        try {
            val url = "ws://$host:$port"
            val request = Request.Builder().url(url).build()

            webSocket?.cancel()
            webSocket = okHttpClient.newWebSocket(request, object : WebSocketListener() {
                override fun onOpen(webSocket: WebSocket, response: Response) {
                    statusMessage = "Connected. Authenticating..."
                    // Send pairing handshake: use active session_id for reconnection if available, else fresh pairing code
                    val pairMsg = if (!sessionId.isNullOrBlank()) {
                        PairRequest(session_id = sessionId)
                    } else {
                        PairRequest(code = pairingCode)
                    }
                    val jsonStr = DoodleJson.json.encodeToString(pairMsg)
                    webSocket.send(jsonStr)
                }

                override fun onMessage(webSocket: WebSocket, text: String) {
                    handleIncomingMessage(text)
                }

                override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                    webSocket.close(1000, null)
                }

                override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                    stopPingTimer()
                    if (!userDisconnected) {
                        scheduleReconnect("Connection closed by host: $reason")
                    } else {
                        statusMessage = "Disconnected"
                        connectionState = ConnectionState.DISCONNECTED
                    }
                }

                override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                    stopPingTimer()
                    val errorMsg = formatErrorMessage(t)
                    if (!userDisconnected) {
                        scheduleReconnect(errorMsg)
                    } else {
                        statusMessage = errorMsg
                        connectionState = ConnectionState.ERROR
                    }
                }
            })
        } catch (e: Exception) {
            scheduleReconnect(formatErrorMessage(e))
        }
    }

    fun formatErrorMessage(t: Throwable): String {
        val msg = t.message ?: t.javaClass.simpleName
        val isUsb = host == "127.0.0.1" || host == "localhost"
        return when {
            t is java.net.ConnectException -> {
                if (isUsb) {
                    "USB connection refused: Ensure 'adb reverse' is enabled on PC"
                } else {
                    "Connection refused: Ensure server is running on $host:$port"
                }
            }
            t is java.net.SocketTimeoutException -> {
                "Connection timed out: Check PC IP and Wi-Fi/Hotspot network"
            }
            t is java.net.NoRouteToHostException -> {
                "No route to host: Ensure phone and PC are on same network"
            }
            else -> msg
        }
    }

    fun disconnect() {
        userDisconnected = true
        sessionId = null
        reconnectJob?.cancel()
        stopPingTimer()
        webSocket?.close(1000, "User disconnected")
        webSocket = null
        statusMessage = "Disconnected"
        connectionState = ConnectionState.DISCONNECTED
    }

    private fun scheduleReconnect(reason: String) {
        if (userDisconnected) return

        reconnectAttempts++
        val backoffSeconds = (reconnectAttempts * 2).coerceAtMost(10)
        statusMessage = "Reconnecting in ${backoffSeconds}s... ($reason)"
        connectionState = ConnectionState.RECONNECTING

        reconnectJob?.cancel()
        reconnectJob = clientScope.launch {
            delay(backoffSeconds * 1000L)
            if (!userDisconnected && isActive) {
                initiateConnection()
            }
        }
    }

    private fun startPingTimer() {
        stopPingTimer()
        pingJob = clientScope.launch {
            while (isActive) {
                delay(10_000L) // 10 second ping interval
                if (connectionState == ConnectionState.CONNECTED) {
                    val ping = HeartbeatEvent(type = "ping")
                    val payload = DoodleJson.json.encodeToString(ping)
                    webSocket?.send(payload)
                }
            }
        }
    }

    private fun stopPingTimer() {
        pingJob?.cancel()
        pingJob = null
    }

    private fun handleIncomingMessage(rawText: String) {
        try {
            val msg = DoodleJson.json.decodeFromString<GenericMessage>(rawText)

            when (msg.type) {
                "pair_success" -> {
                    sessionId = msg.session_id
                    reconnectAttempts = 0
                    statusMessage = "Connected to $host"
                    connectionState = ConnectionState.CONNECTED
                    startPingTimer()
                }
                "error" -> {
                    statusMessage = msg.message ?: "Server error (${msg.code})"
                    if (msg.code == "INVALID_PAIRING_CODE") {
                        sessionId = null
                        userDisconnected = true // Don't loop reconnect on bad credentials
                        connectionState = ConnectionState.ERROR
                    }
                }
                "stroke_start" -> {
                    val pts = msg.points ?: emptyList()
                    val stroke = Stroke(
                        id = msg.stroke_id ?: "",
                        tool = ToolType.fromString(msg.tool ?: "pen"),
                        color = msg.color ?: "#000000",
                        width = msg.width ?: 0.004f,
                        points = pts.toMutableList()
                    )
                    onRemoteStrokeStart?.invoke(stroke)
                }
                "stroke_points" -> {
                    val sId = msg.stroke_id ?: return
                    val pts = msg.points ?: return
                    onRemoteStrokePoints?.invoke(sId, pts)
                }
                "stroke_end" -> {
                    onRemoteStrokeEnd?.invoke(msg.stroke_id ?: "")
                }
                "stroke_cancel" -> {
                    onRemoteStrokeCancel?.invoke(msg.stroke_id ?: "")
                }
                "undo" -> onRemoteUndo?.invoke()
                "redo" -> onRemoteRedo?.invoke()
                "clear_canvas" -> onRemoteClear?.invoke()
                "ping" -> {
                    val pong = HeartbeatEvent(type = "pong")
                    webSocket?.send(DoodleJson.json.encodeToString(pong))
                }
                "pong" -> {
                    // Heartbeat acknowledged
                }
            }
        } catch (_: Exception) {
            // Ignore malformed messages safely
        }
    }

    // --- Outbound Drawing Event Dispatchers ---

    fun sendStrokeStart(stroke: Stroke, sequence: Int) {
        if (connectionState != ConnectionState.CONNECTED) return
        val event = StrokeStartEvent(
            session_id = sessionId,
            stroke_id = stroke.id,
            sequence = sequence,
            tool = stroke.tool.name.lowercase(),
            color = stroke.color,
            width = stroke.width,
            points = stroke.points.toList()
        )
        webSocket?.send(DoodleJson.json.encodeToString(event))
    }

    fun sendStrokePoints(strokeId: String, points: List<Point>, sequence: Int) {
        if (connectionState != ConnectionState.CONNECTED || points.isEmpty()) return
        val event = StrokePointsEvent(
            session_id = sessionId,
            stroke_id = strokeId,
            sequence = sequence,
            points = points
        )
        webSocket?.send(DoodleJson.json.encodeToString(event))
    }

    fun sendStrokeEnd(strokeId: String, sequence: Int) {
        if (connectionState != ConnectionState.CONNECTED) return
        val event = StrokeLifecycleEvent(
            type = "stroke_end",
            session_id = sessionId,
            stroke_id = strokeId,
            sequence = sequence
        )
        webSocket?.send(DoodleJson.json.encodeToString(event))
    }

    fun sendStrokeCancel(strokeId: String, sequence: Int) {
        if (connectionState != ConnectionState.CONNECTED) return
        val event = StrokeLifecycleEvent(
            type = "stroke_cancel",
            session_id = sessionId,
            stroke_id = strokeId,
            sequence = sequence
        )
        webSocket?.send(DoodleJson.json.encodeToString(event))
    }

    fun sendUndo(sequence: Int) {
        if (connectionState != ConnectionState.CONNECTED) return
        val event = ActionEvent(type = "undo", session_id = sessionId, sequence = sequence)
        webSocket?.send(DoodleJson.json.encodeToString(event))
    }

    fun sendRedo(sequence: Int) {
        if (connectionState != ConnectionState.CONNECTED) return
        val event = ActionEvent(type = "redo", session_id = sessionId, sequence = sequence)
        webSocket?.send(DoodleJson.json.encodeToString(event))
    }

    fun sendClear(sequence: Int) {
        if (connectionState != ConnectionState.CONNECTED) return
        val event = ActionEvent(type = "clear_canvas", session_id = sessionId, sequence = sequence)
        webSocket?.send(DoodleJson.json.encodeToString(event))
    }
}
