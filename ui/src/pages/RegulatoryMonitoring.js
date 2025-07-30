import React, { useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Button,
  TextField,
  InputAdornment,
  IconButton,
  Alert
} from '@mui/material';
import {
  Search,
  Refresh,
  FilterList,
  Notifications,
  Warning,
  Info,
  Error
} from '@mui/icons-material';

const RegulatoryMonitoring = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [regulatoryUpdates] = useState([
    {
      id: 1,
      title: 'Basel III Capital Requirements Update',
      source: 'Basel Committee',
      severity: 'high',
      date: '2024-06-30',
      status: 'new',
      description: 'Updated capital adequacy requirements for banks',
      impact: 'High impact on capital calculations'
    },
    {
      id: 2,
      title: 'GDPR Amendment on Data Processing',
      source: 'European Commission',
      severity: 'medium',
      date: '2024-06-28',
      status: 'reviewed',
      description: 'New guidelines for personal data processing',
      impact: 'Medium impact on data handling procedures'
    },
    {
      id: 3,
      title: 'AML Directive 6 Implementation',
      source: 'EU Parliament',
      severity: 'high',
      date: '2024-06-25',
      status: 'implemented',
      description: 'Enhanced anti-money laundering measures',
      impact: 'High impact on transaction monitoring'
    }
  ]);

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'info';
      default: return 'default';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'new': return 'error';
      case 'reviewed': return 'warning';
      case 'implemented': return 'success';
      default: return 'default';
    }
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Regulatory Monitoring
      </Typography>

      {/* Alert Summary */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Alert severity="error" sx={{ mb: 2 }}>
            <Typography variant="h6">3 High Priority Updates</Typography>
            <Typography variant="body2">Require immediate attention</Typography>
          </Alert>
        </Grid>
        <Grid item xs={12} md={4}>
          <Alert severity="warning">
            <Typography variant="h6">5 Medium Priority Updates</Typography>
            <Typography variant="body2">Review within 7 days</Typography>
          </Alert>
        </Grid>
        <Grid item xs={12} md={4}>
          <Alert severity="info">
            <Typography variant="h6">12 Low Priority Updates</Typography>
            <Typography variant="body2">Monitor for changes</Typography>
          </Alert>
        </Grid>
      </Grid>

      {/* Search and Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <TextField
              placeholder="Search regulatory updates..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search />
                  </InputAdornment>
                ),
              }}
              sx={{ flexGrow: 1 }}
            />
            <Button variant="outlined" startIcon={<FilterList />}>
              Filters
            </Button>
            <IconButton>
              <Refresh />
            </IconButton>
          </Box>
        </CardContent>
      </Card>

      {/* Regulatory Updates Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Recent Regulatory Updates
          </Typography>
          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Title</TableCell>
                  <TableCell>Source</TableCell>
                  <TableCell>Severity</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Date</TableCell>
                  <TableCell>Impact</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {regulatoryUpdates
                  .filter(update => 
                    update.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                    update.source.toLowerCase().includes(searchTerm.toLowerCase())
                  )
                  .map((update) => (
                    <TableRow key={update.id} hover>
                      <TableCell>
                        <Typography variant="subtitle2">{update.title}</Typography>
                        <Typography variant="body2" color="textSecondary">
                          {update.description}
                        </Typography>
                      </TableCell>
                      <TableCell>{update.source}</TableCell>
                      <TableCell>
                        <Chip
                          label={update.severity.toUpperCase()}
                          color={getSeverityColor(update.severity)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={update.status.toUpperCase()}
                          color={getStatusColor(update.status)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{update.date}</TableCell>
                      <TableCell>
                        <Typography variant="body2">{update.impact}</Typography>
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
};

export default RegulatoryMonitoring;
