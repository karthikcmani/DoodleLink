package com.doodlelink.app.viewmodel

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import com.doodlelink.app.model.CanvasState
import com.doodlelink.app.model.CoordinateMapper
import com.doodlelink.app.model.ToolType

class DrawingViewModel : ViewModel() {
    val canvasState = CanvasState()
    val coordMapper = CoordinateMapper()

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

    // Drives recomposition on canvas state mutations
    var stateVersion by mutableIntStateOf(0)
        private set

    init {
        canvasState.addChangeListener {
            stateVersion++
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

    fun undo() {
        canvasState.undo()
    }

    fun redo() {
        canvasState.redo()
    }

    fun clear() {
        canvasState.clear()
    }
}
