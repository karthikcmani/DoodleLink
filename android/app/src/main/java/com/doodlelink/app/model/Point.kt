package com.doodlelink.app.model

import kotlinx.serialization.Serializable

/**
 * A normalized coordinate point within the logical whiteboard [0.0, 1.0] x [0.0, 1.0].
 */
@Serializable
data class Point(
    val x: Float,
    val y: Float,
    val timestamp: Double = System.currentTimeMillis().toDouble(),
    val pressure: Float = 1.0f
) {
    init {
        require(x in -0.05f..1.05f) { "Normalized x ($x) out of tolerance" }
        require(y in -0.05f..1.05f) { "Normalized y ($y) out of tolerance" }
    }

    /**
     * Clamped point strictly within [0.0, 1.0].
     */
    fun clamped(): Point = copy(
        x = x.coerceIn(0.0f, 1.0f),
        y = y.coerceIn(0.0f, 1.0f),
        pressure = pressure.coerceIn(0.0f, 1.0f)
    )
}
