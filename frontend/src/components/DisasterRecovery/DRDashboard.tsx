/**
 * RegulensAI Disaster Recovery Dashboard
 * Comprehensive DR monitoring, testing, and management interface
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  LinearProgress,
  Alert,
  Tabs,
  Tab,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Security as SecurityIcon,
  PlayArrow as PlayIcon,
  Refresh as RefreshIcon,
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
  Assessment as AssessmentIcon
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';

import { drApi } from '../../services/api/disasterRecovery';
import { DRStatusCard } from './DRStatusCard';
import { DRComponentList } from './DRComponentList';
import { DREventsList } from './DREventsList';
import { DRTestResults } from './DRTestResults';
import { DRTestDialog } from './DRTestDialog';
import { DRHealthScore } from './DRHealthScore';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`dr-tabpanel-${index}`}
      aria-labelledby={`dr-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export const DRDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [testDialogOpen, setTestDialogOpen] = useState(false);
  const [fullTestDialogOpen, setFullTestDialogOpen] = useState(false);
  const queryClient = useQueryClient();

  // Fetch DR status
  const {
    data: drStatus,
    isLoading: statusLoading,
    error: statusError,
    refetch: refetchStatus
  } = useQuery({
    queryKey: ['drStatus'],
    queryFn: drApi.getStatus,
    refetchInterval: 30000, // Refresh every 30 seconds
    staleTime: 10000
  });

  // Fetch DR components
  const {
    data: drComponents,
    isLoading: componentsLoading
  } = useQuery({
    queryKey: ['drComponents'],
    queryFn: drApi.getComponents,
    refetchInterval: 60000 // Refresh every minute
  });

  // Fetch DR events
  const {
    data: drEvents,
    isLoading: eventsLoading
  } = useQuery({
    queryKey: ['drEvents'],
    queryFn: () => drApi.getEvents({ limit: 20, hours: 24 }),
    refetchInterval: 30000
  });

  // Fetch test results
  const {
    data: testResults,
    isLoading: resultsLoading
  } = useQuery({
    queryKey: ['drTestResults'],
    queryFn: () => drApi.getTestResults({ limit: 10 }),
    refetchInterval: 30000
  });

  // Fetch health score
  const {
    data: healthScore,
    isLoading: healthLoading
  } = useQuery({
    queryKey: ['drHealthScore'],
    queryFn: drApi.getHealthScore,
    refetchInterval: 60000
  });

  // Run full DR test mutation
  const fullTestMutation = useMutation({
    mutationFn: (dryRun: boolean) => drApi.runFullTest({ dryRun }),
    onSuccess: () => {
      toast.success('Full DR test initiated successfully');
      setFullTestDialogOpen(false);
      // Refresh data after a delay
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['drTestResults'] });
        queryClient.invalidateQueries({ queryKey: ['drStatus'] });
      }, 2000);
    },
    onError: (error: any) => {
      toast.error(`Failed to initiate full DR test: ${error.message}`);
    }
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['drStatus'] });
    queryClient.invalidateQueries({ queryKey: ['drComponents'] });
    queryClient.invalidateQueries({ queryKey: ['drEvents'] });
    queryClient.invalidateQueries({ queryKey: ['drTestResults'] });
    queryClient.invalidateQueries({ queryKey: ['drHealthScore'] });
    toast.info('DR dashboard refreshed');
  };

  const handleRunFullTest = (dryRun: boolean) => {
    fullTestMutation.mutate(dryRun);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'warning':
        return 'warning';
      case 'critical':
      case 'failed':
        return 'error';
      case 'testing':
        return 'info';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckIcon color="success" />;
      case 'warning':
        return <WarningIcon color="warning" />;
      case 'critical':
      case 'failed':
        return <ErrorIcon color="error" />;
      case 'testing':
        return <ScheduleIcon color="info" />;
      default:
        return <DashboardIcon />;
    }
  };

  if (statusLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress size={60} />
        <Typography variant="h6" sx={{ ml: 2 }}>
          Loading DR Dashboard...
        </Typography>
      </Box>
    );
  }

  if (statusError) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        Failed to load DR dashboard: {(statusError as Error).message}
      </Alert>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box display="flex" alignItems="center">
          <SecurityIcon sx={{ fontSize: 32, mr: 1, color: 'primary.main' }} />
          <Typography variant="h4" component="h1">
            Disaster Recovery
          </Typography>
        </Box>
        <Box>
          <Tooltip title="Refresh Dashboard">
            <IconButton onClick={handleRefresh} sx={{ mr: 1 }}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Button
            variant="outlined"
            startIcon={<PlayIcon />}
            onClick={() => setTestDialogOpen(true)}
            sx={{ mr: 1 }}
          >
            Run Test
          </Button>
          <Button
            variant="contained"
            startIcon={<AssessmentIcon />}
            onClick={() => setFullTestDialogOpen(true)}
            color="primary"
          >
            Full DR Test
          </Button>
        </Box>
      </Box>

      {/* Status Overview */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={1}>
                {getStatusIcon(drStatus?.overall_status || 'unknown')}
                <Typography variant="h6" sx={{ ml: 1 }}>
                  Overall Status
                </Typography>
              </Box>
              <Chip
                label={drStatus?.overall_status?.toUpperCase() || 'UNKNOWN'}
                color={getStatusColor(drStatus?.overall_status || 'unknown') as any}
                variant="filled"
                size="small"
              />
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Last updated: {drStatus?.last_updated ? new Date(drStatus.last_updated).toLocaleString() : 'Unknown'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <DRHealthScore 
            score={healthScore?.overall_score || 0}
            loading={healthLoading}
          />
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Active Components
              </Typography>
              <Typography variant="h4" color="primary.main">
                {drComponents?.length || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {drComponents?.filter(c => c.status === 'healthy').length || 0} healthy
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Tests
              </Typography>
              <Typography variant="h4" color="primary.main">
                {testResults?.test_results?.length || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {testResults?.test_results?.filter((t: any) => t.status === 'passed').length || 0} passed
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Main Content Tabs */}
      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={activeTab} onChange={handleTabChange} aria-label="DR dashboard tabs">
            <Tab label="Components" />
            <Tab label="Events" />
            <Tab label="Test Results" />
            <Tab label="Status Overview" />
          </Tabs>
        </Box>

        <TabPanel value={activeTab} index={0}>
          <DRComponentList 
            components={drComponents || []}
            loading={componentsLoading}
            onTestComponent={(component, testType) => {
              // Handle component test
              setTestDialogOpen(true);
            }}
          />
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          <DREventsList 
            events={drEvents?.events || []}
            loading={eventsLoading}
          />
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
          <DRTestResults 
            results={testResults?.test_results || []}
            loading={resultsLoading}
          />
        </TabPanel>

        <TabPanel value={activeTab} index={3}>
          <DRStatusCard 
            status={drStatus}
            loading={statusLoading}
          />
        </TabPanel>
      </Card>

      {/* Test Dialog */}
      <DRTestDialog
        open={testDialogOpen}
        onClose={() => setTestDialogOpen(false)}
        components={drComponents || []}
      />

      {/* Full Test Dialog */}
      <Dialog open={fullTestDialogOpen} onClose={() => setFullTestDialogOpen(false)}>
        <DialogTitle>Run Full DR Test</DialogTitle>
        <DialogContent>
          <Typography variant="body1" gutterBottom>
            This will run comprehensive disaster recovery tests for all components.
            The test will validate backups, test failover procedures, and verify recovery capabilities.
          </Typography>
          <Alert severity="info" sx={{ mt: 2 }}>
            Estimated duration: 60 minutes
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFullTestDialogOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => handleRunFullTest(true)}
            variant="outlined"
            disabled={fullTestMutation.isPending}
          >
            Dry Run
          </Button>
          <Button
            onClick={() => handleRunFullTest(false)}
            variant="contained"
            disabled={fullTestMutation.isPending}
            color="warning"
          >
            {fullTestMutation.isPending ? 'Starting...' : 'Live Test'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
