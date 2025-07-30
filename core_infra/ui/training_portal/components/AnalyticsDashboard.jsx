import React, { useState, useEffect, useContext } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Paper,
  LinearProgress,
  CircularProgress,
  Chip,
  Avatar,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Analytics,
  TrendingUp,
  TrendingDown,
  Schedule,
  CheckCircle,
  Star,
  School,
  Assignment,
  Quiz,
  Certificate,
  Speed,
  Timeline,
  PieChart,
  BarChart,
  Download,
  Refresh,
  DateRange
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart as RechartsBarChart,
  Bar,
  PieChart as RechartsPieChart,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { format, subDays, startOfWeek, endOfWeek } from 'date-fns';
import { AuthContext } from '../../contexts/AuthContext';
import { TrainingAPI } from '../../services/TrainingAPI';

const AnalyticsDashboard = ({ enrollments }) => {
  const { user } = useContext(AuthContext);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState('30d');
  const [selectedMetric, setSelectedMetric] = useState('progress');

  useEffect(() => {
    loadAnalytics();
  }, [dateRange]);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      
      const endDate = new Date();
      let startDate;
      
      switch (dateRange) {
        case '7d':
          startDate = subDays(endDate, 7);
          break;
        case '30d':
          startDate = subDays(endDate, 30);
          break;
        case '90d':
          startDate = subDays(endDate, 90);
          break;
        default:
          startDate = subDays(endDate, 30);
      }
      
      const analyticsData = await TrainingAPI.getUserAnalytics(user.id, {
        start: startDate.toISOString(),
        end: endDate.toISOString()
      });
      
      setAnalytics(analyticsData);
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const calculateOverallProgress = () => {
    if (!enrollments.length) return 0;
    const totalProgress = enrollments.reduce((sum, e) => sum + (e.completion_percentage || 0), 0);
    return Math.round(totalProgress / enrollments.length);
  };

  const getCompletionStats = () => {
    const completed = enrollments.filter(e => e.status === 'completed').length;
    const inProgress = enrollments.filter(e => e.status === 'in_progress').length;
    const notStarted = enrollments.filter(e => e.status === 'enrolled').length;
    
    return { completed, inProgress, notStarted, total: enrollments.length };
  };

  const getTimeSpentStats = () => {
    const totalTime = enrollments.reduce((sum, e) => sum + (e.total_time_spent_minutes || 0), 0);
    const avgTime = enrollments.length > 0 ? Math.round(totalTime / enrollments.length) : 0;
    
    return { totalTime, avgTime };
  };

  const getProgressTrend = () => {
    if (!analytics?.progress_history) return [];
    
    return analytics.progress_history.map(item => ({
      date: format(new Date(item.date), 'MMM dd'),
      progress: item.completion_percentage,
      timeSpent: item.time_spent_minutes
    }));
  };

  const getCategoryBreakdown = () => {
    const categories = {};
    
    enrollments.forEach(enrollment => {
      const category = enrollment.module_category || 'Other';
      if (!categories[category]) {
        categories[category] = { completed: 0, total: 0 };
      }
      categories[category].total++;
      if (enrollment.status === 'completed') {
        categories[category].completed++;
      }
    });
    
    return Object.entries(categories).map(([name, data]) => ({
      name,
      completed: data.completed,
      total: data.total,
      percentage: Math.round((data.completed / data.total) * 100)
    }));
  };

  const getAchievementStats = () => {
    const stats = getCompletionStats();
    const timeStats = getTimeSpentStats();
    
    return [
      {
        title: 'Modules Completed',
        value: stats.completed,
        total: stats.total,
        icon: <CheckCircle color="success" />,
        color: 'success.main'
      },
      {
        title: 'Average Score',
        value: analytics?.average_score || 0,
        suffix: '%',
        icon: <Star color="warning" />,
        color: 'warning.main'
      },
      {
        title: 'Time Invested',
        value: Math.round(timeStats.totalTime / 60),
        suffix: 'h',
        icon: <Schedule color="primary" />,
        color: 'primary.main'
      },
      {
        title: 'Certificates Earned',
        value: analytics?.certificates_earned || 0,
        icon: <Certificate color="secondary" />,
        color: 'secondary.main'
      }
    ];
  };

  const pieChartData = getCategoryBreakdown().map((item, index) => ({
    ...item,
    fill: ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#8dd1e1'][index % 5]
  }));

  const progressTrendData = getProgressTrend();

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" gutterBottom>
          <Analytics sx={{ mr: 1, verticalAlign: 'middle' }} />
          My Learning Analytics
        </Typography>
        
        <Box display="flex" gap={2} alignItems="center">
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Time Period</InputLabel>
            <Select
              value={dateRange}
              label="Time Period"
              onChange={(e) => setDateRange(e.target.value)}
            >
              <MenuItem value="7d">Last 7 days</MenuItem>
              <MenuItem value="30d">Last 30 days</MenuItem>
              <MenuItem value="90d">Last 90 days</MenuItem>
            </Select>
          </FormControl>
          
          <IconButton onClick={loadAnalytics}>
            <Refresh />
          </IconButton>
          
          <Button
            variant="outlined"
            startIcon={<Download />}
            onClick={() => {/* Generate report */}}
          >
            Export Report
          </Button>
        </Box>
      </Box>

      {/* Key Metrics */}
      <Grid container spacing={3} mb={4}>
        {getAchievementStats().map((stat, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography variant="h4" color={stat.color}>
                      {stat.value}{stat.suffix || ''}
                      {stat.total && (
                        <Typography component="span" variant="h6" color="textSecondary">
                          /{stat.total}
                        </Typography>
                      )}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      {stat.title}
                    </Typography>
                  </Box>
                  <Avatar sx={{ bgcolor: stat.color, opacity: 0.1 }}>
                    {stat.icon}
                  </Avatar>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Progress Overview */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Learning Progress Trend
              </Typography>
              
              {progressTrendData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={progressTrendData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <RechartsTooltip />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="progress"
                      stroke="#8884d8"
                      fill="#8884d8"
                      fillOpacity={0.3}
                      name="Progress %"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <Box textAlign="center" py={4}>
                  <Typography color="textSecondary">
                    No progress data available for the selected period
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Overall Progress
              </Typography>
              
              <Box display="flex" alignItems="center" justifyContent="center" mb={3}>
                <Box position="relative" display="inline-flex">
                  <CircularProgress
                    variant="determinate"
                    value={calculateOverallProgress()}
                    size={120}
                    thickness={4}
                  />
                  <Box
                    position="absolute"
                    top={0}
                    left={0}
                    bottom={0}
                    right={0}
                    display="flex"
                    alignItems="center"
                    justifyContent="center"
                  >
                    <Typography variant="h4" component="div" color="primary">
                      {calculateOverallProgress()}%
                    </Typography>
                  </Box>
                </Box>
              </Box>
              
              <Box>
                {Object.entries(getCompletionStats()).map(([key, value]) => (
                  key !== 'total' && (
                    <Box key={key} display="flex" justifyContent="space-between" mb={1}>
                      <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                        {key.replace(/([A-Z])/g, ' $1').trim()}:
                      </Typography>
                      <Typography variant="body2" fontWeight="bold">
                        {value}
                      </Typography>
                    </Box>
                  )
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Category Breakdown */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Progress by Category
              </Typography>
              
              {pieChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <RechartsPieChart>
                    <RechartsPieChart
                      data={pieChartData}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      dataKey="completed"
                    >
                      {pieChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </RechartsPieChart>
                    <RechartsTooltip />
                    <Legend />
                  </RechartsPieChart>
                </ResponsiveContainer>
              ) : (
                <Box textAlign="center" py={4}>
                  <Typography color="textSecondary">
                    No category data available
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Activity
              </Typography>
              
              <List>
                {enrollments
                  .filter(e => e.last_accessed_at)
                  .sort((a, b) => new Date(b.last_accessed_at) - new Date(a.last_accessed_at))
                  .slice(0, 5)
                  .map((enrollment) => (
                    <ListItem key={enrollment.id}>
                      <ListItemIcon>
                        {enrollment.status === 'completed' ? (
                          <CheckCircle color="success" />
                        ) : (
                          <Schedule color="primary" />
                        )}
                      </ListItemIcon>
                      <ListItemText
                        primary={enrollment.module_title}
                        secondary={`Last accessed ${format(new Date(enrollment.last_accessed_at), 'MMM dd, yyyy')}`}
                      />
                      <Chip
                        label={`${enrollment.completion_percentage || 0}%`}
                        size="small"
                        color={enrollment.status === 'completed' ? 'success' : 'primary'}
                      />
                    </ListItem>
                  ))}
              </List>
              
              {enrollments.filter(e => e.last_accessed_at).length === 0 && (
                <Box textAlign="center" py={4}>
                  <Typography color="textSecondary">
                    No recent activity
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Detailed Statistics */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Detailed Statistics
          </Typography>
          
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" gutterBottom>
                Learning Velocity
              </Typography>
              <Box display="flex" alignItems="center" mb={2}>
                <Speed sx={{ mr: 1, color: 'primary.main' }} />
                <Typography variant="body2">
                  Average completion time: {getTimeSpentStats().avgTime} minutes per module
                </Typography>
              </Box>
              
              <Typography variant="subtitle2" gutterBottom>
                Consistency Score
              </Typography>
              <Box display="flex" alignItems="center" mb={2}>
                <Timeline sx={{ mr: 1, color: 'success.main' }} />
                <Typography variant="body2">
                  Learning streak: {analytics?.learning_streak || 0} days
                </Typography>
              </Box>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" gutterBottom>
                Performance Trends
              </Typography>
              <Box display="flex" alignItems="center" mb={2}>
                {analytics?.performance_trend === 'improving' ? (
                  <TrendingUp sx={{ mr: 1, color: 'success.main' }} />
                ) : (
                  <TrendingDown sx={{ mr: 1, color: 'warning.main' }} />
                )}
                <Typography variant="body2">
                  Performance is {analytics?.performance_trend || 'stable'}
                </Typography>
              </Box>
              
              <Typography variant="subtitle2" gutterBottom>
                Engagement Level
              </Typography>
              <Box display="flex" alignItems="center" mb={2}>
                <BarChart sx={{ mr: 1, color: 'info.main' }} />
                <Typography variant="body2">
                  Engagement score: {analytics?.engagement_score || 0}/100
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
};

export default AnalyticsDashboard;
