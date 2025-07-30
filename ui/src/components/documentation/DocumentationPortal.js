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
  Chip,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Paper,
  Breadcrumbs,
  Link
} from '@mui/material';
import {
  Api,
  CloudUpload,
  Settings,
  Security,
  Speed,
  Webhook,
  Language,
  Compare,
  Backup,
  Timeline,
  Home,
  NavigateNext
} from '@mui/icons-material';

import EnhancedAPIDocumentation from './EnhancedAPIDocumentation';
import EnhancedDeploymentGuide from '../operations/EnhancedDeploymentGuide';
import EnhancedConfigurationValidation from '../operations/EnhancedConfigurationValidation';

function TabPanel(props) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`portal-tabpanel-${index}`}
      aria-labelledby={`portal-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const DocumentationPortal = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [breadcrumbs, setBreadcrumbs] = useState(['Documentation']);

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
    
    // Update breadcrumbs based on active tab
    const tabNames = ['Overview', 'API Documentation', 'Deployment Guides', 'Configuration Management'];
    setBreadcrumbs(['Documentation', tabNames[newValue]]);
  };

  // Documentation Overview
  const DocumentationOverview = () => (
    <Box>
      <Typography variant="h4" gutterBottom>
        RegulensAI Documentation Portal
      </Typography>
      
      <Typography variant="body1" paragraph>
        Welcome to the comprehensive RegulensAI documentation portal. Access interactive guides, 
        API documentation, deployment procedures, and configuration management tools.
      </Typography>

      <Alert severity="info" sx={{ mb: 4 }}>
        All documentation is interactive and integrated into the RegulensAI web interface. 
        Use the tabs above to navigate between different sections.
      </Alert>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%', cursor: 'pointer' }} onClick={() => setActiveTab(1)}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Api color="primary" sx={{ mr: 2, fontSize: 32 }} />
                <Typography variant="h5">API Documentation</Typography>
              </Box>
              <Typography variant="body2" paragraph>
                Enhanced interactive API documentation with OAuth2/SAML examples, 
                rate limiting guides, webhook configuration, and SDK examples.
              </Typography>
              <Box>
                <Chip label="OAuth2/SAML" size="small" sx={{ mr: 1, mb: 1 }} />
                <Chip label="Rate Limiting" size="small" sx={{ mr: 1, mb: 1 }} />
                <Chip label="Webhooks" size="small" sx={{ mr: 1, mb: 1 }} />
                <Chip label="SDK Examples" size="small" sx={{ mr: 1, mb: 1 }} />
              </Box>
              <Typography variant="body2" color="primary" sx={{ mt: 2 }}>
                Click to explore →
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%', cursor: 'pointer' }} onClick={() => setActiveTab(2)}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <CloudUpload color="primary" sx={{ mr: 2, fontSize: 32 }} />
                <Typography variant="h5">Deployment Guides</Typography>
              </Box>
              <Typography variant="body2" paragraph>
                Cloud-specific deployment guides for AWS EKS, Google GKE, Azure AKS, 
                and comprehensive disaster recovery procedures.
              </Typography>
              <Box>
                <Chip label="AWS EKS" size="small" sx={{ mr: 1, mb: 1 }} />
                <Chip label="Google GKE" size="small" sx={{ mr: 1, mb: 1 }} />
                <Chip label="Azure AKS" size="small" sx={{ mr: 1, mb: 1 }} />
                <Chip label="Disaster Recovery" size="small" sx={{ mr: 1, mb: 1 }} />
              </Box>
              <Typography variant="body2" color="primary" sx={{ mt: 2 }}>
                Click to explore →
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%', cursor: 'pointer' }} onClick={() => setActiveTab(3)}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Settings color="primary" sx={{ mr: 2, fontSize: 32 }} />
                <Typography variant="h5">Configuration Management</Typography>
              </Box>
              <Typography variant="body2" paragraph>
                Advanced configuration validation with drift detection, backup & versioning, 
                and compliance scanning capabilities.
              </Typography>
              <Box>
                <Chip label="Drift Detection" size="small" sx={{ mr: 1, mb: 1 }} />
                <Chip label="Backup & Versioning" size="small" sx={{ mr: 1, mb: 1 }} />
                <Chip label="Compliance Scanning" size="small" sx={{ mr: 1, mb: 1 }} />
              </Box>
              <Typography variant="body2" color="primary" sx={{ mt: 2 }}>
                Click to explore →
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Timeline color="primary" sx={{ mr: 2, fontSize: 32 }} />
                <Typography variant="h5">Quick Links</Typography>
              </Box>
              <List dense>
                <ListItem button>
                  <ListItemIcon><Api /></ListItemIcon>
                  <ListItemText primary="Interactive Swagger UI" secondary="Test APIs directly" />
                </ListItem>
                <ListItem button>
                  <ListItemIcon><Security /></ListItemIcon>
                  <ListItemText primary="Security Configuration" secondary="Authentication & authorization" />
                </ListItem>
                <ListItem button>
                  <ListItemIcon><Speed /></ListItemIcon>
                  <ListItemText primary="Performance Monitoring" secondary="APM and metrics" />
                </ListItem>
                <ListItem button>
                  <ListItemIcon><Backup /></ListItemIcon>
                  <ListItemText primary="Disaster Recovery" secondary="Backup and failover procedures" />
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Box mt={4}>
        <Typography variant="h6" gutterBottom>
          Recent Updates
        </Typography>
        <Paper sx={{ p: 2 }}>
          <List>
            <ListItem>
              <ListItemText 
                primary="Enhanced API Documentation" 
                secondary="Added OAuth2/SAML authentication examples and webhook configuration guides"
              />
              <Chip label="New" color="success" size="small" />
            </ListItem>
            <Divider />
            <ListItem>
              <ListItemText 
                primary="Cloud Deployment Guides" 
                secondary="Added comprehensive guides for AWS EKS, Google GKE, and Azure AKS"
              />
              <Chip label="New" color="success" size="small" />
            </ListItem>
            <Divider />
            <ListItem>
              <ListItemText 
                primary="Configuration Drift Detection" 
                secondary="Implemented automated configuration monitoring and compliance scanning"
              />
              <Chip label="New" color="success" size="small" />
            </ListItem>
          </List>
        </Paper>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ width: '100%' }}>
      {/* Breadcrumbs */}
      <Breadcrumbs 
        separator={<NavigateNext fontSize="small" />} 
        sx={{ mb: 2 }}
        aria-label="breadcrumb"
      >
        <Link
          underline="hover"
          color="inherit"
          href="#"
          onClick={() => setActiveTab(0)}
          sx={{ display: 'flex', alignItems: 'center' }}
        >
          <Home sx={{ mr: 0.5 }} fontSize="inherit" />
          Documentation
        </Link>
        {breadcrumbs.slice(1).map((crumb, index) => (
          <Typography key={index} color="text.primary">
            {crumb}
          </Typography>
        ))}
      </Breadcrumbs>

      {/* Main Navigation Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs 
          value={activeTab} 
          onChange={handleTabChange} 
          aria-label="documentation portal tabs"
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab icon={<Home />} label="Overview" />
          <Tab icon={<Api />} label="API Documentation" />
          <Tab icon={<CloudUpload />} label="Deployment Guides" />
          <Tab icon={<Settings />} label="Configuration Management" />
        </Tabs>
      </Box>

      {/* Tab Content */}
      <TabPanel value={activeTab} index={0}>
        <DocumentationOverview />
      </TabPanel>

      <TabPanel value={activeTab} index={1}>
        <EnhancedAPIDocumentation />
      </TabPanel>

      <TabPanel value={activeTab} index={2}>
        <EnhancedDeploymentGuide />
      </TabPanel>

      <TabPanel value={activeTab} index={3}>
        <EnhancedConfigurationValidation />
      </TabPanel>
    </Box>
  );
};

export default DocumentationPortal;
