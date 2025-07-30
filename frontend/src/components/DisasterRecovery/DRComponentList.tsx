/**
 * DR Component List Component
 * Displays detailed status and controls for each DR component
 */

import React, { useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Button,
  IconButton,
  Tooltip,
  Box,
  Typography,
  Collapse,
  Alert,
  LinearProgress,
  Menu,
  MenuItem
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Schedule as ScheduleIcon,
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  MoreVert as MoreVertIcon
} from '@mui/icons-material';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';

import { drApi } from '../../services/api/disasterRecovery';

interface DRComponent {
  component: string;
  status: string;
  rto_minutes: number;
  rpo_minutes: number;
  priority: number;
  automated_recovery: boolean;
  last_test_time: string | null;
  last_backup_time: string | null;
  dependencies: string[];
}

interface DRComponentListProps {
  components: DRComponent[];
  loading: boolean;
  onTestComponent?: (component: string, testType: string) => void;
}

export const DRComponentList: React.FC<DRComponentListProps> = ({
  components,
  loading,
  onTestComponent
}) => {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedComponent, setSelectedComponent] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // Test component mutation
  const testMutation = useMutation({
    mutationFn: ({ component, testType, dryRun }: { component: string; testType: string; dryRun: boolean }) =>
      drApi.runTest({ component, test_type: testType, dry_run: dryRun }),
    onSuccess: (data, variables) => {
      toast.success(`${variables.testType} test initiated for ${variables.component}`);
      // Refresh test results after a delay
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['drTestResults'] });
        queryClient.invalidateQueries({ queryKey: ['drComponents'] });
      }, 2000);
    },
    onError: (error: any, variables) => {
      toast.error(`Failed to run ${variables.testType} test for ${variables.component}: ${error.message}`);
    }
  });

  const handleExpandRow = (component: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(component)) {
      newExpanded.delete(component);
    } else {
      newExpanded.add(component);
    }
    setExpandedRows(newExpanded);
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, component: string) => {
    setAnchorEl(event.currentTarget);
    setSelectedComponent(component);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedComponent(null);
  };

  const handleRunTest = (testType: string, dryRun: boolean = true) => {
    if (selectedComponent) {
      testMutation.mutate({
        component: selectedComponent,
        testType,
        dryRun
      });
    }
    handleMenuClose();
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
        return <CheckIcon color="success" fontSize="small" />;
      case 'warning':
        return <WarningIcon color="warning" fontSize="small" />;
      case 'critical':
      case 'failed':
        return <ErrorIcon color="error" fontSize="small" />;
      case 'testing':
        return <ScheduleIcon color="info" fontSize="small" />;
      default:
        return null;
    }
  };

  const getPriorityLabel = (priority: number) => {
    switch (priority) {
      case 1:
        return 'Critical';
      case 2:
        return 'High';
      case 3:
        return 'Medium';
      case 4:
        return 'Low';
      default:
        return 'Unknown';
    }
  };

  const getPriorityColor = (priority: number) => {
    switch (priority) {
      case 1:
        return 'error';
      case 2:
        return 'warning';
      case 3:
        return 'info';
      case 4:
        return 'default';
      default:
        return 'default';
    }
  };

  const formatDuration = (minutes: number) => {
    if (minutes < 60) {
      return `${minutes}m`;
    }
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
  };

  const formatLastTime = (timeString: string | null) => {
    if (!timeString) return 'Never';
    const date = new Date(timeString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) {
      return `${diffDays}d ago`;
    } else if (diffHours > 0) {
      return `${diffHours}h ago`;
    } else {
      return 'Recently';
    }
  };

  if (loading) {
    return (
      <Box>
        <LinearProgress />
        <Typography variant="body2" sx={{ mt: 1, textAlign: 'center' }}>
          Loading DR components...
        </Typography>
      </Box>
    );
  }

  if (!components || components.length === 0) {
    return (
      <Alert severity="info">
        No DR components configured. Please check your disaster recovery setup.
      </Alert>
    );
  }

  return (
    <Box>
      <TableContainer component={Paper} elevation={0}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell />
              <TableCell>Component</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Priority</TableCell>
              <TableCell>RTO</TableCell>
              <TableCell>RPO</TableCell>
              <TableCell>Last Test</TableCell>
              <TableCell>Last Backup</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {components.map((component) => (
              <React.Fragment key={component.component}>
                <TableRow hover>
                  <TableCell>
                    <IconButton
                      size="small"
                      onClick={() => handleExpandRow(component.component)}
                    >
                      {expandedRows.has(component.component) ? (
                        <ExpandLessIcon />
                      ) : (
                        <ExpandMoreIcon />
                      )}
                    </IconButton>
                  </TableCell>
                  <TableCell>
                    <Box display="flex" alignItems="center">
                      <Typography variant="subtitle2" sx={{ fontWeight: 'medium' }}>
                        {component.component.replace('_', ' ').toUpperCase()}
                      </Typography>
                      {component.automated_recovery && (
                        <Chip
                          label="Auto"
                          size="small"
                          color="primary"
                          variant="outlined"
                          sx={{ ml: 1, fontSize: '0.7rem' }}
                        />
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Box display="flex" alignItems="center">
                      {getStatusIcon(component.status)}
                      <Chip
                        label={component.status.toUpperCase()}
                        color={getStatusColor(component.status) as any}
                        size="small"
                        sx={{ ml: 1 }}
                      />
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={getPriorityLabel(component.priority)}
                      color={getPriorityColor(component.priority) as any}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {formatDuration(component.rto_minutes)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {formatDuration(component.rpo_minutes)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography
                      variant="body2"
                      color={component.last_test_time ? 'text.primary' : 'text.secondary'}
                    >
                      {formatLastTime(component.last_test_time)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography
                      variant="body2"
                      color={component.last_backup_time ? 'text.primary' : 'text.secondary'}
                    >
                      {formatLastTime(component.last_backup_time)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Tooltip title="Test Options">
                      <IconButton
                        size="small"
                        onClick={(e) => handleMenuOpen(e, component.component)}
                        disabled={testMutation.isPending}
                      >
                        <MoreVertIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>

                {/* Expanded Row Content */}
                <TableRow>
                  <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={9}>
                    <Collapse in={expandedRows.has(component.component)} timeout="auto" unmountOnExit>
                      <Box sx={{ margin: 2 }}>
                        <Typography variant="h6" gutterBottom component="div">
                          Component Details
                        </Typography>
                        
                        <Box display="flex" gap={4} mb={2}>
                          <Box>
                            <Typography variant="subtitle2" color="text.secondary">
                              Recovery Objectives
                            </Typography>
                            <Typography variant="body2">
                              RTO: {formatDuration(component.rto_minutes)} | RPO: {formatDuration(component.rpo_minutes)}
                            </Typography>
                          </Box>
                          
                          <Box>
                            <Typography variant="subtitle2" color="text.secondary">
                              Automated Recovery
                            </Typography>
                            <Typography variant="body2">
                              {component.automated_recovery ? 'Enabled' : 'Manual intervention required'}
                            </Typography>
                          </Box>
                        </Box>

                        {component.dependencies.length > 0 && (
                          <Box mb={2}>
                            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                              Dependencies
                            </Typography>
                            <Box display="flex" gap={1} flexWrap="wrap">
                              {component.dependencies.map((dep) => (
                                <Chip
                                  key={dep}
                                  label={dep.replace('_', ' ').toUpperCase()}
                                  size="small"
                                  variant="outlined"
                                />
                              ))}
                            </Box>
                          </Box>
                        )}

                        <Box display="flex" gap={1}>
                          <Button
                            size="small"
                            variant="outlined"
                            startIcon={<PlayIcon />}
                            onClick={() => handleRunTest('backup_validation')}
                            disabled={testMutation.isPending}
                          >
                            Validate Backup
                          </Button>
                          <Button
                            size="small"
                            variant="outlined"
                            startIcon={<PlayIcon />}
                            onClick={() => handleRunTest('failover_test')}
                            disabled={testMutation.isPending}
                          >
                            Test Failover
                          </Button>
                          <Button
                            size="small"
                            variant="outlined"
                            startIcon={<PlayIcon />}
                            onClick={() => handleRunTest('recovery_test')}
                            disabled={testMutation.isPending}
                          >
                            Test Recovery
                          </Button>
                        </Box>
                      </Box>
                    </Collapse>
                  </TableCell>
                </TableRow>
              </React.Fragment>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Test Options Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => handleRunTest('backup_validation', true)}>
          Validate Backup (Dry Run)
        </MenuItem>
        <MenuItem onClick={() => handleRunTest('failover_test', true)}>
          Test Failover (Dry Run)
        </MenuItem>
        <MenuItem onClick={() => handleRunTest('recovery_test', true)}>
          Test Recovery (Dry Run)
        </MenuItem>
        <MenuItem onClick={() => handleRunTest('backup_validation', false)} sx={{ color: 'warning.main' }}>
          Validate Backup (Live)
        </MenuItem>
        <MenuItem onClick={() => handleRunTest('failover_test', false)} sx={{ color: 'warning.main' }}>
          Test Failover (Live)
        </MenuItem>
        <MenuItem onClick={() => handleRunTest('recovery_test', false)} sx={{ color: 'warning.main' }}>
          Test Recovery (Live)
        </MenuItem>
      </Menu>
    </Box>
  );
};
