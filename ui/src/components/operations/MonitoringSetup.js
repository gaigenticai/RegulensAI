import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  IconButton,
  Tooltip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import {
  MonitorHeart,
  Timeline,
  Notifications,
  Security,
  Speed,
  Storage,
  ExpandMore,
  ContentCopy,
  PlayArrow,
  CheckCircle,
  Error,
  Warning,
  Settings,
  Dashboard,
  Email,
  Sms,
  Webhook
} from '@mui/icons-material';

const MonitoringSetup = () => {
  const [monitoringConfig, setMonitoringConfig] = useState({
    prometheus: { enabled: true, status: 'healthy' },
    grafana: { enabled: true, status: 'healthy' },
    alertmanager: { enabled: true, status: 'healthy' },
    jaeger: { enabled: false, status: 'disabled' }
  });
  const [alertRules, setAlertRules] = useState([]);
  const [notificationChannels, setNotificationChannels] = useState([]);
  const [activeAlerts, setActiveAlerts] = useState([]);
  const [businessMetrics, setBusinessMetrics] = useState(null);
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [showDashboardDialog, setShowDashboardDialog] = useState(false);
  const [showAlertsDialog, setShowAlertsDialog] = useState(false);
  const [selectedComponent, setSelectedComponent] = useState(null);
  const [selectedDashboard, setSelectedDashboard] = useState(null);

  useEffect(() => {
    fetchMonitoringStatus();
    fetchAlertRules();
    fetchNotificationChannels();
    fetchActiveAlerts();
    fetchBusinessMetrics();

    // Set up periodic updates
    const interval = setInterval(() => {
      fetchActiveAlerts();
      fetchBusinessMetrics();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const fetchMonitoringStatus = async () => {
    try {
      const response = await fetch('/api/v1/operations/monitoring/status');
      if (response.ok) {
        const data = await response.json();
        setMonitoringConfig(data);
      }
    } catch (error) {
      console.error('Failed to fetch monitoring status:', error);
    }
  };

  const fetchAlertRules = async () => {
    try {
      const response = await fetch('/api/v1/operations/monitoring/alerts');
      if (response.ok) {
        const data = await response.json();
        setAlertRules(data);
      }
    } catch (error) {
      console.error('Failed to fetch alert rules:', error);
    }
  };

  const fetchNotificationChannels = async () => {
    try {
      const response = await fetch('/api/v1/operations/monitoring/notifications');
      if (response.ok) {
        const data = await response.json();
        setNotificationChannels(data);
      }
    } catch (error) {
      console.error('Failed to fetch notification channels:', error);
    }
  };

  const fetchActiveAlerts = async () => {
    try {
      const response = await fetch('/api/v1/operations/alerts/active');
      if (response.ok) {
        const data = await response.json();
        setActiveAlerts(data.alerts || []);
      }
    } catch (error) {
      console.error('Failed to fetch active alerts:', error);
    }
  };

  const fetchBusinessMetrics = async () => {
    try {
      const response = await fetch('/api/v1/operations/metrics/business');
      if (response.ok) {
        const data = await response.json();
        setBusinessMetrics(data);
      }
    } catch (error) {
      console.error('Failed to fetch business metrics:', error);
    }
  };

  const availableDashboards = [
    {
      id: 'executive-overview',
      name: 'Executive Overview',
      description: 'High-level business metrics and system health',
      icon: <Dashboard />,
      metrics: ['System Health', 'Compliance Score', 'User Activity', 'Uptime'],
      url: '/grafana/d/executive-overview'
    },
    {
      id: 'technical-operations',
      name: 'Technical Operations',
      description: 'Infrastructure metrics and performance monitoring',
      icon: <MonitorHeart />,
      metrics: ['CPU/Memory Usage', 'Database Performance', 'API Metrics', 'Network I/O'],
      url: '/grafana/d/technical-operations'
    },
    {
      id: 'regulensai-application',
      name: 'Application Metrics',
      description: 'RegulensAI-specific business logic and user interactions',
      icon: <Psychology />,
      metrics: ['Training Portal', 'Compliance Tasks', 'Document Processing', 'AI Services'],
      url: '/grafana/d/regulensai-application'
    },
    {
      id: 'alerting-overview',
      name: 'Alerting Overview',
      description: 'Real-time alerts and incident management',
      icon: <Notifications />,
      metrics: ['Active Alerts', 'Resolution Times', 'Escalation Status', 'MTTD/MTTR'],
      url: '/grafana/d/alerting-overview'
    }
  ];

  const monitoringComponents = [
    {
      name: 'Prometheus',
      description: 'Metrics collection and storage',
      icon: <Timeline />,
      status: monitoringConfig.prometheus?.status || 'unknown',
      enabled: monitoringConfig.prometheus?.enabled || false,
      setupCommands: [
        'helm repo add prometheus-community https://prometheus-community.github.io/helm-charts',
        'helm repo update',
        'helm install prometheus prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace'
      ]
    },
    {
      name: 'Grafana',
      description: 'Metrics visualization and dashboards',
      icon: <Dashboard />,
      status: monitoringConfig.grafana?.status || 'unknown',
      enabled: monitoringConfig.grafana?.enabled || false,
      setupCommands: [
        'kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring',
        'kubectl get secret prometheus-grafana -n monitoring -o jsonpath="{.data.admin-password}" | base64 --decode'
      ]
    },
    {
      name: 'AlertManager',
      description: 'Alert routing and notification management',
      icon: <Notifications />,
      status: monitoringConfig.alertmanager?.status || 'unknown',
      enabled: monitoringConfig.alertmanager?.enabled || false,
      setupCommands: [
        'kubectl apply -f monitoring/alertmanager-config.yaml',
        'kubectl rollout restart deployment/prometheus-kube-prometheus-alertmanager -n monitoring'
      ]
    },
    {
      name: 'Jaeger',
      description: 'Distributed tracing and performance monitoring',
      icon: <Speed />,
      status: monitoringConfig.jaeger?.status || 'unknown',
      enabled: monitoringConfig.jaeger?.enabled || false,
      setupCommands: [
        'helm repo add jaegertracing https://jaegertracing.github.io/helm-charts',
        'helm install jaeger jaegertracing/jaeger --namespace monitoring'
      ]
    }
  ];

  const defaultAlertRules = [
    {
      name: 'High CPU Usage',
      severity: 'warning',
      condition: 'cpu_usage > 80%',
      description: 'Alert when CPU usage exceeds 80%',
      enabled: true
    },
    {
      name: 'High Memory Usage',
      severity: 'warning',
      condition: 'memory_usage > 85%',
      description: 'Alert when memory usage exceeds 85%',
      enabled: true
    },
    {
      name: 'Database Connection Failures',
      severity: 'critical',
      condition: 'db_connection_failures > 5',
      description: 'Alert when database connection failures exceed 5 per minute',
      enabled: true
    },
    {
      name: 'API Response Time',
      severity: 'warning',
      condition: 'api_response_time > 2s',
      description: 'Alert when API response time exceeds 2 seconds',
      enabled: true
    },
    {
      name: 'Pod Restart Rate',
      severity: 'warning',
      condition: 'pod_restarts > 3',
      description: 'Alert when pod restarts exceed 3 per hour',
      enabled: true
    }
  ];

  const notificationChannelTypes = [
    { type: 'email', icon: <Email />, label: 'Email' },
    { type: 'slack', icon: <Webhook />, label: 'Slack' },
    { type: 'webhook', icon: <Webhook />, label: 'Webhook' },
    { type: 'sms', icon: <Sms />, label: 'SMS' }
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return 'success';
      case 'warning': return 'warning';
      case 'error': return 'error';
      case 'disabled': return 'default';
      default: return 'default';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy': return <CheckCircle color="success" />;
      case 'warning': return <Warning color="warning" />;
      case 'error': return <Error color="error" />;
      default: return <Settings />;
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const configureComponent = (component) => {
    setSelectedComponent(component);
    setShowConfigDialog(true);
  };

  const acknowledgeAlert = async (alertId) => {
    try {
      const response = await fetch(`/api/v1/operations/alerts/${alertId}/acknowledge`, {
        method: 'POST'
      });
      if (response.ok) {
        await fetchActiveAlerts();
      }
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
    }
  };

  const openDashboard = (dashboard) => {
    setSelectedDashboard(dashboard);
    setShowDashboardDialog(true);
  };

  return (
    <Box>
      {/* Quick Stats */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="primary">
                {activeAlerts.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Active Alerts
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="success.main">
                {businessMetrics?.compliance?.completion_rate?.toFixed(1) || 0}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Compliance Rate
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="info.main">
                {businessMetrics?.users?.active_users_24h || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Active Users (24h)
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="warning.main">
                {businessMetrics?.training?.avg_completion_rate?.toFixed(1) || 0}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Training Completion
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Dashboards Section */}
      <Typography variant="h6" gutterBottom>
        Monitoring Dashboards
      </Typography>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        {availableDashboards.map((dashboard) => (
          <Grid item xs={12} md={6} key={dashboard.id}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  {dashboard.icon}
                  <Typography variant="h6">{dashboard.name}</Typography>
                </Box>

                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {dashboard.description}
                </Typography>

                <Box sx={{ mb: 2 }}>
                  {dashboard.metrics.map((metric, index) => (
                    <Chip
                      key={index}
                      label={metric}
                      size="small"
                      sx={{ mr: 0.5, mb: 0.5 }}
                    />
                  ))}
                </Box>

                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button
                    size="small"
                    variant="contained"
                    onClick={() => openDashboard(dashboard)}
                    startIcon={<Dashboard />}
                  >
                    Open Dashboard
                  </Button>
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={() => window.open(dashboard.url, '_blank')}
                  >
                    Grafana
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Active Alerts Section */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          Active Alerts ({activeAlerts.length})
        </Typography>
        <Button
          startIcon={<Notifications />}
          onClick={() => setShowAlertsDialog(true)}
          variant="outlined"
        >
          View All Alerts
        </Button>
      </Box>

      {activeAlerts.length > 0 ? (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          {activeAlerts.slice(0, 4).map((alert, index) => (
            <Grid item xs={12} md={6} key={index}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Typography variant="subtitle2">{alert.alertname}</Typography>
                    <Chip
                      label={alert.severity.toUpperCase()}
                      color={alert.severity === 'critical' ? 'error' : 'warning'}
                      size="small"
                    />
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {alert.summary}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Started: {new Date(alert.startsAt).toLocaleString()}
                  </Typography>
                  <Box sx={{ mt: 1 }}>
                    <Button
                      size="small"
                      onClick={() => acknowledgeAlert(alert.alertname)}
                    >
                      Acknowledge
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      ) : (
        <Alert severity="success" sx={{ mb: 3 }}>
          No active alerts - all systems operating normally
        </Alert>
      )}

      {/* Monitoring Components Overview */}
      <Typography variant="h6" gutterBottom>
        Monitoring Components
      </Typography>
      
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {monitoringComponents.map((component) => (
          <Grid item xs={12} md={6} key={component.name}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {component.icon}
                    <Typography variant="h6">{component.name}</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {getStatusIcon(component.status)}
                    <Chip
                      label={component.status.toUpperCase()}
                      color={getStatusColor(component.status)}
                      size="small"
                    />
                  </Box>
                </Box>
                
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {component.description}
                </Typography>
                
                <FormControlLabel
                  control={
                    <Switch
                      checked={component.enabled}
                      onChange={() => {/* Handle toggle */}}
                    />
                  }
                  label="Enabled"
                  sx={{ mb: 1 }}
                />
                
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={() => configureComponent(component)}
                  >
                    Configure
                  </Button>
                  <Button
                    size="small"
                    startIcon={<PlayArrow />}
                    disabled={component.status === 'healthy'}
                  >
                    Deploy
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Alert Rules Configuration */}
      <Accordion sx={{ mb: 2 }}>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Alert Rules Configuration</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <List>
            {defaultAlertRules.map((rule, index) => (
              <ListItem key={index}>
                <ListItemIcon>
                  <Chip
                    label={rule.severity.toUpperCase()}
                    color={rule.severity === 'critical' ? 'error' : 'warning'}
                    size="small"
                  />
                </ListItemIcon>
                <ListItemText
                  primary={rule.name}
                  secondary={`${rule.description} (${rule.condition})`}
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={rule.enabled}
                      onChange={() => {/* Handle toggle */}}
                    />
                  }
                  label="Enabled"
                />
              </ListItem>
            ))}
          </List>
          
          <Alert severity="info" sx={{ mt: 2 }}>
            Alert rules are automatically configured when you deploy the monitoring stack. 
            You can customize these rules by editing the Prometheus configuration.
          </Alert>
        </AccordionDetails>
      </Accordion>

      {/* Notification Channels */}
      <Accordion sx={{ mb: 2 }}>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Notification Channels</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            {notificationChannelTypes.map((channel) => (
              <Grid item xs={12} md={6} key={channel.type}>
                <Card variant="outlined">
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      {channel.icon}
                      <Typography variant="subtitle2">{channel.label}</Typography>
                    </Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      Configure {channel.label.toLowerCase()} notifications for alerts
                    </Typography>
                    <Button size="small" variant="outlined">
                      Configure
                    </Button>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Setup Commands */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Setup Commands</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="subtitle2" gutterBottom>
            Complete Monitoring Stack Setup
          </Typography>
          
          {[
            {
              name: 'Install Prometheus Stack',
              command: 'helm repo add prometheus-community https://prometheus-community.github.io/helm-charts && helm repo update && helm install prometheus prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace --values monitoring/values.yaml'
            },
            {
              name: 'Configure Grafana Dashboards',
              command: 'kubectl apply -f monitoring/grafana-dashboards.yaml'
            },
            {
              name: 'Setup Alert Rules',
              command: 'kubectl apply -f monitoring/alert-rules.yaml'
            },
            {
              name: 'Configure Notification Channels',
              command: 'kubectl apply -f monitoring/alertmanager-config.yaml'
            },
            {
              name: 'Verify Installation',
              command: 'kubectl get pods -n monitoring && kubectl get svc -n monitoring'
            }
          ].map((cmd, index) => (
            <Card key={index} variant="outlined" sx={{ mb: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="subtitle2">{cmd.name}</Typography>
                  <Tooltip title="Copy Command">
                    <IconButton size="small" onClick={() => copyToClipboard(cmd.command)}>
                      <ContentCopy fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
                <Box sx={{ 
                  backgroundColor: 'grey.100', 
                  p: 1, 
                  borderRadius: 1, 
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  overflow: 'auto'
                }}>
                  {cmd.command}
                </Box>
              </CardContent>
            </Card>
          ))}
        </AccordionDetails>
      </Accordion>

      {/* Dashboard Dialog */}
      <Dialog open={showDashboardDialog} onClose={() => setShowDashboardDialog(false)} maxWidth="lg" fullWidth>
        <DialogTitle>
          {selectedDashboard?.name} Dashboard
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            {selectedDashboard?.description}
          </Typography>

          <Alert severity="info" sx={{ mb: 2 }}>
            This dashboard provides real-time monitoring of {selectedDashboard?.name.toLowerCase()} metrics.
            Click "Open in Grafana" for the full interactive experience.
          </Alert>

          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="h6" gutterBottom>
              Dashboard Preview
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Key Metrics: {selectedDashboard?.metrics.join(', ')}
            </Typography>
            <Button
              variant="contained"
              size="large"
              onClick={() => window.open(selectedDashboard?.url, '_blank')}
              startIcon={<Dashboard />}
            >
              Open in Grafana
            </Button>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowDashboardDialog(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Alerts Dialog */}
      <Dialog open={showAlertsDialog} onClose={() => setShowAlertsDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          Active Alerts ({activeAlerts.length})
        </DialogTitle>
        <DialogContent>
          {activeAlerts.length > 0 ? (
            <List>
              {activeAlerts.map((alert, index) => (
                <ListItem key={index}>
                  <ListItemIcon>
                    {alert.severity === 'critical' ?
                      <Error color="error" /> :
                      <Warning color="warning" />
                    }
                  </ListItemIcon>
                  <ListItemText
                    primary={alert.alertname}
                    secondary={
                      <Box>
                        <Typography variant="body2">{alert.summary}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          Started: {new Date(alert.startsAt).toLocaleString()}
                        </Typography>
                      </Box>
                    }
                  />
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Chip
                      label={alert.severity.toUpperCase()}
                      color={alert.severity === 'critical' ? 'error' : 'warning'}
                      size="small"
                    />
                    <Button
                      size="small"
                      onClick={() => acknowledgeAlert(alert.alertname)}
                    >
                      Acknowledge
                    </Button>
                  </Box>
                </ListItem>
              ))}
            </List>
          ) : (
            <Alert severity="success">
              No active alerts - all systems operating normally
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowAlertsDialog(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Configuration Dialog */}
      <Dialog open={showConfigDialog} onClose={() => setShowConfigDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          Configure {selectedComponent?.name}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            {selectedComponent?.description}
          </Typography>
          
          <Typography variant="subtitle2" gutterBottom>
            Setup Commands:
          </Typography>
          
          {selectedComponent?.setupCommands.map((command, index) => (
            <Card key={index} variant="outlined" sx={{ mb: 1 }}>
              <CardContent sx={{ py: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="body2">Step {index + 1}</Typography>
                  <Tooltip title="Copy Command">
                    <IconButton size="small" onClick={() => copyToClipboard(command)}>
                      <ContentCopy fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
                <Box sx={{ 
                  backgroundColor: 'grey.100', 
                  p: 1, 
                  borderRadius: 1, 
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  overflow: 'auto'
                }}>
                  {command}
                </Box>
              </CardContent>
            </Card>
          ))}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowConfigDialog(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default MonitoringSetup;
