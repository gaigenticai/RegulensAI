import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  LinearProgress,
  Box,
  IconButton,
  Avatar,
  Tooltip,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider
} from '@mui/material';
import {
  PlayArrow,
  Bookmark,
  BookmarkBorder,
  MoreVert,
  Schedule,
  CheckCircle,
  Assignment,
  Quiz,
  VideoLibrary,
  MenuBook,
  Code,
  Security,
  Notifications,
  DataUsage,
  Settings,
  School,
  Star,
  StarBorder,
  Share,
  Download,
  Print,
  Info
} from '@mui/icons-material';
import { useTheme } from '@mui/material/styles';

const TrainingModuleCard = ({
  module,
  enrollment,
  isBookmarked,
  onEnroll,
  onBookmark,
  onStart,
  onRate
}) => {
  const theme = useTheme();
  const [anchorEl, setAnchorEl] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  const [rating, setRating] = useState(0);

  // Get category icon and color
  const getCategoryIcon = (category) => {
    const icons = {
      notification_management: <Notifications />,
      external_data: <DataUsage />,
      operational_procedures: <Settings />,
      api_usage: <Code />,
      compliance: <Security />,
      general: <School />
    };
    return icons[category] || <MenuBook />;
  };

  const getCategoryColor = (category) => {
    const colors = {
      notification_management: '#1976d2',
      external_data: '#388e3c',
      operational_procedures: '#f57c00',
      api_usage: '#7b1fa2',
      compliance: '#d32f2f',
      general: '#455a64'
    };
    return colors[category] || '#455a64';
  };

  // Get difficulty color
  const getDifficultyColor = (difficulty) => {
    const colors = {
      beginner: 'success',
      intermediate: 'warning',
      advanced: 'error',
      expert: 'secondary'
    };
    return colors[difficulty] || 'default';
  };

  // Get content type icon
  const getContentTypeIcon = (contentType) => {
    const icons = {
      video: <VideoLibrary />,
      interactive: <Code />,
      document: <MenuBook />,
      hands_on: <Assignment />,
      mixed: <School />
    };
    return icons[contentType] || <MenuBook />;
  };

  // Calculate progress percentage
  const progressPercentage = enrollment?.completion_percentage || 0;
  const isCompleted = enrollment?.status === 'completed';
  const isInProgress = enrollment?.status === 'in_progress';
  const isEnrolled = !!enrollment;

  // Handle menu actions
  const handleMenuClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: module.title,
        text: module.description,
        url: window.location.href
      });
    } else {
      // Fallback: copy to clipboard
      navigator.clipboard.writeText(window.location.href);
    }
    handleMenuClose();
  };

  const handleDownload = () => {
    // Implement download functionality
    console.log('Download module:', module.id);
    handleMenuClose();
  };

  const handlePrint = () => {
    window.print();
    handleMenuClose();
  };

  const handleRating = (newRating) => {
    setRating(newRating);
    if (onRate) {
      onRate(module.id, newRating);
    }
  };

  return (
    <>
      <Card 
        sx={{ 
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
          '&:hover': {
            transform: 'translateY(-4px)',
            boxShadow: theme.shadows[8],
            transition: 'all 0.3s ease-in-out'
          }
        }}
      >
        {/* Status Badge */}
        {isCompleted && (
          <Chip
            icon={<CheckCircle />}
            label="Completed"
            color="success"
            size="small"
            sx={{
              position: 'absolute',
              top: 8,
              right: 8,
              zIndex: 1
            }}
          />
        )}
        
        {isInProgress && (
          <Chip
            label="In Progress"
            color="primary"
            size="small"
            sx={{
              position: 'absolute',
              top: 8,
              right: 8,
              zIndex: 1
            }}
          />
        )}

        <CardContent sx={{ flexGrow: 1, pb: 1 }}>
          {/* Header */}
          <Box display="flex" alignItems="flex-start" mb={2}>
            <Avatar 
              sx={{ 
                bgcolor: getCategoryColor(module.category),
                mr: 2,
                mt: 0.5
              }}
            >
              {getCategoryIcon(module.category)}
            </Avatar>
            
            <Box flexGrow={1}>
              <Typography variant="h6" component="h3" gutterBottom>
                {module.title}
              </Typography>
              
              <Box display="flex" gap={1} mb={1}>
                <Chip 
                  label={module.difficulty_level}
                  color={getDifficultyColor(module.difficulty_level)}
                  size="small"
                />
                <Chip 
                  icon={getContentTypeIcon(module.content_type)}
                  label={module.content_type}
                  variant="outlined"
                  size="small"
                />
              </Box>
            </Box>

            <IconButton
              size="small"
              onClick={handleMenuClick}
              sx={{ ml: 1 }}
            >
              <MoreVert />
            </IconButton>
          </Box>

          {/* Description */}
          <Typography 
            variant="body2" 
            color="textSecondary" 
            paragraph
            sx={{
              display: '-webkit-box',
              WebkitLineClamp: 3,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden'
            }}
          >
            {module.description}
          </Typography>

          {/* Metadata */}
          <Box display="flex" alignItems="center" gap={2} mb={2}>
            <Box display="flex" alignItems="center">
              <Schedule fontSize="small" sx={{ mr: 0.5, color: 'text.secondary' }} />
              <Typography variant="caption" color="textSecondary">
                {module.estimated_duration_minutes} min
              </Typography>
            </Box>
            
            {module.is_mandatory && (
              <Chip 
                label="Required"
                color="error"
                size="small"
                variant="outlined"
              />
            )}
          </Box>

          {/* Progress Bar */}
          {isEnrolled && (
            <Box mb={2}>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                <Typography variant="caption" color="textSecondary">
                  Progress
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  {Math.round(progressPercentage)}%
                </Typography>
              </Box>
              <LinearProgress 
                variant="determinate" 
                value={progressPercentage}
                sx={{ 
                  height: 6, 
                  borderRadius: 3,
                  backgroundColor: theme.palette.grey[200]
                }}
              />
            </Box>
          )}

          {/* Learning Objectives Preview */}
          {module.learning_objectives && module.learning_objectives.length > 0 && (
            <Box>
              <Typography variant="caption" color="textSecondary" gutterBottom>
                You will learn:
              </Typography>
              <Typography variant="body2" color="textSecondary">
                • {module.learning_objectives.slice(0, 2).join(' • ')}
                {module.learning_objectives.length > 2 && '...'}
              </Typography>
            </Box>
          )}
        </CardContent>

        <CardActions sx={{ p: 2, pt: 0 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" width="100%">
            <Box display="flex" gap={1}>
              {!isEnrolled ? (
                <Button
                  variant="contained"
                  startIcon={<PlayArrow />}
                  onClick={onEnroll}
                  size="small"
                >
                  Enroll
                </Button>
              ) : (
                <Button
                  variant={isCompleted ? "outlined" : "contained"}
                  startIcon={isCompleted ? <CheckCircle /> : <PlayArrow />}
                  onClick={onStart}
                  size="small"
                >
                  {isCompleted ? 'Review' : isInProgress ? 'Continue' : 'Start'}
                </Button>
              )}
              
              <Button
                variant="outlined"
                size="small"
                onClick={() => setShowDetails(true)}
                startIcon={<Info />}
              >
                Details
              </Button>
            </Box>

            <IconButton
              onClick={onBookmark}
              color={isBookmarked ? "primary" : "default"}
              size="small"
            >
              {isBookmarked ? <Bookmark /> : <BookmarkBorder />}
            </IconButton>
          </Box>
        </CardActions>
      </Card>

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleShare}>
          <ListItemIcon>
            <Share fontSize="small" />
          </ListItemIcon>
          <ListItemText>Share</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleDownload}>
          <ListItemIcon>
            <Download fontSize="small" />
          </ListItemIcon>
          <ListItemText>Download</ListItemText>
        </MenuItem>
        <MenuItem onClick={handlePrint}>
          <ListItemIcon>
            <Print fontSize="small" />
          </ListItemIcon>
          <ListItemText>Print</ListItemText>
        </MenuItem>
      </Menu>

      {/* Module Details Dialog */}
      <Dialog
        open={showDetails}
        onClose={() => setShowDetails(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" alignItems="center">
            <Avatar 
              sx={{ 
                bgcolor: getCategoryColor(module.category),
                mr: 2
              }}
            >
              {getCategoryIcon(module.category)}
            </Avatar>
            <Box>
              <Typography variant="h6">{module.title}</Typography>
              <Typography variant="caption" color="textSecondary">
                Version {module.version} • {module.category.replace('_', ' ')}
              </Typography>
            </Box>
          </Box>
        </DialogTitle>
        
        <DialogContent>
          <Box mb={3}>
            <Typography variant="body1" paragraph>
              {module.description}
            </Typography>
            
            <Box display="flex" gap={2} mb={3}>
              <Chip 
                label={`${module.difficulty_level} level`}
                color={getDifficultyColor(module.difficulty_level)}
              />
              <Chip 
                icon={<Schedule />}
                label={`${module.estimated_duration_minutes} minutes`}
                variant="outlined"
              />
              <Chip 
                icon={getContentTypeIcon(module.content_type)}
                label={module.content_type}
                variant="outlined"
              />
            </Box>
          </Box>

          {/* Learning Objectives */}
          {module.learning_objectives && module.learning_objectives.length > 0 && (
            <Box mb={3}>
              <Typography variant="h6" gutterBottom>
                Learning Objectives
              </Typography>
              <List dense>
                {module.learning_objectives.map((objective, index) => (
                  <ListItem key={index}>
                    <ListItemIcon>
                      <CheckCircle color="primary" fontSize="small" />
                    </ListItemIcon>
                    <ListItemText primary={objective} />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}

          {/* Prerequisites */}
          {module.prerequisites && module.prerequisites.length > 0 && (
            <Box mb={3}>
              <Typography variant="h6" gutterBottom>
                Prerequisites
              </Typography>
              <List dense>
                {module.prerequisites.map((prereq, index) => (
                  <ListItem key={index}>
                    <ListItemIcon>
                      <Assignment color="warning" fontSize="small" />
                    </ListItemIcon>
                    <ListItemText primary={prereq} />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}

          {/* Progress and Rating */}
          {isEnrolled && (
            <Box>
              <Divider sx={{ my: 2 }} />
              <Typography variant="h6" gutterBottom>
                Your Progress
              </Typography>
              <Box display="flex" alignItems="center" gap={2} mb={2}>
                <LinearProgress 
                  variant="determinate" 
                  value={progressPercentage}
                  sx={{ flexGrow: 1, height: 8, borderRadius: 4 }}
                />
                <Typography variant="body2">
                  {Math.round(progressPercentage)}%
                </Typography>
              </Box>
              
              {isCompleted && (
                <Box>
                  <Typography variant="body2" gutterBottom>
                    Rate this module:
                  </Typography>
                  <Box display="flex" gap={0.5}>
                    {[1, 2, 3, 4, 5].map((star) => (
                      <IconButton
                        key={star}
                        size="small"
                        onClick={() => handleRating(star)}
                      >
                        {star <= rating ? <Star color="primary" /> : <StarBorder />}
                      </IconButton>
                    ))}
                  </Box>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={() => setShowDetails(false)}>
            Close
          </Button>
          {!isEnrolled ? (
            <Button
              variant="contained"
              onClick={() => {
                onEnroll();
                setShowDetails(false);
              }}
            >
              Enroll Now
            </Button>
          ) : (
            <Button
              variant="contained"
              onClick={() => {
                onStart();
                setShowDetails(false);
              }}
            >
              {isCompleted ? 'Review Module' : isInProgress ? 'Continue Learning' : 'Start Module'}
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </>
  );
};

export default TrainingModuleCard;
