package com.doodlelink.app.network

enum class ConnectionState {
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    RECONNECTING,
    ERROR;

    val isConnected: Boolean get() = this == CONNECTED
    val isConnectingOrReconnecting: Boolean get() = this == CONNECTING || this == RECONNECTING
}
