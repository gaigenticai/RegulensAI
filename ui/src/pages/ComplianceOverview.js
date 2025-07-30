import React, { useState, useEffect } from 'react';
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
  LinearProgress,
  Button,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Download,
  Visibility,
  Assessment,
  TrendingUp,
  Warning,
  CheckCircle
} from '@mui/icons-material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';

const ComplianceOverview = () => {
  const [complianceData, setComplianceData] = useState({
    summary: {
      overallScore: 94.2,
      totalChecks: 156,
      passedChecks: 147,
      failedChecks: 9,
      pendingChecks: 0
    },
    recentReports: [
      {
        id: 1,
        name: 'Q2 2024 AML Compliance Report',
        type: 'AML',
        status: 'completed',
        score: 96.5,
        date: '2024-06-30',
        size: '2.4 MB'
      },
      {
        id: 2,
        name: 'KYC Verification Summary',
        type: 'KYC',
        status: 'completed',
        score: 92.1,
        date: '2024-06-28',
        size: '1.8 MB'
      },
      {
        id: 3,
        name: 'Regulatory Change Impact Analysis',
        type: 'Regulatory',
        status: 'in_progress',
        score: null,
        date: '2024-06-25',
        size: null
      },
      {
        id: 4,
        name: 'Risk Assessment Report',
        type: 'Risk',
        status: 'completed',
        score: 89.7,
        date: '2024-06-20',
        size: '3.1 MB'
      }
    ],
    complianceByCategory: [
      { category: 'AML', score: 96, checks: 45, passed: 43 },
      { category: 'KYC', score: 92, checks: 38, passed: 35 },
      { category: 'Risk Management', score: 94, checks: 42, passed: 39 },
      { category: 'Data Privacy', score: 98, checks: 31, passed: 30 }
    ],
    loading: false
  });

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'success';
      case 'in_progress': return 'warning';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return <CheckCircle />;
      case 'in_progress': return <Assessment />;
      case 'failed': return <Warning />;
      default: return <Assessment />;
    }
  };

  const handleDownloadReport = (reportId) => {
    // Implement report download logic
    console.log('Downloading report:', reportId);
  };

  const handleViewReport = (reportId) => {
    // Implement report viewing logic
    console.log('Viewing report:', reportId);
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Compliance Overview
      </Typography>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Overall Score
              </Typography>
              <Typography variant="h4" color="primary">
                {complianceData.summary.overallScore}%
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                <TrendingUp color="success" sx={{ mr: 1 }} />
                <Typography variant="body2" color="success.main">
                  +2.3% from last month
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Checks
              </Typography>
              <Typography variant="h4">
                {complianceData.summary.totalChecks}
              </Typography>
              <LinearProgress
                variant="determinate"
                value={(complianceData.summary.passedChecks / complianceData.summary.totalChecks) * 100}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Passed Checks
              </Typography>
              <Typography variant="h4" color="success.main">
                {complianceData.summary.passedChecks}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                {((complianceData.summary.passedChecks / complianceData.summary.totalChecks) * 100).toFixed(1)}% success rate
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Failed Checks
              </Typography>
              <Typography variant="h4" color="error.main">
                {complianceData.summary.failedChecks}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Requires attention
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Compliance by Category Chart */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Compliance Score by Category
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={complianceData.complianceByCategory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="category" />
                  <YAxis />
                  <RechartsTooltip />
                  <Bar dataKey="score" fill="#1976d2" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Category Details
              </Typography>
              {complianceData.complianceByCategory.map((category) => (
                <Box key={category.category} sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="body2">{category.category}</Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {category.score}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={category.score}
                    sx={{ mt: 0.5 }}
                  />
                  <Typography variant="caption" color="textSecondary">
                    {category.passed}/{category.checks} checks passed
                  </Typography>
                </Box>
              ))}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Recent Reports Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Recent Compliance Reports
          </Typography>
          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Report Name</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Score</TableCell>
                  <TableCell>Date</TableCell>
                  <TableCell>Size</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {complianceData.recentReports.map((report) => (
                  <TableRow key={report.id}>
                    <TableCell>{report.name}</TableCell>
                    <TableCell>
                      <Chip label={report.type} size="small" />
                    </TableCell>
                    <TableCell>
                      <Chip
                        icon={getStatusIcon(report.status)}
                        label={report.status.replace('_', ' ').toUpperCase()}
                        color={getStatusColor(report.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {report.score ? `${report.score}%` : '-'}
                    </TableCell>
                    <TableCell>{report.date}</TableCell>
                    <TableCell>{report.size || '-'}</TableCell>
                    <TableCell>
                      <Tooltip title="View Report">
                        <IconButton
                          size="small"
                          onClick={() => handleViewReport(report.id)}
                        >
                          <Visibility />
                        </IconButton>
                      </Tooltip>
                      {report.status === 'completed' && (
                        <Tooltip title="Download Report">
                          <IconButton
                            size="small"
                            onClick={() => handleDownloadReport(report.id)}
                          >
                            <Download />
                          </IconButton>
                        </Tooltip>
                      )}
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

export default ComplianceOverview;
