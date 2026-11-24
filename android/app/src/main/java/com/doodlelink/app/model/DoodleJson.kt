package com.doodlelink.app.model

import kotlinx.serialization.json.Json

/**
 * Standard JSON serializer configuration matching Protocol v1 specification.
 * Ensures default fields (such as tool: "pen") are always explicitly encoded for
 * cross-platform compatibility with the Python desktop host.
 */
object DoodleJson {
    val json = Json {
        encodeDefaults = true
        ignoreUnknownKeys = true
        isLenient = true
    }
}
