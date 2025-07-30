import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  LinearProgress,
  IconButton,
  Alert
} from '@mui/material';
import {
  CheckCircle,
  Error,
  Warning,
  Refresh,
  Storage,
  Memory,
  Speed,
  Cloud,
  Security,
  Api
} from '@mui/icons-material';

const SystemHealth = () => {
  const [systemStatus, setSystemStatus] = useState({
    overall: 'healthy',
    services: [
      { name: 'API Gateway', status: 'healthy', uptime: '99.9%', responseTime: '45ms' },
      { name: 'Database', status: 'healthy', uptime: '99.8%', responseTime: '12ms' },
      { name: 'Authentication Service', status: 'healthy', uptime: '99.9%', responseTime: '23ms' },
      { name: 'Training Portal', status: 'healthy', uptime: '99.7%', responseTime: '67ms' },
      { name: 'AI/ML Services', status: 'warning', uptime: '98.5%', responseTime: '234ms' },
      { name: 'Regulatory Monitor', status: 'healthy', uptime: '99.6%', responseTime: '89ms' }
    ],
    metrics: {
      cpuUsage: 45,
      memoryUsage: 67,
      diskUsage: 34,
      networkLatency: 23
    },
    alerts: [
      { id: 1, type: 'warning', message: 'AI/ML service response time above threshold', time: '5 minutes ago' },
      { id: 2, type: 'info', message: 'Database backup completed successfully', time: '1 hour ago' },
      { id: 3, type: 'success', message: 'Security scan completed - no issues found', time: '2 hours ago' }
    ]
  });

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return 'success';
      case 'warning': return 'warning';
      case 'error': return 'error';
      default: return 'default';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy': return <CheckCircle color="success" />;
      case 'warning': return <Warning color="warning" />;
      case 'error': return <Error color="error" />;
      default: return <CheckCircle />;
    }
  };

  const getAlertIcon = (type) => {
    switch (type) {
      case 'error': return <Error color="error" />;
      case 'warning': return <Warning color="warning" />;
      case 'success': return <CheckCircle color="success" />;
      default: return <CheckCircle color="info" />;
    }
  };

  const refreshStatus = () => {
    // Simulate refresh
            // Refreshing system status
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          System Health
        </Typography>
        <IconButton onClick={refreshStatus}>
          <Refresh />
        </IconButton>
      </Box>

      {/* Overall Status */}
      <Alert 
        severity={systemStatus.overall === 'healthy' ? 'success' : 'warning'} 
        sx={{ mb: 3 }}
      >
        <Typography variant="h6">
          System Status: {systemStatus.overall === 'healthy' ? 'All Systems Operational' : 'Some Issues Detected'}
        </Typography>
      </Alert>

      {/* System Metrics */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Speed color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">CPU Usage</Typography>
              </Box>
              <Typography variant="h4" gutterBottom>
                {systemStatus.metrics.cpuUsage}%
              </Typography>
              <LinearProgress 
                variant="determinate" 
                value={systemStatus.metrics.cpuUsage} 
                color={systemStatus.metrics.cpuUsage > 80 ? 'error' : 'primary'}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Memory color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Memory Usage</Typography>
              </Box>
              <Typography variant="h4" gutterBottom>
                {systemStatus.metrics.memoryUsage}%
              </Typography>
              <LinearProgress 
                variant="determinate" 
                value={systemStatus.metrics.memoryUsage} 
                color={systemStatus.metrics.memoryUsage > 80 ? 'error' : 'primary'}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Storage color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Disk Usage</Typography>
              </Box>
              <Typography variant="h4" gutterBottom>
                {systemStatus.metrics.diskUsage}%
              </Typography>
              <LinearProgress 
                variant="determinate" 
                value={systemStatus.metrics.diskUsage} 
                color={systemStatus.metrics.diskUsage > 80 ? 'error' : 'primary'}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Cloud color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Network Latency</Typography>
              </Box>
              <Typography variant="h4" gutterBottom>
                {systemStatus.metrics.networkLatency}ms
              </Typography>
              <LinearProgress 
                variant="determinate" 
                value={Math.min(systemStatus.metrics.networkLatency / 2, 100)} 
                color={systemStatus.metrics.networkLatency > 100 ? 'error' : 'primary'}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Services Status */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Service Status
              </Typography>
              <List>
                {systemStatus.services.map((service, index) => (
                  <ListItem key={index}>
                    <ListItemIcon>
                      {getStatusIcon(service.status)}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="subtitle1">{service.name}</Typography>
                          <Chip
                            label={service.status.toUpperCase()}
                            color={getStatusColor(service.status)}
                            size="small"
                          />
                        </Box>
                      }
                      secondary={`Uptime: ${service.uptime} | Response Time: ${service.responseTime}`}
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Alerts
              </Typography>
              <List>
                {systemStatus.alerts.map((alert) => (
                  <ListItem key={alert.id}>
                    <ListItemIcon>
                      {getAlertIcon(alert.type)}
                    </ListItemIcon>
                    <ListItemText
                      primary={alert.message}
                      secondary={alert.time}
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default SystemHealth;
