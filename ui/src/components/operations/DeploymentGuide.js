import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Button,
  Checkbox,
  FormControlLabel,
  Alert,
  Chip,
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
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemIcon,
  ListItemText
} from '@mui/material';
import {
  ExpandMore,
  ContentCopy,
  PlayArrow,
  CheckCircle,
  Error,
  Warning,
  Info,
  Refresh,
  Timeline,
  Storage,
  Security,
  CloudUpload
} from '@mui/icons-material';

const DeploymentGuide = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [environment, setEnvironment] = useState('staging');
  const [deploymentProgress, setDeploymentProgress] = useState({});
  const [checkedItems, setCheckedItems] = useState({});
  const [showCommandDialog, setShowCommandDialog] = useState(false);
  const [selectedCommand, setSelectedCommand] = useState('');
  const [deploymentStatus, setDeploymentStatus] = useState('idle');

  const deploymentSteps = [
    {
      label: 'Pre-deployment Validation',
      description: 'Verify prerequisites and system readiness',
      icon: <Security />,
      tasks: [
        { id: 'security-scan', label: 'Run security scan on container images', required: true },
        { id: 'k8s-access', label: 'Verify Kubernetes cluster access', required: true },
        { id: 'db-backup', label: 'Create database backup', required: true },
        { id: 'secrets-check', label: 'Validate secrets and configurations', required: true }
      ],
      commands: [
        {
          name: 'Security Scan',
          command: 'docker run --rm aquasec/trivy image regulensai:latest',
          description: 'Scan container for vulnerabilities'
        },
        {
          name: 'Kubernetes Access',
          command: 'kubectl cluster-info',
          description: 'Verify cluster connectivity'
        }
      ]
    },
    {
      label: 'Database Migration',
      description: 'Apply database schema changes',
      icon: <Storage />,
      tasks: [
        { id: 'db-connect', label: 'Test database connectivity', required: true },
        { id: 'migration-dry-run', label: 'Run migration dry-run', required: true },
        { id: 'apply-migrations', label: 'Apply database migrations', required: true },
        { id: 'verify-schema', label: 'Verify schema deployment', required: true }
      ],
      commands: [
        {
          name: 'Database Connection Test',
          command: `psql $${environment.toUpperCase()}_DB_URL -c "SELECT 1;"`,
          description: 'Test database connectivity'
        },
        {
          name: 'Migration Dry Run',
          command: `python core_infra/database/migrate.py --database-url $${environment.toUpperCase()}_DB_URL --dry-run`,
          description: 'Preview migration changes'
        },
        {
          name: 'Apply Migrations',
          command: `python core_infra/database/migrate.py --database-url $${environment.toUpperCase()}_DB_URL`,
          description: 'Apply database migrations'
        }
      ]
    },
    {
      label: 'Application Deployment',
      description: 'Deploy application services',
      icon: <CloudUpload />,
      tasks: [
        { id: 'namespace-setup', label: 'Create/update namespace', required: true },
        { id: 'secrets-deploy', label: 'Deploy secrets and configs', required: true },
        { id: 'app-deploy', label: 'Deploy application services', required: true },
        { id: 'health-check', label: 'Verify application health', required: true }
      ],
      commands: [
        {
          name: 'Create Namespace',
          command: `kubectl create namespace regulensai-${environment} --dry-run=client -o yaml | kubectl apply -f -`,
          description: 'Create or update namespace'
        },
        {
          name: 'Deploy Application',
          command: `helm upgrade --install regulensai ./helm/regulensai --namespace regulensai-${environment} --values ./helm/regulensai/values-${environment}.yaml`,
          description: 'Deploy using Helm'
        }
      ]
    },
    {
      label: 'Post-deployment Validation',
      description: 'Verify deployment success',
      icon: <CheckCircle />,
      tasks: [
        { id: 'endpoint-test', label: 'Test API endpoints', required: true },
        { id: 'db-performance', label: 'Verify database performance', required: true },
        { id: 'monitoring-setup', label: 'Configure monitoring alerts', required: false },
        { id: 'documentation', label: 'Update deployment documentation', required: false }
      ],
      commands: [
        {
          name: 'Health Check',
          command: `curl -f https://${environment}.regulens.ai/api/v1/health`,
          description: 'Test API health endpoint'
        },
        {
          name: 'Authentication Test',
          command: `curl -X POST https://${environment}.regulens.ai/api/v1/auth/login -H "Content-Type: application/json" -d '{"email": "admin@regulens.ai", "password": "admin123"}'`,
          description: 'Test authentication flow'
        }
      ]
    }
  ];

  const handleStepClick = (step) => {
    setActiveStep(step);
  };

  const handleTaskCheck = (stepIndex, taskId) => {
    const key = `${stepIndex}-${taskId}`;
    setCheckedItems(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const executeCommand = async (command) => {
    setSelectedCommand(command);
    setShowCommandDialog(true);
  };

  const getStepProgress = (stepIndex) => {
    const step = deploymentSteps[stepIndex];
    const completedTasks = step.tasks.filter(task => 
      checkedItems[`${stepIndex}-${task.id}`]
    ).length;
    return (completedTasks / step.tasks.length) * 100;
  };

  const isStepComplete = (stepIndex) => {
    const step = deploymentSteps[stepIndex];
    const requiredTasks = step.tasks.filter(task => task.required);
    return requiredTasks.every(task => checkedItems[`${stepIndex}-${task.id}`]);
  };

  const getOverallProgress = () => {
    const completedSteps = deploymentSteps.filter((_, index) => isStepComplete(index)).length;
    return (completedSteps / deploymentSteps.length) * 100;
  };

  return (
    <Box>
      {/* Environment Selection and Progress */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <FormControl fullWidth>
            <InputLabel>Environment</InputLabel>
            <Select
              value={environment}
              label="Environment"
              onChange={(e) => setEnvironment(e.target.value)}
            >
              <MenuItem value="staging">Staging</MenuItem>
              <MenuItem value="production">Production</MenuItem>
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} md={8}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2">Overall Progress:</Typography>
            <LinearProgress 
              variant="determinate" 
              value={getOverallProgress()} 
              sx={{ flexGrow: 1, height: 8, borderRadius: 4 }}
            />
            <Typography variant="body2">{Math.round(getOverallProgress())}%</Typography>
          </Box>
        </Grid>
      </Grid>

      {/* Deployment Status Alert */}
      {environment === 'production' && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          <Typography variant="subtitle2">Production Deployment</Typography>
          You are deploying to production. Ensure all staging validations are complete and follow the blue-green deployment process.
        </Alert>
      )}

      {/* Deployment Steps */}
      <Stepper activeStep={activeStep} orientation="vertical">
        {deploymentSteps.map((step, index) => (
          <Step key={step.label}>
            <StepLabel 
              onClick={() => handleStepClick(index)}
              sx={{ cursor: 'pointer' }}
              icon={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {step.icon}
                  {isStepComplete(index) && <CheckCircle color="success" fontSize="small" />}
                </Box>
              }
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Typography variant="h6">{step.label}</Typography>
                <Chip 
                  label={`${Math.round(getStepProgress(index))}%`}
                  size="small"
                  color={isStepComplete(index) ? 'success' : 'default'}
                />
              </Box>
            </StepLabel>
            <StepContent>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {step.description}
              </Typography>

              {/* Tasks Checklist */}
              <Card variant="outlined" sx={{ mb: 2 }}>
                <CardContent>
                  <Typography variant="subtitle2" gutterBottom>
                    Tasks Checklist
                  </Typography>
                  <List dense>
                    {step.tasks.map((task) => (
                      <ListItem key={task.id} sx={{ py: 0.5 }}>
                        <ListItemIcon>
                          <FormControlLabel
                            control={
                              <Checkbox
                                checked={checkedItems[`${index}-${task.id}`] || false}
                                onChange={() => handleTaskCheck(index, task.id)}
                                size="small"
                              />
                            }
                            label=""
                          />
                        </ListItemIcon>
                        <ListItemText 
                          primary={task.label}
                          secondary={task.required ? 'Required' : 'Optional'}
                        />
                        {task.required && (
                          <Chip label="Required" size="small" color="error" />
                        )}
                      </ListItem>
                    ))}
                  </List>
                </CardContent>
              </Card>

              {/* Commands */}
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="subtitle2">Commands & Scripts</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  {step.commands.map((cmd, cmdIndex) => (
                    <Card key={cmdIndex} variant="outlined" sx={{ mb: 1 }}>
                      <CardContent sx={{ py: 1 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                          <Typography variant="subtitle2">{cmd.name}</Typography>
                          <Box>
                            <Tooltip title="Copy Command">
                              <IconButton size="small" onClick={() => copyToClipboard(cmd.command)}>
                                <ContentCopy fontSize="small" />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Execute">
                              <IconButton size="small" onClick={() => executeCommand(cmd)}>
                                <PlayArrow fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </Box>
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
                  ))}
                </AccordionDetails>
              </Accordion>

              <Box sx={{ mt: 2 }}>
                <Button
                  variant="contained"
                  onClick={() => setActiveStep(index + 1)}
                  disabled={!isStepComplete(index) || index === deploymentSteps.length - 1}
                  sx={{ mr: 1 }}
                >
                  {index === deploymentSteps.length - 1 ? 'Complete' : 'Next Step'}
                </Button>
                <Button
                  disabled={index === 0}
                  onClick={() => setActiveStep(index - 1)}
                >
                  Back
                </Button>
              </Box>
            </StepContent>
          </Step>
        ))}
      </Stepper>

      {/* Command Execution Dialog */}
      <Dialog open={showCommandDialog} onClose={() => setShowCommandDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Execute Command</DialogTitle>
        <DialogContent>
          <Typography variant="subtitle2" gutterBottom>
            {selectedCommand.name}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {selectedCommand.description}
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={3}
            value={selectedCommand.command}
            variant="outlined"
            InputProps={{
              readOnly: true,
              sx: { fontFamily: 'monospace' }
            }}
          />
          <Alert severity="info" sx={{ mt: 2 }}>
            Copy this command and execute it in your terminal. Monitor the output for any errors.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => copyToClipboard(selectedCommand.command)}>
            Copy Command
          </Button>
          <Button onClick={() => setShowCommandDialog(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DeploymentGuide;
