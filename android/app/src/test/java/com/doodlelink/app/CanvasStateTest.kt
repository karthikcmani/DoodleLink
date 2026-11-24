package com.doodlelink.app

import com.doodlelink.app.model.CanvasState
import com.doodlelink.app.model.ToolType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class CanvasStateTest {

    @Test
    fun testInitialState() {
        val state = CanvasState()
        assertEquals(0, state.strokeCount)
        assertFalse(state.canUndo)
        assertFalse(state.canRedo)
        assertNull(state.activeStroke)
    }

    @Test
    fun testPointerLifecycleAndCommit() {
        val state = CanvasState()

        val active = state.startStroke(
            tool = ToolType.PEN,
            color = "#2563EB",
            width = 0.005f,
            startX = 0.1f,
            startY = 0.1f
        )
        assertNotNull(state.activeStroke)
        assertEquals(1, active.points.size)

        val pt = state.appendPoint(0.2f, 0.2f)
        assertNotNull(pt)
        assertEquals(2, active.points.size)

        val committed = state.finishStroke()
        assertNotNull(committed)
        assertNull(state.activeStroke)
        assertEquals(1, state.strokeCount)
        assertTrue(state.canUndo)
        assertFalse(state.canRedo)
    }

    @Test
    fun testEmptyStrokeDiscarded() {
        val state = CanvasState()
        state.startStroke()
        val committed = state.finishStroke()
        assertNull(committed)
        assertEquals(0, state.strokeCount)
        assertFalse(state.canUndo)
    }

    @Test
    fun testCancelStroke() {
        val state = CanvasState()
        state.startStroke(startX = 0.5f, startY = 0.5f)
        state.appendPoint(0.6f, 0.6f)
        assertNotNull(state.activeStroke)

        state.cancelStroke()
        assertNull(state.activeStroke)
        assertEquals(0, state.strokeCount)
    }

    @Test
    fun testUndoAndRedo() {
        val state = CanvasState()

        state.startStroke(startX = 0.1f, startY = 0.1f)
        state.finishStroke()
        assertEquals(1, state.strokeCount)

        // Undo
        assertTrue(state.undo())
        assertEquals(0, state.strokeCount)
        assertTrue(state.canRedo)

        // Redo
        assertTrue(state.redo())
        assertEquals(1, state.strokeCount)
        assertFalse(state.canRedo)
    }

    @Test
    fun testClearAndUndoClear() {
        val state = CanvasState()
        assertFalse(state.clear())

        state.startStroke(startX = 0.1f, startY = 0.1f)
        state.finishStroke()
        state.startStroke(startX = 0.2f, startY = 0.2f)
        state.finishStroke()
        assertEquals(2, state.strokeCount)

        assertTrue(state.clear())
        assertEquals(0, state.strokeCount)

        // Undo clear restores both strokes
        assertTrue(state.undo())
        assertEquals(2, state.strokeCount)
    }

    @Test
    fun testResetStrokes() {
        val state = CanvasState()
        state.startStroke(startX = 0.1f, startY = 0.1f)
        state.finishStroke()
        assertEquals(1, state.strokeCount)

        val newStrokes = listOf(
            com.doodlelink.app.model.Stroke(color = "#FF0000"),
            com.doodlelink.app.model.Stroke(color = "#00FF00")
        )
        state.resetStrokes(newStrokes)
        assertEquals(2, state.strokeCount)
        assertFalse(state.canUndo)
        assertFalse(state.canRedo)
        assertNull(state.activeStroke)
    }

    @Test
    fun testChangeListenerCalled() {
        val state = CanvasState()
        var calls = 0
        state.addChangeListener { calls++ }

        state.startStroke(startX = 0.1f, startY = 0.1f)
        state.finishStroke()
        assertTrue(calls > 0)
    }
}
