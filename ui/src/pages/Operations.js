import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Button,
  Alert,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton,
  Tooltip,
  useTheme,
  Container,
  Paper,
  Fade,
  Skeleton,
  AppBar,
  Toolbar,
  Breadcrumbs,
  Link,
  Divider,
} from '@mui/material';
import {
  ExpandMore,
  PlayArrow,
  CheckCircle,
  Error,
  Warning,
  Info,
  ContentCopy,
  Refresh,
  Timeline,
  Storage,
  Security,
  MonitorHeart,
  CloudUpload,
  Settings,
  Dashboard as DashboardIcon,
  Home,
} from '@mui/icons-material';
import { useResponsive } from '../hooks/useResponsive';
import { ResponsiveContainer, ResponsiveGrid, ResponsiveFlex } from '../components/common/ResponsiveContainer';
import { LoadingSpinner, CardSkeleton, FadeInContent } from '../components/common/LoadingComponents';
import { useAuth } from '../contexts/AuthContext';
import DeploymentGuide from '../components/operations/DeploymentGuide';
import TroubleshootingGuide from '../components/operations/TroubleshootingGuide';
import DatabaseOperations from '../components/operations/DatabaseOperations';
import MonitoringSetup from '../components/operations/MonitoringSetup';
import SystemStatus from '../components/operations/SystemStatus';
import ConfigurationValidation from '../components/operations/ConfigurationValidation';

