//! Metrics Dashboards

use serde::{Deserialize, Serialize};

/// Dashboard manager
pub struct DashboardManager;

/// Dashboard definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Dashboard {
    pub id: String,
    pub name: String,
    pub description: String,
    pub widgets: Vec<DashboardWidget>,
}

/// Dashboard widget
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DashboardWidget {
    pub id: String,
    pub widget_type: WidgetType,
    pub title: String,
    pub metrics: Vec<String>,
}

/// Widget types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum WidgetType {
    LineChart,
    BarChart,
    Gauge,
    Counter,
    Table,
}

impl DashboardManager {
    pub fn new() -> Self {
        Self
    }
}
