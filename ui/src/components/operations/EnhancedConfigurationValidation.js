import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Tabs,
  Tab,
  Button,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Paper,
  Switch,
  FormControlLabel,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow
} from '@mui/material';
import {
  ExpandMore,
  ContentCopy,
  PlayArrow,
  Settings,
  Security,
  Storage,
  NetworkCheck,
  CheckCircle,
  Error,
  Warning,
  Info,
  Refresh,
  History,
  Backup,
  Compare,
  Timeline
} from '@mui/icons-material';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';

function TabPanel(props) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`config-tabpanel-${index}`}
      aria-labelledby={`config-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const EnhancedConfigurationValidation = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [validationResults, setValidationResults] = useState({});
  const [configHistory, setConfigHistory] = useState([]);
  const [driftDetection, setDriftDetection] = useState({});
  const [backupDialogOpen, setBackupDialogOpen] = useState(false);
  const [complianceResults, setComplianceResults] = useState({});

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  const runValidation = async (validationType) => {
    setValidationResults(prev => ({
      ...prev,
      [validationType]: { status: 'running', message: 'Validating...' }
    }));

    // Simulate validation
    setTimeout(() => {
      const success = Math.random() > 0.3; // 70% success rate for demo
      setValidationResults(prev => ({
        ...prev,
        [validationType]: { 
          status: success ? 'success' : 'error', 
          message: success ? 'Validation passed' : 'Validation failed',
          details: success ? 'All checks completed successfully' : 'Configuration issues detected'
        }
      }));
    }, 2000);
  };

  const detectDrift = async () => {
    setDriftDetection({ status: 'running', message: 'Detecting configuration drift...' });
    
    setTimeout(() => {
      setDriftDetection({
        status: 'complete',
        message: 'Drift detection completed',
        changes: [
          { component: 'database', field: 'max_connections', expected: '100', actual: '150', severity: 'warning' },
          { component: 'redis', field: 'memory_limit', expected: '2GB', actual: '1.5GB', severity: 'error' },
          { component: 'api', field: 'rate_limit', expected: '1000', actual: '1000', severity: 'ok' }
        ]
      });
    }, 3000);
  };

  // Configuration Drift Detection
  const ConfigurationDriftDetection = () => (
    <Box>
      <Typography variant="h5" gutterBottom>
        Configuration Drift Detection
      </Typography>
      
      <Alert severity="info" sx={{ mb: 3 }}>
        Monitor and detect changes in your RegulensAI configuration that may impact system behavior.
      </Alert>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Drift Detection Status
              </Typography>
              <Box display="flex" alignItems="center" gap={2} mb={2}>
                <Button
                  variant="contained"
                  startIcon={<Compare />}
                  onClick={detectDrift}
                  disabled={driftDetection.status === 'running'}
                >
                  {driftDetection.status === 'running' ? 'Detecting...' : 'Detect Drift'}
                </Button>
                <Chip 
                  label={driftDetection.status || 'Not Run'} 
                  color={driftDetection.status === 'complete' ? 'success' : 'default'}
                />
              </Box>
              
              {driftDetection.status === 'running' && (
                <LinearProgress sx={{ mb: 2 }} />
              )}
              
              {driftDetection.changes && (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Component</TableCell>
                        <TableCell>Field</TableCell>
                        <TableCell>Expected</TableCell>
                        <TableCell>Actual</TableCell>
                        <TableCell>Status</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {driftDetection.changes.map((change, index) => (
                        <TableRow key={index}>
                          <TableCell>{change.component}</TableCell>
                          <TableCell>{change.field}</TableCell>
                          <TableCell>{change.expected}</TableCell>
                          <TableCell>{change.actual}</TableCell>
                          <TableCell>
                            <Chip 
                              size="small"
                              label={change.severity}
                              color={
                                change.severity === 'ok' ? 'success' :
                                change.severity === 'warning' ? 'warning' : 'error'
                              }
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Automated Drift Monitoring
              </Typography>
              <Typography variant="body2" paragraph>
                Configure automated monitoring to detect configuration changes in real-time.
              </Typography>
              
              <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                <SyntaxHighlighter language="yaml" style={tomorrow}>
{`# drift-monitor-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: drift-monitor-config
data:
  schedule: "0 */6 * * *"  # Every 6 hours
  components:
    - database
    - redis
    - api_services
    - monitoring
  notifications:
    slack_webhook: "https://hooks.slack.com/..."
    email_alerts: true
  thresholds:
    warning: 5   # 5% deviation
    critical: 10 # 10% deviation`}
                </SyntaxHighlighter>
              </Paper>

              <Box mt={2}>
                <FormControlLabel
                  control={<Switch defaultChecked />}
                  label="Enable Real-time Monitoring"
                />
                <FormControlLabel
                  control={<Switch defaultChecked />}
                  label="Send Slack Notifications"
                />
                <FormControlLabel
                  control={<Switch />}
                  label="Auto-remediation"
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );

  // Configuration Backup & Versioning
  const ConfigurationBackupVersioning = () => (
    <Box>
      <Typography variant="h5" gutterBottom>
        Configuration Backup & Versioning
      </Typography>
      
      <Alert severity="success" sx={{ mb: 3 }}>
        Maintain version history and automated backups of your RegulensAI configuration.
      </Alert>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Configuration History
              </Typography>
              
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Version</TableCell>
                      <TableCell>Timestamp</TableCell>
                      <TableCell>Changes</TableCell>
                      <TableCell>Author</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell>v1.2.3</TableCell>
                      <TableCell>2024-01-15 14:30:00</TableCell>
                      <TableCell>
                        <Chip size="small" label="Database config" color="primary" />
                        <Chip size="small" label="Redis settings" color="secondary" sx={{ ml: 1 }} />
                      </TableCell>
                      <TableCell>admin@regulens.ai</TableCell>
                      <TableCell>
                        <Button size="small" startIcon={<History />}>Restore</Button>
                        <Button size="small" startIcon={<Compare />}>Compare</Button>
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>v1.2.2</TableCell>
                      <TableCell>2024-01-14 09:15:00</TableCell>
                      <TableCell>
                        <Chip size="small" label="API rate limits" color="warning" />
                      </TableCell>
                      <TableCell>ops@regulens.ai</TableCell>
                      <TableCell>
                        <Button size="small" startIcon={<History />}>Restore</Button>
                        <Button size="small" startIcon={<Compare />}>Compare</Button>
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>v1.2.1</TableCell>
                      <TableCell>2024-01-13 16:45:00</TableCell>
                      <TableCell>
                        <Chip size="small" label="Security settings" color="error" />
                        <Chip size="small" label="Monitoring" color="info" sx={{ ml: 1 }} />
                      </TableCell>
                      <TableCell>security@regulens.ai</TableCell>
                      <TableCell>
                        <Button size="small" startIcon={<History />}>Restore</Button>
                        <Button size="small" startIcon={<Compare />}>Compare</Button>
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Backup Management
              </Typography>
              
              <Box mb={2}>
                <Button
                  variant="contained"
                  fullWidth
                  startIcon={<Backup />}
                  onClick={() => setBackupDialogOpen(true)}
                  sx={{ mb: 1 }}
                >
                  Create Backup
                </Button>
                <Button
                  variant="outlined"
                  fullWidth
                  startIcon={<Refresh />}
                  sx={{ mb: 1 }}
                >
                  Restore from Backup
                </Button>
              </Box>

              <Typography variant="subtitle2" gutterBottom>
                Automated Backup Schedule
              </Typography>
              <Paper sx={{ p: 2, bgcolor: 'grey.50', mb: 2 }}>
                <Typography variant="body2">
                  • Daily: 02:00 UTC<br/>
                  • Weekly: Sunday 01:00 UTC<br/>
                  • Monthly: 1st day 00:00 UTC<br/>
                  • Before deployments: Automatic
                </Typography>
              </Paper>

              <Typography variant="subtitle2" gutterBottom>
                Retention Policy
              </Typography>
              <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                <Typography variant="body2">
                  • Daily backups: 30 days<br/>
                  • Weekly backups: 12 weeks<br/>
                  • Monthly backups: 12 months<br/>
                  • Deployment backups: 6 months
                </Typography>
              </Paper>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );

  // Configuration Compliance Scanning
  const ConfigurationComplianceScanning = () => (
    <Box>
      <Typography variant="h5" gutterBottom>
        Configuration Compliance Scanning
      </Typography>
      
      <Alert severity="warning" sx={{ mb: 3 }}>
        Ensure your RegulensAI configuration meets security and compliance requirements.
      </Alert>

      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Compliance Frameworks
              </Typography>
              
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} md={3}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" color="primary">SOC 2</Typography>
                      <Typography variant="body2">Security & Availability</Typography>
                      <Box mt={1}>
                        <Chip label="98% Compliant" color="success" size="small" />
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} md={3}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" color="primary">ISO 27001</Typography>
                      <Typography variant="body2">Information Security</Typography>
                      <Box mt={1}>
                        <Chip label="95% Compliant" color="success" size="small" />
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} md={3}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" color="primary">GDPR</Typography>
                      <Typography variant="body2">Data Protection</Typography>
                      <Box mt={1}>
                        <Chip label="92% Compliant" color="warning" size="small" />
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} md={3}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" color="primary">PCI DSS</Typography>
                      <Typography variant="body2">Payment Security</Typography>
                      <Box mt={1}>
                        <Chip label="89% Compliant" color="warning" size="small" />
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              <Typography variant="h6" gutterBottom>
                Compliance Scan Results
              </Typography>
              
              <Accordion defaultExpanded>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="subtitle1">Security Configuration</Typography>
                  <Chip label="3 Issues" color="warning" size="small" sx={{ ml: 2 }} />
                </AccordionSummary>
                <AccordionDetails>
                  <List>
                    <ListItem>
                      <ListItemIcon><Warning color="warning" /></ListItemIcon>
                      <ListItemText 
                        primary="Weak password policy detected"
                        secondary="Minimum password length should be 12 characters"
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><Error color="error" /></ListItemIcon>
                      <ListItemText 
                        primary="TLS version 1.1 still enabled"
                        secondary="Disable TLS 1.1 and enforce TLS 1.2+ only"
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><Warning color="warning" /></ListItemIcon>
                      <ListItemText 
                        primary="Session timeout too long"
                        secondary="Reduce session timeout to 30 minutes maximum"
                      />
                    </ListItem>
                  </List>
                </AccordionDetails>
              </Accordion>

              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="subtitle1">Data Protection</Typography>
                  <Chip label="1 Issue" color="warning" size="small" sx={{ ml: 2 }} />
                </AccordionSummary>
                <AccordionDetails>
                  <List>
                    <ListItem>
                      <ListItemIcon><Warning color="warning" /></ListItemIcon>
                      <ListItemText 
                        primary="Backup encryption not enabled"
                        secondary="Enable encryption for all backup files"
                      />
                    </ListItem>
                  </List>
                </AccordionDetails>
              </Accordion>

              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="subtitle1">Access Control</Typography>
                  <Chip label="Compliant" color="success" size="small" sx={{ ml: 2 }} />
                </AccordionSummary>
                <AccordionDetails>
                  <Typography variant="body2" color="success.main">
                    All access control configurations meet compliance requirements.
                  </Typography>
                </AccordionDetails>
              </Accordion>

              <Box mt={3}>
                <Button
                  variant="contained"
                  startIcon={<Security />}
                  onClick={() => runValidation('compliance-scan')}
                  sx={{ mr: 2 }}
                >
                  Run Full Compliance Scan
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<ContentCopy />}
                >
                  Export Report
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );

  return (
    <Box sx={{ width: '100%' }}>
      <Typography variant="h4" gutterBottom>
        Enhanced Configuration Validation
      </Typography>
      
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab} onChange={handleTabChange} aria-label="configuration validation tabs">
          <Tab icon={<Compare />} label="Drift Detection" />
          <Tab icon={<Backup />} label="Backup & Versioning" />
          <Tab icon={<Security />} label="Compliance Scanning" />
        </Tabs>
      </Box>

      <TabPanel value={activeTab} index={0}>
        <ConfigurationDriftDetection />
      </TabPanel>

      <TabPanel value={activeTab} index={1}>
        <ConfigurationBackupVersioning />
      </TabPanel>

      <TabPanel value={activeTab} index={2}>
        <ConfigurationComplianceScanning />
      </TabPanel>

      {/* Backup Dialog */}
      <Dialog open={backupDialogOpen} onClose={() => setBackupDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create Configuration Backup</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Backup Name"
            placeholder="manual-backup-2024-01-15"
            margin="normal"
          />
          <TextField
            fullWidth
            label="Description"
            placeholder="Pre-deployment backup"
            margin="normal"
            multiline
            rows={3}
          />
          <FormControl fullWidth margin="normal">
            <InputLabel>Backup Type</InputLabel>
            <Select defaultValue="full">
              <MenuItem value="full">Full Configuration</MenuItem>
              <MenuItem value="security">Security Settings Only</MenuItem>
              <MenuItem value="database">Database Configuration</MenuItem>
              <MenuItem value="api">API Configuration</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBackupDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={() => setBackupDialogOpen(false)}>Create Backup</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default EnhancedConfigurationValidation;
