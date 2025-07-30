import React from 'react';
import { Box, Container, useTheme } from '@mui/material';
import { useResponsive } from '../../hooks/useResponsive';

/**
 * Responsive container component with consistent padding and max-width
 */
export const ResponsiveContainer = ({ 
  children, 
  maxWidth = 'xl',
  disableGutters = false,
  sx = {},
  ...props 
}) => {
  const theme = useTheme();
  const { isMobile, isTablet } = useResponsive();

  const responsivePadding = {
    xs: theme.spacing(2),
    sm: theme.spacing(3),
    md: theme.spacing(4),
    lg: theme.spacing(4),
    xl: theme.spacing(4),
  };

  return (
    <Container
      maxWidth={maxWidth}
      disableGutters={disableGutters}
      sx={{
        px: disableGutters ? 0 : responsivePadding,
        py: {
          xs: theme.spacing(2),
          sm: theme.spacing(3),
          md: theme.spacing(4),
        },
        ...sx,
      }}
      {...props}
    >
      {children}
    </Container>
  );
};

/**
 * Responsive grid container with automatic spacing
 */
export const ResponsiveGrid = ({ 
  children, 
  spacing = { xs: 2, sm: 3, md: 4 },
  sx = {},
  ...props 
}) => {
  const theme = useTheme();
  const { getCurrentBreakpoint } = useResponsive();
  
  const currentSpacing = typeof spacing === 'object' 
    ? spacing[getCurrentBreakpoint()] || spacing.md || 3
    : spacing;

  return (
    <Box
      sx={{
        display: 'grid',
        gap: theme.spacing(currentSpacing),
        gridTemplateColumns: {
          xs: '1fr',
          sm: 'repeat(auto-fit, minmax(280px, 1fr))',
          md: 'repeat(auto-fit, minmax(320px, 1fr))',
          lg: 'repeat(auto-fit, minmax(360px, 1fr))',
        },
        ...sx,
      }}
      {...props}
    >
      {children}
    </Box>
  );
};

/**
 * Responsive flex container with direction switching
 */
export const ResponsiveFlex = ({ 
  children,
  direction = { xs: 'column', md: 'row' },
  spacing = 2,
  align = 'stretch',
  justify = 'flex-start',
  wrap = 'wrap',
  sx = {},
  ...props 
}) => {
  const theme = useTheme();
  const { getCurrentBreakpoint } = useResponsive();
  
  const currentDirection = typeof direction === 'object'
    ? direction[getCurrentBreakpoint()] || direction.md || 'row'
    : direction;

  const currentSpacing = typeof spacing === 'object'
    ? spacing[getCurrentBreakpoint()] || spacing.md || 2
    : spacing;

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: currentDirection,
        alignItems: align,
        justifyContent: justify,
        flexWrap: wrap,
        gap: theme.spacing(currentSpacing),
        ...sx,
      }}
      {...props}
    >
      {children}
    </Box>
  );
};

/**
 * Responsive card grid with automatic sizing
 */
export const ResponsiveCardGrid = ({ 
  children,
  minCardWidth = { xs: 280, sm: 320, md: 360 },
  spacing = { xs: 2, sm: 3, md: 4 },
  sx = {},
  ...props 
}) => {
  const theme = useTheme();
  const { getCurrentBreakpoint } = useResponsive();
  
  const currentMinWidth = typeof minCardWidth === 'object'
    ? minCardWidth[getCurrentBreakpoint()] || minCardWidth.md || 320
    : minCardWidth;

  const currentSpacing = typeof spacing === 'object'
    ? spacing[getCurrentBreakpoint()] || spacing.md || 3
    : spacing;

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: `repeat(auto-fill, minmax(${currentMinWidth}px, 1fr))`,
        gap: theme.spacing(currentSpacing),
        ...sx,
      }}
      {...props}
    >
      {children}
    </Box>
  );
};

/**
 * Responsive section with consistent spacing
 */
export const ResponsiveSection = ({ 
  children,
  title,
  subtitle,
  spacing = { xs: 3, sm: 4, md: 6 },
  sx = {},
  ...props 
}) => {
  const theme = useTheme();
  const { getCurrentBreakpoint } = useResponsive();
  
  const currentSpacing = typeof spacing === 'object'
    ? spacing[getCurrentBreakpoint()] || spacing.md || 4
    : spacing;

  return (
    <Box
      component="section"
      sx={{
        py: theme.spacing(currentSpacing),
        ...sx,
      }}
      {...props}
    >
      {title && (
        <Box sx={{ mb: theme.spacing(2) }}>
          {title}
          {subtitle && (
            <Box sx={{ mt: theme.spacing(1) }}>
              {subtitle}
            </Box>
          )}
        </Box>
      )}
      {children}
    </Box>
  );
};

/**
 * Responsive stack with automatic direction switching
 */
export const ResponsiveStack = ({ 
  children,
  direction = { xs: 'column', md: 'row' },
  spacing = 2,
  divider,
  sx = {},
  ...props 
}) => {
  const theme = useTheme();
  const { getCurrentBreakpoint } = useResponsive();
  
  const currentDirection = typeof direction === 'object'
    ? direction[getCurrentBreakpoint()] || direction.md || 'row'
    : direction;

  const currentSpacing = typeof spacing === 'object'
    ? spacing[getCurrentBreakpoint()] || spacing.md || 2
    : spacing;

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: currentDirection,
        gap: theme.spacing(currentSpacing),
        ...sx,
      }}
      {...props}
    >
      {React.Children.map(children, (child, index) => (
        <React.Fragment key={index}>
          {index > 0 && divider && (
            <Box sx={{ 
              alignSelf: currentDirection === 'row' ? 'stretch' : 'center',
              width: currentDirection === 'row' ? '1px' : '100%',
              height: currentDirection === 'row' ? 'auto' : '1px',
            }}>
              {divider}
            </Box>
          )}
          {child}
        </React.Fragment>
      ))}
    </Box>
  );
};

/**
 * Responsive visibility wrapper
 */
export const ResponsiveShow = ({ 
  children,
  breakpoint,
  direction = 'up', // 'up', 'down', 'only'
  ...props 
}) => {
  const theme = useTheme();
  
  let display = {};
  
  if (direction === 'up') {
    display = {
      display: { xs: 'none', [breakpoint]: 'block' }
    };
  } else if (direction === 'down') {
    display = {
      display: { [breakpoint]: 'none' }
    };
  } else if (direction === 'only') {
    const breakpoints = ['xs', 'sm', 'md', 'lg', 'xl'];
    const currentIndex = breakpoints.indexOf(breakpoint);
    
    display = {
      display: breakpoints.reduce((acc, bp, index) => {
        acc[bp] = index === currentIndex ? 'block' : 'none';
        return acc;
      }, {})
    };
  }

  return (
    <Box sx={display} {...props}>
      {children}
    </Box>
  );
};

/**
 * Responsive hide wrapper
 */
export const ResponsiveHide = ({ 
  children,
  breakpoint,
  direction = 'down', // 'up', 'down', 'only'
  ...props 
}) => {
  return (
    <ResponsiveShow 
      breakpoint={breakpoint} 
      direction={direction === 'up' ? 'down' : direction === 'down' ? 'up' : 'only'}
      {...props}
    >
      {children}
    </ResponsiveShow>
  );
};
