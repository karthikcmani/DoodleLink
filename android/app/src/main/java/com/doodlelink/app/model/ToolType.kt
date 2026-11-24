package com.doodlelink.app.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
enum class ToolType {
    @SerialName("pen")
    PEN,

    @SerialName("eraser")
    ERASER;

    companion object {
        fun fromString(value: String): ToolType = when (value.lowercase()) {
            "eraser" -> ERASER
            else -> PEN
        }
    }
}
