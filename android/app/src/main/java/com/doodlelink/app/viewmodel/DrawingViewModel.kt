package com.doodlelink.app.viewmodel

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.doodlelink.app.model.CanvasState
import com.doodlelink.app.model.CoordinateMapper
import com.doodlelink.app.model.Stroke
import com.doodlelink.app.model.ToolType
import com.doodlelink.app.network.ConnectionState
import com.doodlelink.app.network.WebSocketClient

class DrawingViewModel : ViewModel() {
    val canvasState = CanvasState()
    val coordMapper = CoordinateMapper()
    val networkClient = WebSocketClient(viewModelScope)

    var currentTool by mutableStateOf(ToolType.PEN)
        private set

    var currentColor by mutableStateOf("#111827")
        private set

    var penThicknessPx by mutableStateOf(6.0f)
        private set

    var eraserThicknessPx by mutableStateOf(32.0f)
        private set

    var isFullScreen by mutableStateOf(false)
        private set

    var isConnectDialogOpen by mutableStateOf(false)
        private set

    var connectionState by mutableStateOf(ConnectionState.DISCONNECTED)
        private set

    var connectionStatusMessage by mutableStateOf("Disconnected")
        private set

    var stateVersion by mutableIntStateOf(0)
        private set

    private var isHandlingRemote = false
    private var sequence = 0

    init {
        canvasState.addChangeListener {
            stateVersion++
        }

        setupNetworkObservers()
    }

    private fun setupNetworkObservers() {
        networkClient.onStateChanged = { state, msg ->
            connectionState = state
            connectionStatusMessage = msg
            stateVersion++
        }

        networkClient.onRemoteStrokeStart = { stroke ->
            isHandlingRemote = true
            try {
                val localStroke = canvasState.startStroke(
                    tool = stroke.tool,
                    color = stroke.color,
                    width = stroke.width
                )
                // Append start points if any
                for (p in stroke.points) {
                    canvasState.appendPoint(p.x, p.y, p.timestamp, p.pressure)
                }
            } finally {
                isHandlingRemote = false
            }
        }

        networkClient.onRemoteStrokePoints = { _, pts ->
            isHandlingRemote = true
            try {
                for (p in pts) {
                    canvasState.appendPoint(p.x, p.y, p.timestamp, p.pressure)
                }
            } finally {
                isHandlingRemote = false
            }
        }

        networkClient.onRemoteStrokeEnd = {
            isHandlingRemote = true
            try {
                canvasState.finishStroke()
            } finally {
                isHandlingRemote = false
            }
        }

        networkClient.onRemoteStrokeCancel = {
            isHandlingRemote = true
            try {
                canvasState.cancelStroke()
            } finally {
                isHandlingRemote = false
            }
        }

        networkClient.onRemoteUndo = {
            isHandlingRemote = true
            try {
                canvasState.undo()
            } finally {
                isHandlingRemote = false
            }
        }

        networkClient.onRemoteRedo = {
            isHandlingRemote = true
            try {
                canvasState.redo()
            } finally {
                isHandlingRemote = false
            }
        }

        networkClient.onRemoteClear = {
            isHandlingRemote = true
            try {
                canvasState.clear()
            } finally {
                isHandlingRemote = false
            }
        }
    }

    val activeThicknessPx: Float
        get() = if (currentTool == ToolType.ERASER) eraserThicknessPx else penThicknessPx

    fun selectTool(tool: ToolType) {
        currentTool = tool
    }

    fun selectColor(hex: String) {
        currentColor = if (hex.startsWith("#")) hex else "#$hex"
    }

    fun setPenThickness(px: Float) {
        penThicknessPx = px.coerceIn(1.0f, 64.0f)
    }

    fun setEraserThickness(px: Float) {
        eraserThicknessPx = px.coerceIn(4.0f, 128.0f)
    }

    fun toggleFullScreen() {
        isFullScreen = !isFullScreen
    }

    fun openConnectDialog() {
        isConnectDialogOpen = true
    }

    fun closeConnectDialog() {
        isConnectDialogOpen = false
    }

    fun connectToHost(host: String, port: Int, code: String) {
        networkClient.connect(host, port, code)
    }

    fun disconnectFromHost() {
        networkClient.disconnect()
    }

    // --- Outbound Drawing Dispatches ---

    fun onLocalStrokeStart(startX: Float, startY: Float, pressure: Float = 1.0f): Stroke {
        val normWidth = coordMapper.pixelToNormalizedWidth(activeThicknessPx)
        val color = if (currentTool == ToolType.PEN) currentColor else "#FFFFFF"

        val stroke = canvasState.startStroke(
            tool = currentTool,
            color = color,
            width = normWidth,
            startX = startX,
            startY = startY,
            pressure = pressure
        )

        if (!isHandlingRemote && networkClient.connectionState.isConnected) {
            networkClient.sendStrokeStart(stroke, ++sequence)
        }
        return stroke
    }

    fun onLocalPointAppend(x: Float, y: Float, pressure: Float = 1.0f) {
        val active = canvasState.activeStroke ?: return
        val pt = canvasState.appendPoint(x, y, pressure = pressure)
        if (!isHandlingRemote && pt != null && networkClient.connectionState.isConnected) {
            networkClient.sendStrokePoints(active.id, listOf(pt), ++sequence)
        }
    }

    fun onLocalStrokeFinish() {
        val activeId = canvasState.activeStroke?.id
        val stroke = canvasState.finishStroke()
        if (!isHandlingRemote && stroke != null && activeId != null && networkClient.connectionState.isConnected) {
            networkClient.sendStrokeEnd(activeId, ++sequence)
        }
    }

    fun onLocalStrokeCancel() {
        val activeId = canvasState.activeStroke?.id
        canvasState.cancelStroke()
        if (!isHandlingRemote && activeId != null && networkClient.connectionState.isConnected) {
            networkClient.sendStrokeCancel(activeId, ++sequence)
        }
    }

    fun undo() {
        if (canvasState.undo() && !isHandlingRemote && networkClient.connectionState.isConnected) {
            networkClient.sendUndo(++sequence)
        }
    }

    fun redo() {
        if (canvasState.redo() && !isHandlingRemote && networkClient.connectionState.isConnected) {
            networkClient.sendRedo(++sequence)
        }
    }

    fun clear() {
        if (canvasState.clear() && !isHandlingRemote && networkClient.connectionState.isConnected) {
            networkClient.sendClear(++sequence)
        }
    }
}