const Operations = () => {
  const theme = useTheme();
  const { isMobile, isTablet, getCurrentBreakpoint } = useResponsive();

  const [activeTab, setActiveTab] = useState(0);
  const [systemStatus, setSystemStatus] = useState({
    overall: 'healthy',
    database: 'healthy',
    api: 'healthy',
    monitoring: 'healthy',
    lastCheck: new Date().toISOString()
  });
  const [loading, setLoading] = useState(true);
  const { hasPermission } = useAuth();

  useEffect(() => {
    // Check if user has operations permissions
    if (!hasPermission('operations.read')) {
      return;
    }
    
    // Fetch system status
    fetchSystemStatus();
    
    // Set up periodic status updates
    const interval = setInterval(fetchSystemStatus, 30000);
    return () => clearInterval(interval);
  }, [hasPermission]);

  const fetchSystemStatus = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/operations/status');
      if (response.ok) {
        const status = await response.json();
        setSystemStatus(status);
      }
    } catch (error) {
      console.error('Failed to fetch system status:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

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
      default: return <Info />;
    }
  };

  if (!hasPermission('operations.read')) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          You don't have permission to access operations documentation.
        </Alert>
      </Box>
    );
  }

  const TabPanel = ({ children, value, index }) => (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`operations-tabpanel-${index}`}
      aria-labelledby={`operations-tab-${index}`}
    >
      {value === index && (
        <Fade in={value === index} timeout={300}>
          <Box>
            {children}
          </Box>
        </Fade>
      )}
    </div>
  );

  if (loading) {
    return (
      <ResponsiveContainer>
        <LoadingSpinner message="Loading Operations Center..." />
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer maxWidth="xl">
      {/* Breadcrumbs */}
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link color="inherit" href="/" sx={{ display: 'flex', alignItems: 'center' }}>
          <Home sx={{ mr: 0.5 }} fontSize="inherit" />
          Home
        </Link>
        <Typography color="text.primary" sx={{ display: 'flex', alignItems: 'center' }}>
          <Settings sx={{ mr: 0.5 }} fontSize="inherit" />
          Operations
        </Typography>
      </Breadcrumbs>

      {/* Header */}
      <ResponsiveFlex
        direction={{ xs: 'column', sm: 'row' }}
        justify="space-between"
        align={{ xs: 'stretch', sm: 'center' }}
        sx={{ mb: 4 }}
      >
        <Box>
          <Typography
            variant={isMobile ? "h5" : "h4"}
            component="h1"
            fontWeight="bold"
            sx={{ mb: { xs: 1, sm: 0 } }}
          >
            Operations Center
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Monitor and manage RegulensAI system operations
          </Typography>
        </Box>

        <ResponsiveFlex
          direction={{ xs: 'column', sm: 'row' }}
          spacing={1}
          sx={{ mt: { xs: 2, sm: 0 } }}
        >
          <Chip
            icon={getStatusIcon(systemStatus.overall)}
            label={`System ${systemStatus.overall.toUpperCase()}`}
            color={getStatusColor(systemStatus.overall)}
            size={isMobile ? "medium" : "small"}
          />
          <Tooltip title="Refresh Status">
            <IconButton
              onClick={fetchSystemStatus}
              size={isMobile ? "medium" : "small"}
            >
              <Refresh />
            </IconButton>
          </Tooltip>
        </ResponsiveFlex>
      </ResponsiveFlex>

      {/* System Status Overview */}
      <FadeInContent loading={loading} skeleton={
        <ResponsiveGrid spacing={{ xs: 2, sm: 3 }}>
          {[1, 2, 3, 4].map((i) => (
            <CardSkeleton key={i} height={{ xs: 140, sm: 160 }} />
          ))}
        </ResponsiveGrid>
      }>
        <ResponsiveGrid
          spacing={{ xs: 2, sm: 3, md: 4 }}
          sx={{ mb: 4 }}
        >
          <Card
            sx={{
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: theme.shadows[4],
              }
            }}
          >
            <CardContent sx={{ textAlign: 'center', py: { xs: 2, sm: 3 } }}>
              <Storage
                color="primary"
                sx={{
                  fontSize: { xs: 32, sm: 40 },
                  mb: 1
                }}
              />
              <Typography variant={isMobile ? "subtitle1" : "h6"} gutterBottom>
                Database
              </Typography>
              <Chip
                label={systemStatus.database.toUpperCase()}
                color={getStatusColor(systemStatus.database)}
                size={isMobile ? "medium" : "small"}
              />
            </CardContent>
          </Card>

          <Card
            sx={{
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: theme.shadows[4],
              }
            }}
          >
            <CardContent sx={{ textAlign: 'center', py: { xs: 2, sm: 3 } }}>
              <CloudUpload
                color="primary"
                sx={{
                  fontSize: { xs: 32, sm: 40 },
                  mb: 1
                }}
              />
              <Typography variant={isMobile ? "subtitle1" : "h6"} gutterBottom>
                API Services
              </Typography>
              <Chip
                label={systemStatus.api.toUpperCase()}
                color={getStatusColor(systemStatus.api)}
                size={isMobile ? "medium" : "small"}
              />
            </CardContent>
          </Card>

          <Card
            sx={{
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: theme.shadows[4],
              }
            }}
          >
            <CardContent sx={{ textAlign: 'center', py: { xs: 2, sm: 3 } }}>
              <MonitorHeart
                color="primary"
                sx={{
                  fontSize: { xs: 32, sm: 40 },
                  mb: 1
                }}
              />
              <Typography variant={isMobile ? "subtitle1" : "h6"} gutterBottom>
                Monitoring
              </Typography>
              <Chip
                label={systemStatus.monitoring.toUpperCase()}
                color={getStatusColor(systemStatus.monitoring)}
                size={isMobile ? "medium" : "small"}
              />
            </CardContent>
          </Card>

          <Card
            sx={{
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: theme.shadows[4],
              }
            }}
          >
            <CardContent sx={{ textAlign: 'center', py: { xs: 2, sm: 3 } }}>
              <Security
                color="primary"
                sx={{
                  fontSize: { xs: 32, sm: 40 },
                  mb: 1
                }}
              />
              <Typography variant={isMobile ? "subtitle1" : "h6"} gutterBottom>
                Security
              </Typography>
              <Chip
                label="ACTIVE"
                color="success"
                size={isMobile ? "medium" : "small"}
              />
            </CardContent>
          </Card>
        </ResponsiveGrid>
      </FadeInContent>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Security color="primary" sx={{ fontSize: 40, mb: 1 }} />
              <Typography variant="h6">Security</Typography>
              <Chip
                label="COMPLIANT"
                color="success"
                size="small"
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Operations Tabs */}
      <Paper
        elevation={2}
        sx={{
          borderRadius: 2,
          overflow: 'hidden',
        }}
      >
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          variant={isMobile ? "scrollable" : "standard"}
          scrollButtons={isMobile ? "auto" : false}
          allowScrollButtonsMobile
          sx={{
            borderBottom: 1,
            borderColor: 'divider',
            '& .MuiTab-root': {
              minHeight: { xs: 48, sm: 64 },
              fontSize: { xs: '0.75rem', sm: '0.875rem' },
              fontWeight: 500,
              textTransform: 'none',
              '&.Mui-selected': {
                fontWeight: 600,
              },
            },
            '& .MuiTabs-indicator': {
              height: 3,
              borderRadius: '3px 3px 0 0',
            },
          }}
        >
          <Tab
            icon={<Timeline />}
            label={isMobile ? "Deploy" : "Deployment"}
            iconPosition={isMobile ? "top" : "start"}
          />
          <Tab
            icon={<Error />}
            label={isMobile ? "Issues" : "Troubleshooting"}
            iconPosition={isMobile ? "top" : "start"}
          />
          <Tab
            icon={<Storage />}
            label="Database"
            iconPosition={isMobile ? "top" : "start"}
          />
          <Tab
            icon={<MonitorHeart />}
            label={isMobile ? "Monitor" : "Monitoring"}
            iconPosition={isMobile ? "top" : "start"}
          />
          <Tab
            icon={<Settings />}
            label={isMobile ? "Config" : "Configuration"}
            iconPosition={isMobile ? "top" : "start"}
          />
          <Tab
            icon={<Info />}
            label="Status"
            iconPosition={isMobile ? "top" : "start"}
          />
        </Tabs>

        <Box sx={{
          p: { xs: 2, sm: 3, md: 4 },
          minHeight: '400px',
        }}>
          <TabPanel value={activeTab} index={0}>
            <FadeInContent>
              <DeploymentGuide />
            </FadeInContent>
          </TabPanel>

          <TabPanel value={activeTab} index={1}>
            <FadeInContent>
              <TroubleshootingGuide />
            </FadeInContent>
          </TabPanel>

          <TabPanel value={activeTab} index={2}>
            <FadeInContent>
              <DatabaseOperations />
            </FadeInContent>
          </TabPanel>

          <TabPanel value={activeTab} index={3}>
            <FadeInContent>
              <MonitoringSetup />
            </FadeInContent>
          </TabPanel>

          <TabPanel value={activeTab} index={4}>
            <FadeInContent>
              <ConfigurationValidation />
            </FadeInContent>
          </TabPanel>

          <TabPanel value={activeTab} index={5}>
            <FadeInContent>
              <SystemStatus systemStatus={systemStatus} />
            </FadeInContent>
          </TabPanel>
        </Box>
      </Paper>

      {/* Quick Actions */}
      <ResponsiveGrid
        spacing={{ xs: 2, sm: 3 }}
        sx={{ mt: 4 }}
      >
        <Card
          sx={{
            transition: 'all 0.2s ease-in-out',
            '&:hover': {
              transform: 'translateY(-2px)',
              boxShadow: theme.shadows[4],
            }
          }}
        >
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <PlayArrow color="primary" />
              Quick Actions
            </Typography>
            <List disablePadding>
              <ListItem
                sx={{
                  px: 0,
                  flexDirection: { xs: 'column', sm: 'row' },
                  alignItems: { xs: 'stretch', sm: 'center' },
                  gap: { xs: 1, sm: 0 },
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', flex: 1 }}>
                  <ListItemIcon sx={{ minWidth: 40 }}>
                    <PlayArrow />
                  </ListItemIcon>
                  <ListItemText
                    primary="Start Deployment"
                    secondary="Begin staging or production deployment"
                    primaryTypographyProps={{
                      fontSize: { xs: '0.875rem', sm: '1rem' }
                    }}
                    secondaryTypographyProps={{
                      fontSize: { xs: '0.75rem', sm: '0.875rem' }
                    }}
                  />
                </Box>
                <Button
                  variant="outlined"
                  size={isMobile ? "medium" : "small"}
                  fullWidth={isMobile}
                >
                  Start
                </Button>
              </ListItem>
              <ListItem
                sx={{
                  px: 0,
                  flexDirection: { xs: 'column', sm: 'row' },
                  alignItems: { xs: 'stretch', sm: 'center' },
                  gap: { xs: 1, sm: 0 },
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', flex: 1 }}>
                  <ListItemIcon sx={{ minWidth: 40 }}>
                    <Storage />
                  </ListItemIcon>
                  <ListItemText
                    primary="Database Migration"
                    secondary="Run pending database migrations"
                    primaryTypographyProps={{
                      fontSize: { xs: '0.875rem', sm: '1rem' }
                    }}
                    secondaryTypographyProps={{
                      fontSize: { xs: '0.75rem', sm: '0.875rem' }
                    }}
                  />
                </Box>
                <Button
                  variant="outlined"
                  size={isMobile ? "medium" : "small"}
                  fullWidth={isMobile}
                >
                  Migrate
                </Button>
              </ListItem>

              <ListItem
                sx={{
                  px: 0,
                  flexDirection: { xs: 'column', sm: 'row' },
                  alignItems: { xs: 'stretch', sm: 'center' },
                  gap: { xs: 1, sm: 0 },
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', flex: 1 }}>
                  <ListItemIcon sx={{ minWidth: 40 }}>
                    <MonitorHeart />
                  </ListItemIcon>
                  <ListItemText
                    primary="Health Check"
                    secondary="Run comprehensive system health check"
                    primaryTypographyProps={{
                      fontSize: { xs: '0.875rem', sm: '1rem' }
                    }}
                    secondaryTypographyProps={{
                      fontSize: { xs: '0.75rem', sm: '0.875rem' }
                    }}
                  />
                </Box>
                <Button
                  variant="outlined"
                  size={isMobile ? "medium" : "small"}
                  fullWidth={isMobile}
                >
                  Check
                </Button>
              </ListItem>
            </List>
          </CardContent>
        </Card>

        <Card
          sx={{
            transition: 'all 0.2s ease-in-out',
            '&:hover': {
              transform: 'translateY(-2px)',
              boxShadow: theme.shadows[4],
            }
          }}
        >
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Timeline color="primary" />
              Recent Activities
            </Typography>
            <List disablePadding>
              <ListItem sx={{ px: 0, py: 1 }}>
                <ListItemIcon sx={{ minWidth: 40 }}>
                  <CheckCircle color="success" />
                </ListItemIcon>
                <ListItemText
                  primary="Production deployment completed"
                  secondary="2 hours ago - v1.2.0"
                  primaryTypographyProps={{
                    fontSize: { xs: '0.875rem', sm: '1rem' }
                  }}
                  secondaryTypographyProps={{
                    fontSize: { xs: '0.75rem', sm: '0.875rem' }
                  }}
                />
              </ListItem>

              <ListItem sx={{ px: 0, py: 1 }}>
                <ListItemIcon sx={{ minWidth: 40 }}>
                  <CheckCircle color="success" />
                </ListItemIcon>
                <ListItemText
                  primary="Database migration successful"
                  secondary="3 hours ago - Migration 005"
                  primaryTypographyProps={{
                    fontSize: { xs: '0.875rem', sm: '1rem' }
                  }}
                  secondaryTypographyProps={{
                    fontSize: { xs: '0.75rem', sm: '0.875rem' }
                  }}
                />
              </ListItem>

              <ListItem sx={{ px: 0, py: 1 }}>
                <ListItemIcon sx={{ minWidth: 40 }}>
                  <Warning color="warning" />
                </ListItemIcon>
                <ListItemText
                  primary="High memory usage detected"
                  secondary="1 day ago - Resolved"
                  primaryTypographyProps={{
                    fontSize: { xs: '0.875rem', sm: '1rem' }
                  }}
                  secondaryTypographyProps={{
                    fontSize: { xs: '0.75rem', sm: '0.875rem' }
                  }}
                />
              </ListItem>
            </List>
          </CardContent>
        </Card>
      </ResponsiveGrid>
    </ResponsiveContainer>
  );
};

export default Operations;
