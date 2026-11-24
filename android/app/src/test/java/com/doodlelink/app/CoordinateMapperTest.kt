package com.doodlelink.app

import com.doodlelink.app.model.CoordinateMapper
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CoordinateMapperTest {

    @Test
    fun testPillarboxWideScreen() {
        // Screen 2400x900 with 16:9 target -> pillarbox (margins on left and right)
        val mapper = CoordinateMapper(logicalAspectRatio = 16.0f / 9.0f, preserveAspectRatio = true)
        val vp = mapper.updateScreenSize(2400f, 900f)

        assertEquals(900f, vp.height, 0.01f)
        assertEquals(1600f, vp.width, 0.01f)
        assertEquals(400f, vp.x, 0.01f)
        assertEquals(0f, vp.y, 0.01f)

        // Center of screen (1200, 450) maps to normalized (0.5, 0.5)
        val (nx, ny) = mapper.screenToNormalized(1200f, 450f)
        assertEquals(0.5f, nx, 0.001f)
        assertEquals(0.5f, ny, 0.001f)

        // Left viewport border (400, 0) maps to (0.0, 0.0)
        val (leftNx, topNy) = mapper.screenToNormalized(400f, 0f)
        assertEquals(0.0f, leftNx, 0.001f)
        assertEquals(0.0f, topNy, 0.001f)
    }

    @Test
    fun testLetterboxTallScreen() {
        // Screen 1080x2400 (typical 20:9 phone portrait) with 16:9 logical canvas
        val mapper = CoordinateMapper(logicalAspectRatio = 16.0f / 9.0f, preserveAspectRatio = true)
        val vp = mapper.updateScreenSize(1080f, 2400f)

        assertEquals(1080f, vp.width, 0.01f)
        val expectedHeight = 1080f / (16f / 9f) // 607.5
        assertEquals(expectedHeight, vp.height, 0.01f)
        assertTrue(vp.y > 0f)

        // Center of viewport maps to (0.5, 0.5)
        val centerY = vp.y + vp.height / 2.0f
        val (nx, ny) = mapper.screenToNormalized(540f, centerY)
        assertEquals(0.5f, nx, 0.001f)
        assertEquals(0.5f, ny, 0.001f)
    }

    @Test
    fun testRoundtripMapping() {
        val mapper = CoordinateMapper()
        mapper.updateScreenSize(1920f, 1080f)

        val points = listOf(
            0.0f to 0.0f,
            1.0f to 1.0f,
            0.5f to 0.5f,
            0.25f to 0.75f,
            0.8f to 0.2f
        )

        for ((origX, origY) in points) {
            val (sx, sy) = mapper.normalizedToScreen(origX, origY)
            val (nx, ny) = mapper.screenToNormalized(sx, sy)
            assertEquals(origX, nx, 0.0001f)
            assertEquals(origY, ny, 0.0001f)
        }
    }

    @Test
    fun testWidthConversions() {
        val mapper = CoordinateMapper()
        mapper.updateScreenSize(1000f, 600f)

        val normWidth = mapper.pixelToNormalizedWidth(8.0f)
        val pxWidth = mapper.normalizedToPixelWidth(normWidth)
        assertEquals(8.0f, pxWidth, 0.01f)
    }
}
