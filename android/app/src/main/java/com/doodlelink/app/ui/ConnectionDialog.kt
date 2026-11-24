package com.doodlelink.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.doodlelink.app.network.ConnectionState
import com.doodlelink.app.viewmodel.DrawingViewModel

@Composable
fun ConnectionDialog(
    viewModel: DrawingViewModel
) {
    if (!viewModel.isConnectDialogOpen) return

    val state = viewModel.connectionState
    val isConnected = state.isConnected

    // 0: Wi-Fi / Hotspot, 1: USB Cable (ADB)
    var selectedTab by remember {
        mutableIntStateOf(if (viewModel.networkClient.host == "127.0.0.1") 1 else 0)
    }
    var wifiHostInput by remember {
        mutableStateOf(
            if (viewModel.networkClient.host.isNotEmpty() && viewModel.networkClient.host != "127.0.0.1") {
                viewModel.networkClient.host
            } else {
                "192.168."
            }
        )
    }
    var usbHostInput by remember { mutableStateOf("127.0.0.1") }
    var portInput by remember { mutableStateOf(viewModel.networkClient.port.toString()) }
    var codeInput by remember { mutableStateOf(viewModel.networkClient.pairingCode) }

    val currentHost = if (selectedTab == 0) wifiHostInput else usbHostInput

    AlertDialog(
        onDismissRequest = { viewModel.closeConnectDialog() },
        containerColor = Color(0xFF1F, 0x29, 0x37),
        shape = RoundedCornerShape(20.dp),
        title = {
            Text(
                text = if (isConnected) "PC Connection Status" else "Connect to Windows PC",
                color = Color.White,
                fontWeight = FontWeight.Bold,
                fontSize = 18.sp
            )
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 4.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                // Status message
                Text(
                    text = "Status: ${viewModel.connectionStatusMessage}",
                    color = when (state) {
                        ConnectionState.CONNECTED -> Color(0xFF10B981)
                        ConnectionState.CONNECTING, ConnectionState.RECONNECTING -> Color(0xFF38BDF8)
                        ConnectionState.ERROR -> Color(0xFFEF4444)
                        ConnectionState.DISCONNECTED -> Color(0xFF9CA3AF)
                    },
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium
                )

                if (!isConnected) {
                    TabRow(
                        selectedTabIndex = selectedTab,
                        containerColor = Color(0xFF11, 0x18, 0x27),
                        contentColor = Color(0xFF38, 0xBD, 0xF8)
                    ) {
                        Tab(
                            selected = selectedTab == 0,
                            onClick = { selectedTab = 0 },
                            text = { Text("Wi-Fi / Hotspot", fontSize = 12.sp) }
                        )
                        Tab(
                            selected = selectedTab == 1,
                            onClick = { selectedTab = 1 },
                            text = { Text("USB (ADB)", fontSize = 12.sp) }
                        )
                    }

                    if (selectedTab == 0) {
                        Card(
                            colors = CardDefaults.cardColors(containerColor = Color(0xFF11, 0x18, 0x27)),
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(8.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                                Text(
                                    "• Wi-Fi: Connect PC & phone to same Wi-Fi. Enter PC IP.",
                                    color = Color(0xFF9CA3AF),
                                    fontSize = 11.sp
                                )
                                Text(
                                    "• Hotspot: Connect PC to phone hotspot. Enter PC's 192.168.43.x IP.",
                                    color = Color(0xFF9CA3AF),
                                    fontSize = 11.sp
                                )
                            }
                        }

                        OutlinedTextField(
                            value = wifiHostInput,
                            onValueChange = { wifiHostInput = it },
                            label = { Text("Desktop PC IP Address") },
                            placeholder = { Text("e.g. 192.168.1.100") },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Text),
                            colors = textFieldColors(),
                            modifier = Modifier.fillMaxWidth()
                        )
                    } else {
                        Card(
                            colors = CardDefaults.cardColors(containerColor = Color(0xFF11, 0x18, 0x27)),
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(8.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                                Text(
                                    "1. Connect phone to PC via USB cable.",
                                    color = Color(0xFF9CA3AF),
                                    fontSize = 11.sp
                                )
                                Text(
                                    "2. Enable USB debugging in Developer Options.",
                                    color = Color(0xFF9CA3AF),
                                    fontSize = 11.sp
                                )
                                Text(
                                    "3. On PC DoodleLink: Click 'Enable ADB Reverse' in USB tab.",
                                    color = Color(0xFF9CA3AF),
                                    fontSize = 11.sp
                                )
                            }
                        }

                        OutlinedTextField(
                            value = usbHostInput,
                            onValueChange = { usbHostInput = it },
                            label = { Text("USB Localhost Address") },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Text),
                            colors = textFieldColors(),
                            modifier = Modifier.fillMaxWidth()
                        )
                    }

                    OutlinedTextField(
                        value = portInput,
                        onValueChange = { portInput = it },
                        label = { Text("Port") },
                        placeholder = { Text("8765") },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        colors = textFieldColors(),
                        modifier = Modifier.fillMaxWidth()
                    )

                    OutlinedTextField(
                        value = codeInput,
                        onValueChange = { if (it.length <= 6) codeInput = it },
                        label = { Text("6-Digit Pairing Code") },
                        placeholder = { Text("123456") },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        colors = textFieldColors(),
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }
        },
        confirmButton = {
            if (isConnected) {
                Button(
                    onClick = {
                        viewModel.disconnectFromHost()
                        viewModel.closeConnectDialog()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFEF4444))
                ) {
                    Text("Disconnect")
                }
            } else {
                Button(
                    onClick = {
                        val port = portInput.toIntOrNull() ?: 8765
                        viewModel.connectToHost(currentHost, port, codeInput)
                    },
                    enabled = currentHost.isNotBlank() && codeInput.length == 6,
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2563EB))
                ) {
                    Text("Connect")
                }
            }
        },
        dismissButton = {
            OutlinedButton(
                onClick = { viewModel.closeConnectDialog() }
            ) {
                Text("Close", color = Color(0xFFD1D5DB))
            }
        }
    )
}

@Composable
private fun textFieldColors() = OutlinedTextFieldDefaults.colors(
    focusedBorderColor = Color(0xFF38BDF8),
    unfocusedBorderColor = Color(0xFF4B5563),
    focusedTextColor = Color.White,
    unfocusedTextColor = Color(0xFFE5E7EB),
    focusedLabelColor = Color(0xFF38BDF8),
    unfocusedLabelColor = Color(0xFF9CA3AF)
)
