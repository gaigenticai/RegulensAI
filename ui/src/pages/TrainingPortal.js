import React from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  LinearProgress,
  Chip,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText
} from '@mui/material';
import {
  School,
  PlayArrow,
  CheckCircle,
  Schedule,
  Assessment,
  Certificate
} from '@mui/icons-material';

const TrainingPortal = () => {
  const trainingModules = [
    {
      id: 1,
      title: 'AML Fundamentals',
      description: 'Learn the basics of Anti-Money Laundering regulations',
      progress: 100,
      status: 'completed',
      duration: '2 hours',
      certificate: true
    },
    {
      id: 2,
      title: 'KYC Procedures',
      description: 'Know Your Customer verification processes',
      progress: 75,
      status: 'in_progress',
      duration: '1.5 hours',
      certificate: false
    },
    {
      id: 3,
      title: 'Risk Management',
      description: 'Understanding and managing financial risks',
      progress: 0,
      status: 'not_started',
      duration: '3 hours',
      certificate: false
    },
    {
      id: 4,
      title: 'Regulatory Compliance',
      description: 'Staying compliant with financial regulations',
      progress: 50,
      status: 'in_progress',
      duration: '2.5 hours',
      certificate: false
    }
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'success';
      case 'in_progress': return 'warning';
      case 'not_started': return 'default';
      default: return 'default';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return <CheckCircle />;
      case 'in_progress': return <Schedule />;
      case 'not_started': return <PlayArrow />;
      default: return <PlayArrow />;
    }
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Training Portal
      </Typography>

      {/* Training Overview */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <School color="primary" sx={{ fontSize: 48, mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                Overall Progress
              </Typography>
              <Typography variant="h4" color="primary">
                56%
              </Typography>
              <LinearProgress variant="determinate" value={56} sx={{ mt: 2 }} />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Certificate color="success" sx={{ fontSize: 48, mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                Certificates Earned
              </Typography>
              <Typography variant="h4" color="success.main">
                3
              </Typography>
              <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                Out of 8 available
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Assessment color="info" sx={{ fontSize: 48, mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                Average Score
              </Typography>
              <Typography variant="h4" color="info.main">
                87%
              </Typography>
              <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                Across all assessments
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Training Modules */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Available Training Modules
          </Typography>
          <List>
            {trainingModules.map((module) => (
              <ListItem key={module.id} sx={{ mb: 2, border: 1, borderColor: 'divider', borderRadius: 1 }}>
                <ListItemAvatar>
                  <Avatar sx={{ bgcolor: 'primary.main' }}>
                    {getStatusIcon(module.status)}
                  </Avatar>
                </ListItemAvatar>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="h6">{module.title}</Typography>
                      <Chip
                        label={module.status.replace('_', ' ').toUpperCase()}
                        color={getStatusColor(module.status)}
                        size="small"
                      />
                      {module.certificate && (
                        <Chip
                          icon={<Certificate />}
                          label="Certified"
                          color="success"
                          size="small"
                        />
                      )}
                    </Box>
                  }
                  secondary={
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="body2" color="textSecondary" gutterBottom>
                        {module.description}
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        Duration: {module.duration}
                      </Typography>
                      <Box sx={{ mt: 1, mb: 1 }}>
                        <LinearProgress
                          variant="determinate"
                          value={module.progress}
                          sx={{ height: 8, borderRadius: 4 }}
                        />
                        <Typography variant="caption" color="textSecondary">
                          {module.progress}% Complete
                        </Typography>
                      </Box>
                    </Box>
                  }
                />
                <Box sx={{ ml: 2 }}>
                  <Button
                    variant={module.status === 'not_started' ? 'contained' : 'outlined'}
                    startIcon={module.status === 'completed' ? <CheckCircle /> : <PlayArrow />}
                    disabled={module.status === 'completed'}
                  >
                    {module.status === 'completed' ? 'Completed' : 
                     module.status === 'in_progress' ? 'Continue' : 'Start'}
                  </Button>
                </Box>
              </ListItem>
            ))}
          </List>
        </CardContent>
      </Card>
    </Box>
  );
};

export default TrainingPortal;
