import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Alert,
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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import {
  Storage,
  PlayArrow,
  Refresh,
  CheckCircle,
  Error,
  Warning,
  Info,
  ContentCopy,
  Backup,
  Restore,
  Timeline,
  ExpandMore,
  Speed,
  Security
} from '@mui/icons-material';

const DatabaseOperations = () => {
  const [migrationStatus, setMigrationStatus] = useState({
    applied: [],
    pending: [],
    available: [],
    upToDate: false
  });
  const [dbHealth, setDbHealth] = useState({
    status: 'unknown',
    connections: 0,
    size: '0 MB',
    lastBackup: null,
    performance: {}
  });
  const [showMigrationDialog, setShowMigrationDialog] = useState(false);
  const [showBackupDialog, setShowBackupDialog] = useState(false);
  const [selectedEnvironment, setSelectedEnvironment] = useState('staging');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchMigrationStatus();
    fetchDatabaseHealth();
  }, [selectedEnvironment]);

  const fetchMigrationStatus = async () => {
    try {
      const response = await fetch(`/api/v1/operations/database/migrations?env=${selectedEnvironment}`);
      if (response.ok) {
        const data = await response.json();
        setMigrationStatus(data);
      }
    } catch (error) {
      console.error('Failed to fetch migration status:', error);
    }
  };

  const fetchDatabaseHealth = async () => {
    try {
      const response = await fetch(`/api/v1/operations/database/health?env=${selectedEnvironment}`);
      if (response.ok) {
        const data = await response.json();
        setDbHealth(data);
      }
    } catch (error) {
      console.error('Failed to fetch database health:', error);
    }
  };

  const runMigration = async (migrationName = null) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/operations/database/migrate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          environment: selectedEnvironment,
          migration: migrationName,
          dryRun: false
        })
      });
      
      if (response.ok) {
        await fetchMigrationStatus();
        setShowMigrationDialog(false);
      }
    } catch (error) {
      console.error('Migration failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const createBackup = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/operations/database/backup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          environment: selectedEnvironment,
          type: 'full'
        })
      });
      
      if (response.ok) {
        await fetchDatabaseHealth();
        setShowBackupDialog(false);
      }
    } catch (error) {
      console.error('Backup failed:', error);
    } finally {
      setLoading(false);
    }
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

  const migrationCommands = [
    {
      name: 'Check Migration Status',
      command: `python core_infra/database/migrate.py --database-url $${selectedEnvironment.toUpperCase()}_DB_URL --status`,
      description: 'Check current migration status'
    },
    {
      name: 'Dry Run Migration',
      command: `python core_infra/database/migrate.py --database-url $${selectedEnvironment.toUpperCase()}_DB_URL --dry-run`,
      description: 'Preview migration changes without applying'
    },
    {
      name: 'Apply All Migrations',
      command: `python core_infra/database/migrate.py --database-url $${selectedEnvironment.toUpperCase()}_DB_URL`,
      description: 'Apply all pending migrations'
    },
    {
      name: 'Rollback Last Migration',
      command: `python core_infra/database/migrate.py --database-url $${selectedEnvironment.toUpperCase()}_DB_URL --rollback last`,
      description: 'Rollback the most recent migration'
    }
  ];

  const performanceQueries = [
    {
      name: 'Slow Queries',
      query: 'SELECT query, total_time, calls, mean_time FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;',
      description: 'Find the slowest queries'
    },
    {
      name: 'Table Sizes',
      query: 'SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||\'.\' ||tablename)) as size FROM pg_tables WHERE schemaname = \'public\' ORDER BY pg_total_relation_size(schemaname||\'.\' ||tablename) DESC;',
      description: 'Show table sizes'
    },
    {
      name: 'Index Usage',
      query: 'SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch FROM pg_stat_user_indexes WHERE idx_scan > 0 ORDER BY idx_scan DESC;',
      description: 'Check index usage statistics'
    },
    {
      name: 'Active Connections',
      query: 'SELECT count(*), state FROM pg_stat_activity GROUP BY state;',
      description: 'Monitor active database connections'
    }
  ];

  return (
    <Box>
      {/* Environment Selection */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <FormControl fullWidth>
            <InputLabel>Environment</InputLabel>
            <Select
              value={selectedEnvironment}
              label="Environment"
              onChange={(e) => setSelectedEnvironment(e.target.value)}
            >
              <MenuItem value="staging">Staging</MenuItem>
              <MenuItem value="production">Production</MenuItem>
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} md={8}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2">Database Status:</Typography>
            {getStatusIcon(dbHealth.status)}
            <Chip
              label={dbHealth.status.toUpperCase()}
              color={getStatusColor(dbHealth.status)}
              size="small"
            />
            <Button
              startIcon={<Refresh />}
              onClick={() => {
                fetchMigrationStatus();
                fetchDatabaseHealth();
              }}
              size="small"
            >
              Refresh
            </Button>
          </Box>
        </Grid>
      </Grid>

      {/* Database Health Overview */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Storage color="primary" sx={{ fontSize: 40, mb: 1 }} />
              <Typography variant="h6">Database Size</Typography>
              <Typography variant="h4" color="primary">
                {dbHealth.size}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Timeline color="primary" sx={{ fontSize: 40, mb: 1 }} />
              <Typography variant="h6">Active Connections</Typography>
              <Typography variant="h4" color="primary">
                {dbHealth.connections}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Backup color="primary" sx={{ fontSize: 40, mb: 1 }} />
              <Typography variant="h6">Last Backup</Typography>
              <Typography variant="body2" color="text.secondary">
                {dbHealth.lastBackup ? new Date(dbHealth.lastBackup).toLocaleDateString() : 'Never'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Speed color="primary" sx={{ fontSize: 40, mb: 1 }} />
              <Typography variant="h6">Performance</Typography>
              <Chip
                label={dbHealth.performance.status || 'Good'}
                color="success"
                size="small"
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Migration Status */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">Migration Status</Typography>
            <Box>
              <Button
                startIcon={<PlayArrow />}
                onClick={() => setShowMigrationDialog(true)}
                disabled={migrationStatus.upToDate}
                sx={{ mr: 1 }}
              >
                Run Migrations
              </Button>
              <Button
                startIcon={<Backup />}
                onClick={() => setShowBackupDialog(true)}
              >
                Create Backup
              </Button>
            </Box>
          </Box>

          {migrationStatus.upToDate ? (
            <Alert severity="success">
              Database schema is up to date. No pending migrations.
            </Alert>
          ) : (
            <Alert severity="warning">
              {migrationStatus.pending.length} pending migration(s) found.
            </Alert>
          )}

          <TableContainer component={Paper} sx={{ mt: 2 }}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Migration</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Applied Date</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {migrationStatus.applied.map((migration) => (
                  <TableRow key={migration.name}>
                    <TableCell>{migration.name}</TableCell>
                    <TableCell>
                      <Chip label="Applied" color="success" size="small" />
                    </TableCell>
                    <TableCell>{new Date(migration.appliedAt).toLocaleString()}</TableCell>
                    <TableCell>
                      <Button size="small" disabled>
                        Rollback
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {migrationStatus.pending.map((migration) => (
                  <TableRow key={migration}>
                    <TableCell>{migration}</TableCell>
                    <TableCell>
                      <Chip label="Pending" color="warning" size="small" />
                    </TableCell>
                    <TableCell>-</TableCell>
                    <TableCell>
                      <Button
                        size="small"
                        onClick={() => runMigration(migration)}
                        disabled={loading}
                      >
                        Apply
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Database Commands */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Migration Commands</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            {migrationCommands.map((cmd, index) => (
              <Grid item xs={12} md={6} key={index}>
                <Card variant="outlined">
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="subtitle2">{cmd.name}</Typography>
                      <Tooltip title="Copy Command">
                        <IconButton size="small" onClick={() => navigator.clipboard.writeText(cmd.command)}>
                          <ContentCopy fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {cmd.description}
                    </Typography>
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
              </Grid>
            ))}
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Performance Queries */}
      <Accordion sx={{ mt: 2 }}>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Performance Analysis Queries</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            {performanceQueries.map((query, index) => (
              <Grid item xs={12} md={6} key={index}>
                <Card variant="outlined">
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="subtitle2">{query.name}</Typography>
                      <Tooltip title="Copy Query">
                        <IconButton size="small" onClick={() => navigator.clipboard.writeText(query.query)}>
                          <ContentCopy fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {query.description}
                    </Typography>
                    <Box sx={{ 
                      backgroundColor: 'grey.100', 
                      p: 1, 
                      borderRadius: 1, 
                      fontFamily: 'monospace',
                      fontSize: '0.875rem',
                      overflow: 'auto'
                    }}>
                      {query.query}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Migration Dialog */}
      <Dialog open={showMigrationDialog} onClose={() => setShowMigrationDialog(false)}>
        <DialogTitle>Run Database Migration</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This will apply all pending migrations to the {selectedEnvironment} database.
            Ensure you have a recent backup before proceeding.
          </Alert>
          <Typography variant="body2">
            Pending migrations: {migrationStatus.pending.length}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowMigrationDialog(false)}>Cancel</Button>
          <Button onClick={() => runMigration()} disabled={loading} variant="contained">
            {loading ? 'Running...' : 'Run Migrations'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Backup Dialog */}
      <Dialog open={showBackupDialog} onClose={() => setShowBackupDialog(false)}>
        <DialogTitle>Create Database Backup</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Create a full backup of the {selectedEnvironment} database.
          </Typography>
          <Alert severity="info">
            The backup will be stored in the configured backup location and can be used for disaster recovery.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowBackupDialog(false)}>Cancel</Button>
          <Button onClick={createBackup} disabled={loading} variant="contained">
            {loading ? 'Creating...' : 'Create Backup'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DatabaseOperations;
