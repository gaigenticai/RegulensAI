import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Alert,
  Paper
} from '@mui/material';
import {
  TrendingUp,
  Warning,
  CheckCircle,
  Error,
  Refresh,
  Assessment,
  Security,
  School,
  MonitorHeart
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState({
    metrics: {
      totalCompliance: 0,
      activeAlerts: 0,
      completedTraining: 0,
      systemHealth: 0
    },
    recentAlerts: [],
    complianceScore: [],
    riskDistribution: [],
    loading: true
  });

  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setRefreshing(true);
      
      // Simulate API calls - replace with actual endpoints
      const [metricsRes, alertsRes, complianceRes, riskRes] = await Promise.allSettled([
        axios.get(`${API_BASE_URL}/dashboard/metrics`),
        axios.get(`${API_BASE_URL}/dashboard/alerts`),
        axios.get(`${API_BASE_URL}/dashboard/compliance-score`),
        axios.get(`${API_BASE_URL}/dashboard/risk-distribution`)
      ]);

      // Mock data for demonstration
      const mockData = {
        metrics: {
          totalCompliance: 94.2,
          activeAlerts: 12,
          completedTraining: 87.5,
          systemHealth: 99.1
        },
        recentAlerts: [
          { id: 1, type: 'warning', message: 'AML threshold exceeded for customer ID 12345', time: '2 hours ago' },
          { id: 2, type: 'info', message: 'New regulatory update available', time: '4 hours ago' },
          { id: 3, type: 'error', message: 'KYC document verification failed', time: '6 hours ago' },
          { id: 4, type: 'success', message: 'Compliance report generated successfully', time: '8 hours ago' }
        ],
        complianceScore: [
          { month: 'Jan', score: 92 },
          { month: 'Feb', score: 89 },
          { month: 'Mar', score: 94 },
          { month: 'Apr', score: 91 },
          { month: 'May', score: 96 },
          { month: 'Jun', score: 94 }
        ],
        riskDistribution: [
          { name: 'Low Risk', value: 65, color: '#4caf50' },
          { name: 'Medium Risk', value: 25, color: '#ff9800' },
          { name: 'High Risk', value: 10, color: '#f44336' }
        ],
        loading: false
      };

      setDashboardData(mockData);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      setDashboardData(prev => ({ ...prev, loading: false }));
    } finally {
      setRefreshing(false);
    }
  };

  const getAlertIcon = (type) => {
    switch (type) {
      case 'error': return <Error color="error" />;
      case 'warning': return <Warning color="warning" />;
      case 'success': return <CheckCircle color="success" />;
      default: return <Assessment color="info" />;
    }
  };

  const getAlertColor = (type) => {
    switch (type) {
      case 'error': return 'error';
      case 'warning': return 'warning';
      case 'success': return 'success';
      default: return 'info';
    }
  };

  if (dashboardData.loading) {
    return (
      <Box sx={{ width: '100%' }}>
        <LinearProgress />
        <Typography variant="h6" sx={{ mt: 2, textAlign: 'center' }}>
          Loading dashboard data...
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Dashboard Overview
        </Typography>
        <IconButton onClick={fetchDashboardData} disabled={refreshing}>
          <Refresh />
        </IconButton>
      </Box>

      {/* Key Metrics Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Compliance Score
                  </Typography>
                  <Typography variant="h4">
                    {dashboardData.metrics.totalCompliance}%
                  </Typography>
                </Box>
                <Security color="primary" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Active Alerts
                  </Typography>
                  <Typography variant="h4">
                    {dashboardData.metrics.activeAlerts}
                  </Typography>
                </Box>
                <Warning color="warning" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Training Completion
                  </Typography>
                  <Typography variant="h4">
                    {dashboardData.metrics.completedTraining}%
                  </Typography>
                </Box>
                <School color="success" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    System Health
                  </Typography>
                  <Typography variant="h4">
                    {dashboardData.metrics.systemHealth}%
                  </Typography>
                </Box>
                <MonitorHeart color="success" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts and Recent Activity */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Compliance Score Trend
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={dashboardData.complianceScore}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="score" stroke="#1976d2" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Risk Distribution
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={dashboardData.riskDistribution}
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                    label={({ name, value }) => `${name}: ${value}%`}
                  >
                    {dashboardData.riskDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Alerts
              </Typography>
              <List>
                {dashboardData.recentAlerts.map((alert) => (
                  <ListItem key={alert.id}>
                    <ListItemIcon>
                      {getAlertIcon(alert.type)}
                    </ListItemIcon>
                    <ListItemText
                      primary={alert.message}
                      secondary={alert.time}
                    />
                    <Chip
                      label={alert.type.toUpperCase()}
                      color={getAlertColor(alert.type)}
                      size="small"
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

export default Dashboard;
