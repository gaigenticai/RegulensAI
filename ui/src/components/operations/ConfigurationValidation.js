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
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Collapse,
  useTheme,
  Fade,
  Stack,
} from '@mui/material';
import { useResponsive } from '../../hooks/useResponsive';
import { ResponsiveContainer, ResponsiveGrid, ResponsiveFlex } from '../common/ResponsiveContainer';
import { LoadingSpinner, CardSkeleton, FadeInContent } from '../common/LoadingComponents';
import { ResponsiveTable } from '../common/ResponsiveTable';
import {
  CheckCircle,
  Error,
  Warning,
  Info,
  Refresh,
  Settings,
  ExpandMore,
  ExpandLess,
  Security,
  Storage,
  CloudUpload,
  Psychology,
  MonitorHeart,
  Folder,
  ContentCopy
} from '@mui/icons-material';

const ConfigurationValidation = () => {
  const theme = useTheme();
  const { isMobile, isTablet, getCurrentBreakpoint } = useResponsive();

  const [validationResults, setValidationResults] = useState(null);
  const [configSummary, setConfigSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showDetails, setShowDetails] = useState({});
  const [showSummaryDialog, setShowSummaryDialog] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);

  useEffect(() => {
    runValidation();
  }, []);

  const runValidation = async (includeSummary = false) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/operations/configuration/validate?include_summary=${includeSummary}`);
      if (response.ok) {
        const data = await response.json();
        setValidationResults(data);
        if (data.summary) {
          setConfigSummary(data.summary);
        }
      } else {
        const error = await response.json();
        console.error('Validation failed:', error);
      }
    } catch (error) {
      console.error('Failed to run validation:', error);
    } finally {
      setLoading(false);
      setInitialLoading(false);
    }
  };

  const reloadConfiguration = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/operations/configuration/reload', {
        method: 'POST'
      });
      if (response.ok) {
        await runValidation();
      }
    } catch (error) {
      console.error('Failed to reload configuration:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'passed': return 'success';
      case 'failed': return 'error';
      case 'warning': return 'warning';
      default: return 'default';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'passed': return <CheckCircle color="success" />;
      case 'failed': return <Error color="error" />;
      case 'warning': return <Warning color="warning" />;
      default: return <Info />;
    }
  };

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'database': return <Storage />;
      case 'redis': return <Memory />;
      case 'external_services': return <CloudUpload />;
      case 'security': return <Security />;
      case 'filesystem': return <Folder />;
      case 'ai_services': return <Psychology />;
      default: return <Settings />;
    }
  };

  const toggleDetails = (category) => {
    setShowDetails(prev => ({
      ...prev,
      [category]: !prev[category]
    }));
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  if (initialLoading) {
    return (
      <Box>
        <LoadingSpinner message="Loading configuration validation..." />
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <ResponsiveFlex
        direction={{ xs: 'column', sm: 'row' }}
        justify="space-between"
        align={{ xs: 'stretch', sm: 'center' }}
        sx={{ mb: 4 }}
      >
        <Box sx={{ mb: { xs: 2, sm: 0 } }}>
          <Typography variant={isMobile ? "h6" : "h5"} fontWeight="bold">
            Configuration Validation
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Validate system configuration and settings
          </Typography>
        </Box>

        <ResponsiveFlex
          direction={{ xs: 'column', sm: 'row' }}
          spacing={1}
        >
          <Button
            startIcon={<Settings />}
            onClick={() => setShowSummaryDialog(true)}
            variant="outlined"
            size={isMobile ? "medium" : "small"}
            fullWidth={isMobile}
          >
            {isMobile ? "Summary" : "View Summary"}
          </Button>
          <Button
            startIcon={<Refresh />}
            onClick={() => runValidation(true)}
            disabled={loading}
            variant="contained"
            size={isMobile ? "medium" : "small"}
            fullWidth={isMobile}
          >
            {loading ? "Validating..." : "Validate"}
          </Button>
          <Button
            startIcon={<Refresh />}
            onClick={reloadConfiguration}
            disabled={loading}
            variant="outlined"
            size={isMobile ? "medium" : "small"}
            fullWidth={isMobile}
          >
            {isMobile ? "Reload" : "Reload Config"}
          </Button>
        </ResponsiveFlex>
      </ResponsiveFlex>

      {/* Overall Status */}
      <FadeInContent loading={loading} skeleton={<CardSkeleton height={{ xs: 160, sm: 180 }} />}>
        <Card
          sx={{
            mb: 4,
            transition: 'all 0.2s ease-in-out',
            '&:hover': {
              transform: 'translateY(-2px)',
              boxShadow: theme.shadows[4],
            }
          }}
        >
          <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
            <ResponsiveFlex
              direction={{ xs: 'column', sm: 'row' }}
              align={{ xs: 'flex-start', sm: 'center' }}
              spacing={2}
              sx={{ mb: 2 }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {getStatusIcon(validationResults?.overall_status)}
                <Typography variant={isMobile ? "subtitle1" : "h6"} fontWeight="bold">
                  Overall Status: {validationResults?.overall_status?.toUpperCase()}
                </Typography>
              </Box>

              <Chip
                label={validationResults?.environment?.toUpperCase()}
                color="primary"
                size={isMobile ? "medium" : "small"}
              />
            </ResponsiveFlex>

            {validationResults?.overall_status === 'failed' && (
              <Alert
                severity="error"
                sx={{
                  mb: 2,
                  '& .MuiAlert-message': {
                    fontSize: { xs: '0.875rem', sm: '1rem' }
                  }
                }}
              >
                Configuration validation failed. Please review the issues below and fix them before deployment.
              </Alert>
            )}

            {validationResults?.overall_status === 'passed' && (
              <Alert
                severity="success"
                sx={{
                  mb: 2,
                  '& .MuiAlert-message': {
                    fontSize: { xs: '0.875rem', sm: '1rem' }
                  }
                }}
              >
                All configuration validations passed successfully. System is ready for deployment.
              </Alert>
            )}

            <Typography variant="body2" color="text.secondary">
              Last validated: {validationResults?.timestamp ? new Date(validationResults.timestamp).toLocaleString() : 'Never'}
            </Typography>
          </CardContent>
        </Card>
      </FadeInContent>

      {/* Validation Results */}
      <FadeInContent
        loading={loading}
        skeleton={
          <ResponsiveGrid spacing={{ xs: 2, sm: 3 }}>
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <CardSkeleton key={i} height={{ xs: 200, sm: 240 }} />
            ))}
          </ResponsiveGrid>
        }
      >
        <ResponsiveGrid spacing={{ xs: 2, sm: 3, md: 4 }}>
          {validationResults?.validations && Object.entries(validationResults.validations).map(([category, result]) => (
            <Card
              key={category}
              sx={{
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  transform: 'translateY(-2px)',
                  boxShadow: theme.shadows[4],
                }
              }}
            >
              <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
                <ResponsiveFlex
                  justify="space-between"
                  align="center"
                  sx={{ mb: 2 }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {getCategoryIcon(category)}
                    <Typography
                      variant={isMobile ? "subtitle1" : "h6"}
                      sx={{ textTransform: 'capitalize' }}
                      fontWeight="bold"
                    >
                      {category.replace('_', ' ')}
                    </Typography>
                  </Box>

                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Chip
                      icon={getStatusIcon(result.status)}
                      label={result.status.toUpperCase()}
                      color={getStatusColor(result.status)}
                      size={isMobile ? "medium" : "small"}
                    />
                    <IconButton
                      size="small"
                      onClick={() => toggleDetails(category)}
                      sx={{
                        transition: 'transform 0.2s ease-in-out',
                        transform: showDetails[category] ? 'rotate(180deg)' : 'rotate(0deg)',
                      }}
                    >
                      <ExpandMore />
                    </IconButton>
                  </Box>
                </ResponsiveFlex>

                <Collapse in={showDetails[category]}>
                  {/* Errors */}
                  {result.errors && result.errors.length > 0 && (
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="subtitle2" color="error" gutterBottom>
                        Errors:
                      </Typography>
                      <List dense>
                        {result.errors.map((error, index) => (
                          <ListItem key={index}>
                            <ListItemIcon>
                              <Error color="error" fontSize="small" />
                            </ListItemIcon>
                            <ListItemText primary={error} />
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                  )}

                  {/* Warnings */}
                  {result.warnings && result.warnings.length > 0 && (
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="subtitle2" color="warning.main" gutterBottom>
                        Warnings:
                      </Typography>
                      <List dense>
                        {result.warnings.map((warning, index) => (
                          <ListItem key={index}>
                            <ListItemIcon>
                              <Warning color="warning" fontSize="small" />
                            </ListItemIcon>
                            <ListItemText primary={warning} />
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                  )}

                  {/* Detailed Checks */}
                  {result.checks && Object.keys(result.checks).length > 0 && (
                    <Box>
                      <Typography variant="subtitle2" gutterBottom>
                        Detailed Checks:
                      </Typography>
                      {Object.entries(result.checks).map(([checkName, checkResult]) => (
                        <Box key={checkName} sx={{ mb: 1 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {getStatusIcon(checkResult.status)}
                            <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                              {checkName.replace('_', ' ')}
                            </Typography>
                          </Box>
                          {checkResult.message && (
                            <Typography variant="body2" color="text.secondary" sx={{ ml: 4 }}>
                              {checkResult.message}
                            </Typography>
                          )}
                          {checkResult.suggestions && (
                            <List dense sx={{ ml: 2 }}>
                              {checkResult.suggestions.map((suggestion, index) => (
                                <ListItem key={index}>
                                  <ListItemText 
                                    primary={suggestion}
                                    primaryTypographyProps={{ variant: 'body2', color: 'text.secondary' }}
                                  />
                                </ListItem>
                              ))}
                            </List>
                          )}
                        </Box>
                      ))}
                    </Box>
                  )}
                </Collapse>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Configuration Summary Dialog */}
      <Dialog open={showSummaryDialog} onClose={() => setShowSummaryDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Configuration Summary</DialogTitle>
        <DialogContent>
          {configSummary ? (
            <TableContainer component={Paper}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Category</TableCell>
                    <TableCell>Setting</TableCell>
                    <TableCell>Value</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {Object.entries(configSummary).map(([category, settings]) => (
                    Object.entries(settings).map(([key, value]) => (
                      <TableRow key={`${category}-${key}`}>
                        <TableCell sx={{ textTransform: 'capitalize' }}>
                          {category.replace('_', ' ')}
                        </TableCell>
                        <TableCell>{key.replace('_', ' ')}</TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Tooltip title="Copy Value">
                            <IconButton 
                              size="small" 
                              onClick={() => copyToClipboard(String(value))}
                            >
                              <ContentCopy fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Typography>No configuration summary available. Run validation with summary option.</Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowSummaryDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ConfigurationValidation;
