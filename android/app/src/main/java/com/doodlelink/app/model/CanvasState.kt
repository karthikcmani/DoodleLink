package com.doodlelink.app.model

sealed interface CanvasAction {
    fun apply(state: CanvasState)
    fun undo(state: CanvasState)
}

data class AddStrokeAction(val stroke: Stroke) : CanvasAction {
    override fun apply(state: CanvasState) {
        if (!state.strokes.contains(stroke)) {
            state.strokes.add(stroke)
        }
    }

    override fun undo(state: CanvasState) {
        state.strokes.remove(stroke)
    }
}

data class ClearCanvasAction(val clearedStrokes: List<Stroke>) : CanvasAction {
    override fun apply(state: CanvasState) {
        state.strokes.clear()
    }

    override fun undo(state: CanvasState) {
        state.strokes.clear()
        state.strokes.addAll(clearedStrokes)
    }
}

/**
 * Manages ordered strokes, pointer lifecycle, undo/redo history, and change notifications.
 * Pure Kotlin logic completely decoupled from Compose UI or networking.
 */
class CanvasState {
    val strokes: MutableList<Stroke> = mutableListOf()
    var activeStroke: Stroke? = null
        private set

    private val undoStack = ArrayDeque<CanvasAction>()
    private val redoStack = ArrayDeque<CanvasAction>()

    val canUndo: Boolean get() = undoStack.isNotEmpty()
    val canRedo: Boolean get() = redoStack.isNotEmpty()
    val strokeCount: Int get() = strokes.size

    private val changeListeners = mutableListOf<() -> Unit>()

    fun addChangeListener(listener: () -> Unit) {
        if (!changeListeners.contains(listener)) {
            changeListeners.add(listener)
        }
    }

    fun removeChangeListener(listener: () -> Unit) {
        changeListeners.remove(listener)
    }

    private fun notifyChange() {
        for (listener in changeListeners) {
            listener()
        }
    }

    // --- Pointer Lifecycle ---

    fun startStroke(
        tool: ToolType = ToolType.PEN,
        color: String = "#000000",
        width: Float = 0.004f,
        startX: Float? = null,
        startY: Float? = null,
        pressure: Float = 1.0f
    ): Stroke {
        val stroke = Stroke(tool = tool, color = color, width = width)
        if (startX != null && startY != null) {
            stroke.addPoint(startX, startY, pressure = pressure)
        }
        activeStroke = stroke
        notifyChange()
        return stroke
    }

    fun appendPoint(
        x: Float,
        y: Float,
        timestamp: Double = System.currentTimeMillis().toDouble(),
        pressure: Float = 1.0f
    ): Point? {
        val active = activeStroke ?: return null
        val pt = active.addPoint(x, y, timestamp, pressure)
        notifyChange()
        return pt
    }

    fun finishStroke(): Stroke? {
        val active = activeStroke ?: return null
        activeStroke = null

        if (active.isEmpty()) {
            notifyChange()
            return null
        }

        strokes.add(active)
        undoStack.addLast(AddStrokeAction(active))
        redoStack.clear()
        notifyChange()
        return active
    }

    fun cancelStroke() {
        if (activeStroke != null) {
            activeStroke = null
            notifyChange()
        }
    }

    fun addRemoteStroke(stroke: Stroke) {
        strokes.add(stroke)
        undoStack.addLast(AddStrokeAction(stroke))
        redoStack.clear()
        notifyChange()
    }

    fun resetStrokes(newStrokes: List<Stroke>) {
        activeStroke = null
        strokes.clear()
        strokes.addAll(newStrokes)
        undoStack.clear()
        redoStack.clear()
        notifyChange()
    }

    // --- History Control ---

    fun undo(): Boolean {
        if (!canUndo) return false
        val action = undoStack.removeLast()
        action.undo(this)
        redoStack.addLast(action)
        notifyChange()
        return true
    }

    fun redo(): Boolean {
        if (!canRedo) return false
        val action = redoStack.removeLast()
        action.apply(this)
        undoStack.addLast(action)
        notifyChange()
        return true
    }

    fun clear(): Boolean {
        if (strokes.isEmpty()) return false
        val action = ClearCanvasAction(strokes.toList())
        action.apply(this)
        undoStack.addLast(action)
        redoStack.clear()
        notifyChange()
        return true
    }
}
