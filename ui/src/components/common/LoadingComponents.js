import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Skeleton,
  CircularProgress,
  LinearProgress,
  Typography,
  useTheme,
  Fade,
  Backdrop,
} from '@mui/material';
import { useResponsive } from '../../hooks/useResponsive';

/**
 * Enhanced loading spinner with responsive sizing
 */
export const LoadingSpinner = ({ 
  size = { xs: 32, sm: 40, md: 48 },
  message,
  overlay = false,
  sx = {},
  ...props 
}) => {
  const theme = useTheme();
  const { getCurrentBreakpoint } = useResponsive();
  
  const currentSize = typeof size === 'object'
    ? size[getCurrentBreakpoint()] || size.md || 40
    : size;

  const content = (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: theme.spacing(2),
        p: theme.spacing(3),
        ...sx,
      }}
      {...props}
    >
      <CircularProgress size={currentSize} />
      {message && (
        <Typography variant="body2" color="text.secondary" textAlign="center">
          {message}
        </Typography>
      )}
    </Box>
  );

  if (overlay) {
    return (
      <Backdrop
        open={true}
        sx={{
          color: '#fff',
          zIndex: theme.zIndex.drawer + 1,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
        }}
      >
        {content}
      </Backdrop>
    );
  }

  return content;
};

/**
 * Progress bar with responsive styling
 */
export const ProgressBar = ({ 
  value,
  message,
  showPercentage = true,
  variant = 'determinate',
  sx = {},
  ...props 
}) => {
  const theme = useTheme();

  return (
    <Box sx={{ width: '100%', ...sx }} {...props}>
      {message && (
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="body2" color="text.secondary">
            {message}
          </Typography>
          {showPercentage && variant === 'determinate' && (
            <Typography variant="body2" color="text.secondary">
              {Math.round(value)}%
            </Typography>
          )}
        </Box>
      )}
      <LinearProgress
        variant={variant}
        value={value}
        sx={{
          height: 8,
          borderRadius: 4,
          backgroundColor: theme.palette.grey[200],
          '& .MuiLinearProgress-bar': {
            borderRadius: 4,
          },
        }}
      />
    </Box>
  );
};

/**
 * Card skeleton with responsive layout
 */
