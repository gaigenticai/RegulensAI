import React, { useState, useEffect, useContext } from 'react';
import {
  Box,
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  LinearProgress,
  Avatar,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Breadcrumbs,
  Link,
  TextField,
  InputAdornment,
  Badge,
  Tooltip,
  Fab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
  Paper,
  Divider
} from '@mui/material';
import {
  School,
  PlayArrow,
  CheckCircle,
  Schedule,
  BookmarkBorder,
  Bookmark,
  Search,
  FilterList,
  MenuBook,
  Quiz,
  Certificate,
  Forum,
  Analytics,
  Download,
  Print,
  Share,
  Star,
  TrendingUp,
  Group,
  Assignment,
  VideoLibrary,
  Code,
  Security,
  Notifications,
  DataUsage,
  Settings,
  Help,
  NavigateNext,
  Home
} from '@mui/icons-material';
import { useTheme } from '@mui/material/styles';
import { AuthContext } from '../contexts/AuthContext';
import { TrainingAPI } from '../services/TrainingAPI';
import TrainingModuleCard from './components/TrainingModuleCard';
import TrainingProgress from './components/TrainingProgress';
import SearchAndFilter from './components/SearchAndFilter';
import BookmarkManager from './components/BookmarkManager';
import CertificateViewer from './components/CertificateViewer';
import DiscussionForum from './components/DiscussionForum';
import AnalyticsDashboard from './components/AnalyticsDashboard';

