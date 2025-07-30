import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Tooltip,
  Button,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import {
  CheckCircle,
  Error,
  Warning,
  Info,
  Refresh,
  Timeline,
  Storage,
  Memory,
  Speed,
  NetworkCheck,
  Security,
  ExpandMore,
  MonitorHeart,
  CloudUpload
} from '@mui/icons-material';

const SystemStatus = ({ systemStatus }) => {
  const [detailedMetrics, setDetailedMetrics] = useState({
    pods: [],
    services: [],
    nodes: [],
    resources: {},
    performance: {}
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchDetailedMetrics();
  }, []);

  const fetchDetailedMetrics = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/operations/system/detailed-status');
      if (response.ok) {
        const data = await response.json();
        setDetailedMetrics(data);
      }
    } catch (error) {
      console.error('Failed to fetch detailed metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
      case 'running':
      case 'ready': return 'success';
      case 'warning':
      case 'pending': return 'warning';
      case 'error':
      case 'failed':
      case 'crashloopbackoff': return 'error';
      default: return 'default';
    }
  };

  const getStatusIcon = (status) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
      case 'running':
      case 'ready': return <CheckCircle color="success" />;
      case 'warning':
      case 'pending': return <Warning color="warning" />;
      case 'error':
      case 'failed':
      case 'crashloopbackoff': return <Error color="error" />;
      default: return <Info />;
    }
  };

  const systemComponents = [
    {
      name: 'API Gateway',
      status: systemStatus?.api || 'unknown',
      description: 'Main API service handling requests',
      icon: <CloudUpload />
    },
    {
      name: 'Database',
      status: systemStatus?.database || 'unknown',
      description: 'PostgreSQL database cluster',
      icon: <Storage />
    },
    {
      name: 'Redis Cache',
      status: systemStatus?.redis || 'unknown',
      description: 'Redis caching layer',
      icon: <Memory />
    },
    {
      name: 'Monitoring',
      status: systemStatus?.monitoring || 'unknown',
      description: 'Prometheus and Grafana stack',
      icon: <MonitorHeart />
    }
  ];

  const mockPods = [
    { name: 'regulensai-api-7d8f9b5c6d-abc12', status: 'Running', restarts: 0, age: '2d', cpu: '45%', memory: '512Mi' },
    { name: 'regulensai-api-7d8f9b5c6d-def34', status: 'Running', restarts: 0, age: '2d', cpu: '38%', memory: '487Mi' },
    { name: 'regulensai-worker-5f6g7h8i9j-ghi56', status: 'Running', restarts: 1, age: '1d', cpu: '23%', memory: '256Mi' },
    { name: 'postgres-primary-0', status: 'Running', restarts: 0, age: '7d', cpu: '67%', memory: '2Gi' },
    { name: 'redis-master-0', status: 'Running', restarts: 0, age: '7d', cpu: '12%', memory: '128Mi' }
  ];

  const mockServices = [
    { name: 'regulensai-api', type: 'ClusterIP', clusterIP: '10.96.1.100', ports: '8000/TCP', age: '7d' },
    { name: 'regulensai-frontend', type: 'LoadBalancer', clusterIP: '10.96.1.101', ports: '80/TCP,443/TCP', age: '7d' },
    { name: 'postgres-primary', type: 'ClusterIP', clusterIP: '10.96.1.102', ports: '5432/TCP', age: '7d' },
    { name: 'redis-master', type: 'ClusterIP', clusterIP: '10.96.1.103', ports: '6379/TCP', age: '7d' }
  ];

  const performanceMetrics = [
    { metric: 'CPU Usage', value: 45, unit: '%', status: 'healthy' },
    { metric: 'Memory Usage', value: 67, unit: '%', status: 'warning' },
    { metric: 'Disk Usage', value: 23, unit: '%', status: 'healthy' },
    { metric: 'Network I/O', value: 156, unit: 'MB/s', status: 'healthy' },
    { metric: 'API Response Time', value: 245, unit: 'ms', status: 'healthy' },
    { metric: 'Database Connections', value: 45, unit: 'active', status: 'healthy' }
  ];

  const healthChecks = [
    { name: 'API Health Endpoint', status: 'passing', lastCheck: '30s ago' },
    { name: 'Database Connectivity', status: 'passing', lastCheck: '1m ago' },
    { name: 'Redis Connectivity', status: 'passing', lastCheck: '1m ago' },
    { name: 'External API Access', status: 'warning', lastCheck: '2m ago' },
    { name: 'SSL Certificate', status: 'passing', lastCheck: '1h ago' },
    { name: 'Backup Status', status: 'passing', lastCheck: '6h ago' }
  ];

  return (
    <Box>
      {/* System Overview */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6">System Status Overview</Typography>
        <Button
          startIcon={<Refresh />}
          onClick={fetchDetailedMetrics}
          disabled={loading}
        >
          Refresh
        </Button>
      </Box>

      {/* Component Status Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {systemComponents.map((component) => (
          <Grid item xs={12} md={3} key={component.name}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <Box sx={{ display: 'flex', justifyContent: 'center', mb: 1 }}>
                  {component.icon}
                </Box>
                <Typography variant="h6" gutterBottom>
                  {component.name}
                </Typography>
                <Chip
                  icon={getStatusIcon(component.status)}
                  label={component.status.toUpperCase()}
                  color={getStatusColor(component.status)}
                  size="small"
                />
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  {component.description}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Performance Metrics */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Performance Metrics
          </Typography>
          <Grid container spacing={3}>
            {performanceMetrics.map((metric) => (
              <Grid item xs={12} md={4} key={metric.metric}>
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Typography variant="body2">{metric.metric}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {metric.value}{metric.unit}
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={typeof metric.value === 'number' && metric.unit === '%' ? metric.value : 50}
                    color={getStatusColor(metric.status)}
                    sx={{ height: 8, borderRadius: 4 }}
                  />
                </Box>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>

      {/* Health Checks */}
      <Accordion sx={{ mb: 2 }}>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Health Checks</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <List>
            {healthChecks.map((check, index) => (
              <ListItem key={index}>
                <ListItemIcon>
                  {getStatusIcon(check.status)}
                </ListItemIcon>
                <ListItemText
                  primary={check.name}
                  secondary={`Last check: ${check.lastCheck}`}
                />
                <Chip
                  label={check.status.toUpperCase()}
                  color={getStatusColor(check.status)}
                  size="small"
                />
              </ListItem>
            ))}
          </List>
        </AccordionDetails>
      </Accordion>

      {/* Pod Status */}
      <Accordion sx={{ mb: 2 }}>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Pod Status</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Pod Name</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Restarts</TableCell>
                  <TableCell>Age</TableCell>
                  <TableCell>CPU</TableCell>
                  <TableCell>Memory</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {mockPods.map((pod) => (
                  <TableRow key={pod.name}>
                    <TableCell>{pod.name}</TableCell>
                    <TableCell>
                      <Chip
                        label={pod.status}
                        color={getStatusColor(pod.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{pod.restarts}</TableCell>
                    <TableCell>{pod.age}</TableCell>
                    <TableCell>{pod.cpu}</TableCell>
                    <TableCell>{pod.memory}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </AccordionDetails>
      </Accordion>

      {/* Service Status */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Service Status</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Service Name</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Cluster IP</TableCell>
                  <TableCell>Ports</TableCell>
                  <TableCell>Age</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {mockServices.map((service) => (
                  <TableRow key={service.name}>
                    <TableCell>{service.name}</TableCell>
                    <TableCell>{service.type}</TableCell>
                    <TableCell>{service.clusterIP}</TableCell>
                    <TableCell>{service.ports}</TableCell>
                    <TableCell>{service.age}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </AccordionDetails>
      </Accordion>

      {/* System Information */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            System Information
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Typography variant="body2" color="text.secondary">
                <strong>Last Updated:</strong> {systemStatus?.lastCheck ? new Date(systemStatus.lastCheck).toLocaleString() : 'Unknown'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                <strong>Uptime:</strong> 7 days, 14 hours, 23 minutes
              </Typography>
              <Typography variant="body2" color="text.secondary">
                <strong>Version:</strong> RegulensAI v1.2.0
              </Typography>
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography variant="body2" color="text.secondary">
                <strong>Environment:</strong> Production
              </Typography>
              <Typography variant="body2" color="text.secondary">
                <strong>Cluster:</strong> regulensai-prod-cluster
              </Typography>
              <Typography variant="body2" color="text.secondary">
                <strong>Region:</strong> us-east-1
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
};

export default SystemStatus;
