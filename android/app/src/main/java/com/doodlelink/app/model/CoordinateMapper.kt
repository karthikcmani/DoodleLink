package com.doodlelink.app.model

data class ViewportRect(
    val x: Float,
    val y: Float,
    val width: Float,
    val height: Float
) {
    val right: Float get() = x + width
    val bottom: Float get() = y + height

    fun contains(px: Float, py: Float): Boolean {
        return px in x..right && py in y..bottom
    }
}

/**
 * Coordinate mapper translating between physical screen pixels and normalized
 * [0.0, 1.0] whiteboard coordinates. Guarantees 1:1 cross-device aspect ratio alignment.
 */
class CoordinateMapper(
    var logicalAspectRatio: Float? = 16.0f / 9.0f,
    var preserveAspectRatio: Boolean = true
) {
    var viewport: ViewportRect = ViewportRect(0.0f, 0.0f, 1.0f, 1.0f)
        private set

    fun updateScreenSize(screenWidth: Float, screenHeight: Float): ViewportRect {
        val w = screenWidth.coerceAtLeast(1.0f)
        val h = screenHeight.coerceAtLeast(1.0f)

        val targetRatio = logicalAspectRatio
        if (!preserveAspectRatio || targetRatio == null) {
            viewport = ViewportRect(0.0f, 0.0f, w, h)
            return viewport
        }

        val currentRatio = w / h

        viewport = if (currentRatio > targetRatio) {
            // Screen is wider than logical canvas -> pillarbox (left/right margins)
            val viewportH = h
            val viewportW = h * targetRatio
            val viewportX = (w - viewportW) / 2.0f
            ViewportRect(viewportX, 0.0f, viewportW, viewportH)
        } else {
            // Screen is taller than logical canvas -> letterbox (top/bottom margins)
            val viewportW = w
            val viewportH = w / targetRatio
            val viewportY = (h - viewportH) / 2.0f
            ViewportRect(0.0f, viewportY, viewportW, viewportH)
        }

        return viewport
    }

    fun screenToNormalized(screenX: Float, screenY: Float, clamp: Boolean = true): Pair<Float, Float> {
        val vp = viewport
        if (vp.width <= 0f || vp.height <= 0f) return 0.0f to 0.0f

        var normX = (screenX - vp.x) / vp.width
        var normY = (screenY - vp.y) / vp.height

        if (clamp) {
            normX = normX.coerceIn(0.0f, 1.0f)
            normY = normY.coerceIn(0.0f, 1.0f)
        }

        return normX to normY
    }

    fun normalizedToScreen(normX: Float, normY: Float): Pair<Float, Float> {
        val vp = viewport
        val sx = vp.x + normX * vp.width
        val sy = vp.y + normY * vp.height
        return sx to sy
    }

    fun normalizedToPixelWidth(normWidth: Float): Float {
        return (normWidth * viewport.width).coerceAtLeast(1.0f)
    }

    fun pixelToNormalizedWidth(pxWidth: Float): Float {
        val vpW = viewport.width.coerceAtLeast(1.0f)
        return (pxWidth / vpW).coerceAtLeast(0.0001f)
    }
}