export const CardSkeleton = ({ 
  lines = 3,
  showAvatar = false,
  showActions = false,
  height = { xs: 200, sm: 220, md: 240 },
  sx = {},
  ...props 
}) => {
  const theme = useTheme();
  const { getCurrentBreakpoint } = useResponsive();
  
  const currentHeight = typeof height === 'object'
    ? height[getCurrentBreakpoint()] || height.md || 220
    : height;

  return (
    <Card sx={{ height: currentHeight, ...sx }} {...props}>
      <CardContent>
        {showAvatar && (
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Skeleton variant="circular" width={40} height={40} />
            <Box sx={{ ml: 2, flex: 1 }}>
              <Skeleton variant="text" width="60%" />
              <Skeleton variant="text" width="40%" />
            </Box>
          </Box>
        )}
        
        <Skeleton variant="text" width="80%" height={32} sx={{ mb: 1 }} />
        
        {Array.from({ length: lines }).map((_, index) => (
          <Skeleton
            key={index}
            variant="text"
            width={index === lines - 1 ? '60%' : '100%'}
            sx={{ mb: 0.5 }}
          />
        ))}
        
        {showActions && (
          <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
            <Skeleton variant="rectangular" width={80} height={32} />
            <Skeleton variant="rectangular" width={80} height={32} />
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

/**
 * Table skeleton with responsive columns
 */
export const TableSkeleton = ({ 
  rows = 5,
  columns = { xs: 2, sm: 3, md: 5 },
  sx = {},
  ...props 
}) => {
  const theme = useTheme();
  const { getCurrentBreakpoint } = useResponsive();
  
  const currentColumns = typeof columns === 'object'
    ? columns[getCurrentBreakpoint()] || columns.md || 4
    : columns;

  return (
    <Box sx={{ width: '100%', ...sx }} {...props}>
      {/* Header */}
      <Box sx={{ 
        display: 'flex', 
        gap: theme.spacing(2), 
        mb: theme.spacing(2),
        pb: theme.spacing(1),
        borderBottom: `1px solid ${theme.palette.divider}`,
      }}>
        {Array.from({ length: currentColumns }).map((_, index) => (
          <Skeleton
            key={`header-${index}`}
            variant="text"
            width={index === 0 ? '30%' : '20%'}
            height={24}
          />
        ))}
      </Box>
      
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <Box
          key={`row-${rowIndex}`}
          sx={{ 
            display: 'flex', 
            gap: theme.spacing(2), 
            mb: theme.spacing(1.5),
            alignItems: 'center',
          }}
        >
          {Array.from({ length: currentColumns }).map((_, colIndex) => (
            <Skeleton
              key={`cell-${rowIndex}-${colIndex}`}
              variant="text"
              width={colIndex === 0 ? '30%' : '20%'}
              height={20}
            />
          ))}
        </Box>
      ))}
    </Box>
  );
};

/**
 * Dashboard skeleton with responsive grid
 */
export const DashboardSkeleton = ({ 
  cards = { xs: 2, sm: 4, md: 6 },
  sx = {},
  ...props 
}) => {
  const theme = useTheme();
  const { getCurrentBreakpoint } = useResponsive();
  
  const currentCards = typeof cards === 'object'
    ? cards[getCurrentBreakpoint()] || cards.md || 4
    : cards;

  return (
    <Box sx={{ ...sx }} {...props}>
      {/* Header skeleton */}
      <Box sx={{ mb: theme.spacing(4) }}>
        <Skeleton variant="text" width="40%" height={40} sx={{ mb: 1 }} />
        <Skeleton variant="text" width="60%" height={24} />
      </Box>
      
      {/* Stats cards skeleton */}
      <Box sx={{ 
        display: 'grid',
        gridTemplateColumns: {
          xs: 'repeat(2, 1fr)',
          sm: 'repeat(2, 1fr)',
          md: 'repeat(4, 1fr)',
        },
        gap: theme.spacing(3),
        mb: theme.spacing(4),
      }}>
        {Array.from({ length: 4 }).map((_, index) => (
          <CardSkeleton
            key={`stat-${index}`}
            lines={1}
            height={{ xs: 120, sm: 140, md: 160 }}
          />
        ))}
      </Box>
      
      {/* Main content cards */}
      <Box sx={{ 
        display: 'grid',
        gridTemplateColumns: {
          xs: '1fr',
          sm: 'repeat(2, 1fr)',
          md: 'repeat(3, 1fr)',
        },
        gap: theme.spacing(3),
      }}>
        {Array.from({ length: currentCards }).map((_, index) => (
          <CardSkeleton
            key={`card-${index}`}
            lines={4}
            showActions={true}
          />
        ))}
      </Box>
    </Box>
  );
};

/**
 * List skeleton with responsive items
 */
export const ListSkeleton = ({ 
  items = 5,
  showAvatar = true,
  showSecondary = true,
  sx = {},
  ...props 
}) => {
  const theme = useTheme();

  return (
    <Box sx={{ ...sx }} {...props}>
      {Array.from({ length: items }).map((_, index) => (
        <Box
          key={index}
          sx={{
            display: 'flex',
            alignItems: 'center',
            py: theme.spacing(2),
            borderBottom: index < items - 1 ? `1px solid ${theme.palette.divider}` : 'none',
          }}
        >
          {showAvatar && (
            <Skeleton
              variant="circular"
              width={40}
              height={40}
              sx={{ mr: theme.spacing(2) }}
            />
          )}
          <Box sx={{ flex: 1 }}>
            <Skeleton variant="text" width="70%" height={24} />
            {showSecondary && (
              <Skeleton variant="text" width="50%" height={20} sx={{ mt: 0.5 }} />
            )}
          </Box>
          <Skeleton variant="rectangular" width={60} height={32} />
        </Box>
      ))}
    </Box>
  );
};

/**
 * Fade-in wrapper for smooth loading transitions
 */
export const FadeInContent = ({ 
  children, 
  loading = false, 
  skeleton,
  timeout = 300,
  ...props 
}) => {
  return (
    <Fade in={!loading} timeout={timeout} {...props}>
      <Box>
        {loading ? skeleton : children}
      </Box>
    </Fade>
  );
};

/**
 * Suspense-like loading boundary
 */
export const LoadingBoundary = ({ 
  children, 
  loading = false, 
  fallback,
  error,
  retry,
  ...props 
}) => {
  const theme = useTheme();

  if (error) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          p: theme.spacing(4),
          textAlign: 'center',
        }}
        {...props}
      >
        <Typography variant="h6" color="error" gutterBottom>
          Something went wrong
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {error.message || 'An unexpected error occurred'}
        </Typography>
        {retry && (
          <button onClick={retry}>
            Try Again
          </button>
        )}
      </Box>
    );
  }

  if (loading) {
    return fallback || <LoadingSpinner message="Loading..." />;
  }

  return children;
};
