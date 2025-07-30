import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  TextField,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Button,
  Alert,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
  InputAdornment
} from '@mui/material';
import {
  ExpandMore,
  Search,
  Error,
  Warning,
  Info,
  CheckCircle,
  ContentCopy,
  PlayArrow,
  Storage,
  CloudUpload,
  Security,
  MonitorHeart,
  NetworkCheck,
  BugReport
} from '@mui/icons-material';

const TroubleshootingGuide = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState(0);
  const [expandedPanel, setExpandedPanel] = useState(false);
  const [showSolutionDialog, setShowSolutionDialog] = useState(false);
  const [selectedSolution, setSelectedSolution] = useState(null);

  const troubleshootingCategories = [
    { label: 'All Issues', icon: <BugReport /> },
    { label: 'Database', icon: <Storage /> },
    { label: 'API Services', icon: <CloudUpload /> },
    { label: 'Authentication', icon: <Security /> },
    { label: 'Monitoring', icon: <MonitorHeart /> },
    { label: 'Network', icon: <NetworkCheck /> }
  ];

  const troubleshootingIssues = [
    {
      id: 'db-connection-failed',
      category: 'Database',
      severity: 'error',
      title: 'Database Connection Failed',
      symptoms: [
        'Application pods failing to start',
        'Connection timeout errors in logs',
        'Health check endpoints returning 500 errors'
      ],
      causes: [
        'Incorrect database URL or credentials',
        'Database server is down or unreachable',
        'Network connectivity issues',
        'Connection pool exhausted'
      ],
      solutions: [
        {
          title: 'Verify Database Connectivity',
          steps: [
            'Check database server status',
            'Verify network connectivity',
            'Test credentials manually'
          ],
          commands: [
            'kubectl get pods -n database',
            'nc -zv database-host 5432',
            'psql $DATABASE_URL -c "SELECT 1;"'
          ]
        },
        {
          title: 'Check Connection Pool Settings',
          steps: [
            'Review connection pool configuration',
            'Monitor active connections',
            'Adjust pool size if needed'
          ],
          commands: [
            'kubectl logs deployment/regulensai-api | grep "connection pool"',
            'psql $DATABASE_URL -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"'
          ]
        }
      ]
    },
    {
      id: 'migration-failed',
      category: 'Database',
      severity: 'error',
      title: 'Database Migration Failed',
      symptoms: [
        'Migration script errors in logs',
        'Schema version mismatch',
        'Application startup failures'
      ],
      causes: [
        'Conflicting schema changes',
        'Insufficient database permissions',
        'Data integrity constraints violated',
        'Migration script syntax errors'
      ],
      solutions: [
        {
          title: 'Rollback and Retry Migration',
          steps: [
            'Identify failed migration',
            'Rollback to previous version',
            'Fix migration script',
            'Retry migration'
          ],
          commands: [
            'python migrate.py --status',
            'python migrate.py --rollback migration_name',
            'python migrate.py --dry-run',
            'python migrate.py'
          ]
        }
      ]
    },
    {
      id: 'api-high-latency',
      category: 'API Services',
      severity: 'warning',
      title: 'High API Response Times',
      symptoms: [
        'Slow response times (>2 seconds)',
        'Timeout errors from clients',
        'High CPU usage on API pods'
      ],
      causes: [
        'Database query performance issues',
        'Insufficient resources allocated',
        'Memory leaks or garbage collection issues',
        'External service dependencies slow'
      ],
      solutions: [
        {
          title: 'Database Query Optimization',
          steps: [
            'Identify slow queries',
            'Check missing indexes',
            'Analyze query execution plans'
          ],
          commands: [
            'psql $DATABASE_URL -c "SELECT query, total_time, calls FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"',
            'psql $DATABASE_URL -c "SELECT schemaname, tablename, attname, n_distinct, correlation FROM pg_stats WHERE schemaname = \'public\';"'
          ]
        },
        {
          title: 'Resource Scaling',
          steps: [
            'Check current resource usage',
            'Scale API pods horizontally',
            'Increase resource limits'
          ],
          commands: [
            'kubectl top pods -n regulensai-prod',
            'kubectl scale deployment regulensai-api --replicas=5',
            'kubectl patch deployment regulensai-api -p \'{"spec":{"template":{"spec":{"containers":[{"name":"api","resources":{"limits":{"memory":"2Gi","cpu":"1000m"}}}]}}}}\''
          ]
        }
      ]
    },
    {
      id: 'auth-token-invalid',
      category: 'Authentication',
      severity: 'error',
      title: 'Authentication Token Issues',
      symptoms: [
        '401 Unauthorized errors',
        'Token validation failures',
        'Users unable to login'
      ],
      causes: [
        'JWT secret key mismatch',
        'Token expiration issues',
        'Clock synchronization problems',
        'Corrupted token payload'
      ],
      solutions: [
        {
          title: 'Verify JWT Configuration',
          steps: [
            'Check JWT secret consistency',
            'Verify token expiration settings',
            'Test token generation and validation'
          ],
          commands: [
            'kubectl get secret regulensai-secrets -o yaml | grep jwt-secret',
            'kubectl logs deployment/regulensai-api | grep "JWT"'
          ]
        }
      ]
    },
    {
      id: 'monitoring-alerts-not-firing',
      category: 'Monitoring',
      severity: 'warning',
      title: 'Monitoring Alerts Not Firing',
      symptoms: [
        'No alerts received during known issues',
        'Prometheus targets down',
        'Grafana dashboards showing no data'
      ],
      causes: [
        'Prometheus configuration issues',
        'Alert manager not configured',
        'Network connectivity to monitoring targets',
        'Incorrect alert rule definitions'
      ],
      solutions: [
        {
          title: 'Check Prometheus Configuration',
          steps: [
            'Verify Prometheus targets',
            'Check alert rule syntax',
            'Test alert manager connectivity'
          ],
          commands: [
            'kubectl port-forward svc/prometheus-server 9090:80',
            'curl http://localhost:9090/api/v1/targets',
            'kubectl logs deployment/prometheus-alertmanager'
          ]
        }
      ]
    }
  ];

  const handleCategoryChange = (event, newValue) => {
    setSelectedCategory(newValue);
  };

  const handleAccordionChange = (panel) => (event, isExpanded) => {
    setExpandedPanel(isExpanded ? panel : false);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const showSolution = (solution) => {
    setSelectedSolution(solution);
    setShowSolutionDialog(true);
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'error': return 'error';
      case 'warning': return 'warning';
      case 'info': return 'info';
      default: return 'default';
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'error': return <Error />;
      case 'warning': return <Warning />;
      case 'info': return <Info />;
      default: return <CheckCircle />;
    }
  };

  const filteredIssues = troubleshootingIssues.filter(issue => {
    const matchesSearch = searchTerm === '' || 
      issue.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      issue.symptoms.some(symptom => symptom.toLowerCase().includes(searchTerm.toLowerCase())) ||
      issue.causes.some(cause => cause.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesCategory = selectedCategory === 0 || 
      issue.category === troubleshootingCategories[selectedCategory].label;
    
    return matchesSearch && matchesCategory;
  });

  return (
    <Box>
      {/* Search and Filter */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={8}>
          <TextField
            fullWidth
            placeholder="Search issues, symptoms, or solutions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
            }}
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <Typography variant="body2" color="text.secondary">
            Found {filteredIssues.length} issue(s)
          </Typography>
        </Grid>
      </Grid>

      {/* Category Tabs */}
      <Tabs value={selectedCategory} onChange={handleCategoryChange} sx={{ mb: 3 }}>
        {troubleshootingCategories.map((category, index) => (
          <Tab
            key={index}
            icon={category.icon}
            label={category.label}
            iconPosition="start"
          />
        ))}
      </Tabs>

      {/* Issues List */}
      {filteredIssues.length === 0 ? (
        <Alert severity="info">
          No issues found matching your search criteria.
        </Alert>
      ) : (
        filteredIssues.map((issue) => (
          <Accordion
            key={issue.id}
            expanded={expandedPanel === issue.id}
            onChange={handleAccordionChange(issue.id)}
            sx={{ mb: 2 }}
          >
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                {getSeverityIcon(issue.severity)}
                <Typography variant="h6" sx={{ flexGrow: 1 }}>
                  {issue.title}
                </Typography>
                <Chip
                  label={issue.severity.toUpperCase()}
                  color={getSeverityColor(issue.severity)}
                  size="small"
                />
                <Chip
                  label={issue.category}
                  variant="outlined"
                  size="small"
                />
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={3}>
                {/* Symptoms */}
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    Symptoms
                  </Typography>
                  <List dense>
                    {issue.symptoms.map((symptom, index) => (
                      <ListItem key={index}>
                        <ListItemIcon>
                          <Error color="error" fontSize="small" />
                        </ListItemIcon>
                        <ListItemText primary={symptom} />
                      </ListItem>
                    ))}
                  </List>
                </Grid>

                {/* Possible Causes */}
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    Possible Causes
                  </Typography>
                  <List dense>
                    {issue.causes.map((cause, index) => (
                      <ListItem key={index}>
                        <ListItemIcon>
                          <Warning color="warning" fontSize="small" />
                        </ListItemIcon>
                        <ListItemText primary={cause} />
                      </ListItem>
                    ))}
                  </List>
                </Grid>

                {/* Solutions */}
                <Grid item xs={12}>
                  <Typography variant="subtitle2" gutterBottom>
                    Solutions
                  </Typography>
                  <Grid container spacing={2}>
                    {issue.solutions.map((solution, index) => (
                      <Grid item xs={12} md={6} key={index}>
                        <Card variant="outlined">
                          <CardContent>
                            <Typography variant="subtitle2" gutterBottom>
                              {solution.title}
                            </Typography>
                            <List dense>
                              {solution.steps.map((step, stepIndex) => (
                                <ListItem key={stepIndex}>
                                  <ListItemIcon>
                                    <CheckCircle color="success" fontSize="small" />
                                  </ListItemIcon>
                                  <ListItemText primary={step} />
                                </ListItem>
                              ))}
                            </List>
                            <Button
                              variant="outlined"
                              size="small"
                              onClick={() => showSolution(solution)}
                              startIcon={<PlayArrow />}
                            >
                              View Commands
                            </Button>
                          </CardContent>
                        </Card>
                      </Grid>
                    ))}
                  </Grid>
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>
        ))
      )}

      {/* Solution Commands Dialog */}
      <Dialog open={showSolutionDialog} onClose={() => setShowSolutionDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {selectedSolution?.title}
        </DialogTitle>
        <DialogContent>
          <Typography variant="subtitle2" gutterBottom>
            Commands to Execute:
          </Typography>
          {selectedSolution?.commands.map((command, index) => (
            <Card key={index} variant="outlined" sx={{ mb: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Step {index + 1}
                  </Typography>
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
          <Alert severity="warning">
            Execute these commands in order and monitor the output. Stop if any command fails and investigate the error.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowSolutionDialog(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TroubleshootingGuide;