const TrainingPortal = () => {
  const theme = useTheme();
  const { user } = useContext(AuthContext);
  
  // State management
  const [currentView, setCurrentView] = useState('dashboard');
  const [modules, setModules] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [bookmarks, setBookmarks] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState({
    category: 'all',
    difficulty: 'all',
    status: 'all'
  });
  const [loading, setLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedModule, setSelectedModule] = useState(null);
  const [showCertificateDialog, setShowCertificateDialog] = useState(false);
  const [selectedCertificate, setSelectedCertificate] = useState(null);

  // Load initial data
  useEffect(() => {
    loadTrainingData();
  }, []);

  const loadTrainingData = async () => {
    try {
      setLoading(true);
      const [modulesData, enrollmentsData, certificatesData, bookmarksData] = await Promise.all([
        TrainingAPI.getModules(),
        TrainingAPI.getUserEnrollments(user.id),
        TrainingAPI.getUserCertificates(user.id),
        TrainingAPI.getUserBookmarks(user.id)
      ]);
      
      setModules(modulesData);
      setEnrollments(enrollmentsData);
      setCertificates(certificatesData);
      setBookmarks(bookmarksData);
    } catch (error) {
      console.error('Failed to load training data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Navigation items
  const navigationItems = [
    { id: 'dashboard', label: 'Dashboard', icon: <Home />, badge: null },
    { id: 'modules', label: 'Training Modules', icon: <MenuBook />, badge: modules.length },
    { id: 'assessments', label: 'Assessments', icon: <Quiz />, badge: null },
    { id: 'certificates', label: 'Certificates', icon: <Certificate />, badge: certificates.length },
    { id: 'bookmarks', label: 'Bookmarks', icon: <Bookmark />, badge: bookmarks.length },
    { id: 'discussions', label: 'Discussions', icon: <Forum />, badge: null },
    { id: 'analytics', label: 'My Progress', icon: <Analytics />, badge: null }
  ];

  // Training categories
  const trainingCategories = [
    { id: 'notification_management', label: 'Notification Management', icon: <Notifications />, color: '#1976d2' },
    { id: 'external_data', label: 'External Data Providers', icon: <DataUsage />, color: '#388e3c' },
    { id: 'operational_procedures', label: 'Operational Procedures', icon: <Settings />, color: '#f57c00' },
    { id: 'api_usage', label: 'API Usage', icon: <Code />, color: '#7b1fa2' },
    { id: 'compliance', label: 'Compliance', icon: <Security />, color: '#d32f2f' },
    { id: 'general', label: 'General Training', icon: <School />, color: '#455a64' }
  ];

  // Filter modules based on search and filters
  const filteredModules = modules.filter(module => {
    const matchesSearch = module.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         module.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = filters.category === 'all' || module.category === filters.category;
    const matchesDifficulty = filters.difficulty === 'all' || module.difficulty_level === filters.difficulty;
    
    let matchesStatus = true;
    if (filters.status !== 'all') {
      const enrollment = enrollments.find(e => e.module_id === module.id);
      if (filters.status === 'enrolled' && !enrollment) matchesStatus = false;
      if (filters.status === 'completed' && (!enrollment || enrollment.status !== 'completed')) matchesStatus = false;
      if (filters.status === 'in_progress' && (!enrollment || enrollment.status !== 'in_progress')) matchesStatus = false;
    }
    
    return matchesSearch && matchesCategory && matchesDifficulty && matchesStatus;
  });

  // Calculate overall progress
  const overallProgress = enrollments.length > 0 
    ? enrollments.reduce((sum, e) => sum + (e.completion_percentage || 0), 0) / enrollments.length
    : 0;

  const completedModules = enrollments.filter(e => e.status === 'completed').length;
  const inProgressModules = enrollments.filter(e => e.status === 'in_progress').length;

  // Handle module enrollment
  const handleEnrollModule = async (moduleId) => {
    try {
      await TrainingAPI.enrollInModule(moduleId);
      await loadTrainingData(); // Refresh data
    } catch (error) {
      console.error('Failed to enroll in module:', error);
    }
  };

  // Handle bookmark toggle
  const handleBookmarkToggle = async (moduleId, sectionId = null) => {
    try {
      const existingBookmark = bookmarks.find(b => 
        b.module_id === moduleId && b.section_id === sectionId
      );
      
      if (existingBookmark) {
        await TrainingAPI.removeBookmark(existingBookmark.id);
      } else {
        await TrainingAPI.createBookmark({
          module_id: moduleId,
          section_id: sectionId,
          title: modules.find(m => m.id === moduleId)?.title || 'Bookmark'
        });
      }
      
      await loadTrainingData(); // Refresh bookmarks
    } catch (error) {
      console.error('Failed to toggle bookmark:', error);
    }
  };

  // Render dashboard view
  const renderDashboard = () => (
    <Grid container spacing={3}>
      {/* Progress Overview */}
      <Grid item xs={12}>
        <Card>
          <CardContent>
            <Typography variant="h5" gutterBottom>
              Welcome back, {user.full_name}!
            </Typography>
            <Typography variant="body1" color="textSecondary" paragraph>
              Continue your RegulensAI training journey. You're making great progress!
            </Typography>
            
            <Grid container spacing={3} sx={{ mt: 2 }}>
              <Grid item xs={12} md={4}>
                <Box textAlign="center">
                  <Typography variant="h3" color="primary">
                    {Math.round(overallProgress)}%
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Overall Progress
                  </Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={overallProgress} 
                    sx={{ mt: 1, height: 8, borderRadius: 4 }}
                  />
                </Box>
              </Grid>
              
              <Grid item xs={12} md={4}>
                <Box textAlign="center">
                  <Typography variant="h3" color="success.main">
                    {completedModules}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Completed Modules
                  </Typography>
                </Box>
              </Grid>
              
              <Grid item xs={12} md={4}>
                <Box textAlign="center">
                  <Typography variant="h3" color="warning.main">
                    {inProgressModules}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    In Progress
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </Grid>

      {/* Quick Actions */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Quick Actions
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<MenuBook />}
                  onClick={() => setCurrentView('modules')}
                >
                  Browse Modules
                </Button>
              </Grid>
              <Grid item xs={6}>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<Quiz />}
                  onClick={() => setCurrentView('assessments')}
                >
                  Take Assessment
                </Button>
              </Grid>
              <Grid item xs={6}>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<Certificate />}
                  onClick={() => setCurrentView('certificates')}
                >
                  View Certificates
                </Button>
              </Grid>
              <Grid item xs={6}>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<Forum />}
                  onClick={() => setCurrentView('discussions')}
                >
                  Join Discussion
                </Button>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </Grid>

      {/* Recent Activity */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Recent Activity
            </Typography>
            {enrollments.slice(0, 3).map((enrollment) => {
              const module = modules.find(m => m.id === enrollment.module_id);
              return (
                <Box key={enrollment.id} sx={{ mb: 2 }}>
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2">
                      {module?.title}
                    </Typography>
                    <Chip 
                      size="small" 
                      label={enrollment.status}
                      color={enrollment.status === 'completed' ? 'success' : 'primary'}
                    />
                  </Box>
                  <LinearProgress 
                    variant="determinate" 
                    value={enrollment.completion_percentage || 0}
                    sx={{ mt: 1, height: 4, borderRadius: 2 }}
                  />
                </Box>
              );
            })}
          </CardContent>
        </Card>
      </Grid>

      {/* Training Categories */}
      <Grid item xs={12}>
        <Typography variant="h6" gutterBottom>
          Training Categories
        </Typography>
        <Grid container spacing={2}>
          {trainingCategories.map((category) => (
            <Grid item xs={12} sm={6} md={4} key={category.id}>
              <Card 
                sx={{ 
                  cursor: 'pointer',
                  '&:hover': { transform: 'translateY(-2px)', transition: 'transform 0.2s' }
                }}
                onClick={() => {
                  setFilters({ ...filters, category: category.id });
                  setCurrentView('modules');
                }}
              >
                <CardContent>
                  <Box display="flex" alignItems="center" mb={1}>
                    <Avatar sx={{ bgcolor: category.color, mr: 2 }}>
                      {category.icon}
                    </Avatar>
                    <Typography variant="h6">
                      {category.label}
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="textSecondary">
                    {modules.filter(m => m.category === category.id).length} modules available
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Grid>
    </Grid>
  );

  // Render modules view
  const renderModules = () => (
    <Box>
      <SearchAndFilter
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        filters={filters}
        onFiltersChange={setFilters}
        categories={trainingCategories}
      />
      
      <Grid container spacing={3} sx={{ mt: 2 }}>
        {filteredModules.map((module) => {
          const enrollment = enrollments.find(e => e.module_id === module.id);
          const isBookmarked = bookmarks.some(b => b.module_id === module.id);
          
          return (
            <Grid item xs={12} md={6} lg={4} key={module.id}>
              <TrainingModuleCard
                module={module}
                enrollment={enrollment}
                isBookmarked={isBookmarked}
                onEnroll={() => handleEnrollModule(module.id)}
                onBookmark={() => handleBookmarkToggle(module.id)}
                onStart={() => setSelectedModule(module)}
              />
            </Grid>
          );
        })}
      </Grid>
    </Box>
  );

  // Render current view
  const renderCurrentView = () => {
    switch (currentView) {
      case 'dashboard':
        return renderDashboard();
      case 'modules':
        return renderModules();
      case 'assessments':
        return <Typography>Assessments view coming soon...</Typography>;
      case 'certificates':
        return <CertificateViewer certificates={certificates} />;
      case 'bookmarks':
        return <BookmarkManager bookmarks={bookmarks} onRemove={loadTrainingData} />;
      case 'discussions':
        return <DiscussionForum />;
      case 'analytics':
        return <AnalyticsDashboard enrollments={enrollments} />;
      default:
        return renderDashboard();
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>Loading training portal...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* Navigation Drawer */}
      <Drawer
        variant="permanent"
        sx={{
          width: 280,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: 280,
            boxSizing: 'border-box',
            position: 'relative'
          },
        }}
      >
        <Box sx={{ p: 2 }}>
          <Typography variant="h5" color="primary" gutterBottom>
            Training Portal
          </Typography>
          <Divider />
        </Box>
        
        <List>
          {navigationItems.map((item) => (
            <ListItem
              button
              key={item.id}
              selected={currentView === item.id}
              onClick={() => setCurrentView(item.id)}
            >
              <ListItemIcon>
                {item.badge ? (
                  <Badge badgeContent={item.badge} color="primary">
                    {item.icon}
                  </Badge>
                ) : (
                  item.icon
                )}
              </ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItem>
          ))}
        </List>
      </Drawer>

      {/* Main Content */}
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        {/* Breadcrumbs */}
        <Breadcrumbs sx={{ mb: 3 }}>
          <Link color="inherit" href="#" onClick={() => setCurrentView('dashboard')}>
            Training Portal
          </Link>
          <Typography color="textPrimary">
            {navigationItems.find(item => item.id === currentView)?.label || 'Dashboard'}
          </Typography>
        </Breadcrumbs>

        {/* Content */}
        {renderCurrentView()}
      </Box>

      {/* Floating Action Button for Help */}
      <Fab
        color="primary"
        sx={{ position: 'fixed', bottom: 16, right: 16 }}
        onClick={() => setCurrentView('help')}
      >
        <Help />
      </Fab>
    </Box>
  );
};

export default TrainingPortal;
