package com.agentetrading.control.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import com.agentetrading.control.data.DashboardRepository
import com.agentetrading.control.data.DemoRepository
import com.agentetrading.control.ui.components.DemoBanner
import com.agentetrading.control.ui.screens.ControlsScreen
import com.agentetrading.control.ui.screens.DecisionsScreen
import com.agentetrading.control.ui.screens.LearningScreen
import com.agentetrading.control.ui.screens.ReportsScreen
import com.agentetrading.control.ui.screens.SummaryScreen

enum class Tab(
    val label: String,
    val icon: ImageVector,
) {
    SUMMARY("Resumen", Icons.Filled.Home),
    DECISIONS("Decisiones", Icons.AutoMirrored.Filled.List),
    LEARNING("Aprendizaje", Icons.Filled.Star),
    REPORTS("Reportes", Icons.Filled.DateRange),
    CONTROLS("Controles", Icons.Filled.Lock),
}

@Composable
fun App(repository: DashboardRepository = DemoRepository) {
    var selected by rememberSaveable { mutableStateOf(Tab.SUMMARY) }
    Scaffold(
        bottomBar = {
            NavigationBar {
                Tab.entries.forEach { tab ->
                    NavigationBarItem(
                        selected = selected == tab,
                        onClick = { selected = tab },
                        icon = { Icon(tab.icon, contentDescription = tab.label) },
                        label = { Text(tab.label) },
                    )
                }
            }
        },
    ) { innerPadding ->
        Column(modifier = Modifier.padding(innerPadding).fillMaxSize()) {
            if (repository.isDemo) DemoBanner()
            when (selected) {
                Tab.SUMMARY -> SummaryScreen(repository.summary())
                Tab.DECISIONS -> DecisionsScreen(repository.decisions(), repository.isDemo)
                Tab.LEARNING -> LearningScreen(repository.learning(), repository.isDemo)
                Tab.REPORTS -> ReportsScreen(repository.taxReport())
                Tab.CONTROLS -> ControlsScreen()
            }
        }
    }
}
