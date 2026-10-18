package ai.tessaris.pilot

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { PilotHome() }
    }
}

@Composable
private fun PilotHome() {
    var mode by remember { mutableStateOf("Personal") }
    var prompt by remember { mutableStateOf("") }
    MaterialTheme {
        Scaffold(topBar = { CenterAlignedTopAppBar(title = { Text("Pilot") }) }) { inset ->
            Column(Modifier.padding(inset).padding(18.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                SingleChoiceSegmentedButtonRow {
                    listOf("Personal", "Workspace", "Boardroom").forEachIndexed { index, label ->
                        SegmentedButton(selected = mode == label, onClick = { mode = label },
                            shape = SegmentedButtonDefaults.itemShape(index, 3)) { Text(label) }
                    }
                }
                Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("Inbox", "Tasks", "Calendar", "TV", "Files", "Devices").forEach { AssistChip(onClick = {}, label = { Text(it) }) }
                }
                Spacer(Modifier.weight(1f))
                Text("Your private Pilot connects directly to the mother you own.")
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(prompt, { prompt = it }, Modifier.weight(1f), placeholder = { Text("Ask Pilot…") })
                    Button(onClick = { prompt = "" }) { Text("Send") }
                }
            }
        }
    }
}
