import { useTheme } from '@mui/material/styles';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useState, useEffect } from 'react';

/**
 * Hook for responsive breakpoint detection
 */
export const useResponsive = () => {
  const theme = useTheme();
  
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const isTablet = useMediaQuery(theme.breakpoints.between('sm', 'lg'));
  const isDesktop = useMediaQuery(theme.breakpoints.up('lg'));
  const isXs = useMediaQuery(theme.breakpoints.only('xs'));
  const isSm = useMediaQuery(theme.breakpoints.only('sm'));
  const isMd = useMediaQuery(theme.breakpoints.only('md'));
  const isLg = useMediaQuery(theme.breakpoints.only('lg'));
  const isXl = useMediaQuery(theme.breakpoints.only('xl'));

  // Touch device detection
  const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

  // Screen orientation
  const [orientation, setOrientation] = useState(
    window.innerHeight > window.innerWidth ? 'portrait' : 'landscape'
  );

  useEffect(() => {
    const handleOrientationChange = () => {
      setOrientation(window.innerHeight > window.innerWidth ? 'portrait' : 'landscape');
    };

    window.addEventListener('resize', handleOrientationChange);
    return () => window.removeEventListener('resize', handleOrientationChange);
  }, []);

  // Get current breakpoint name
  const getCurrentBreakpoint = () => {
    if (isXs) return 'xs';
    if (isSm) return 'sm';
    if (isMd) return 'md';
    if (isLg) return 'lg';
    if (isXl) return 'xl';
    return 'xl';
  };

  // Responsive value selector
  const getResponsiveValue = (values) => {
    const breakpoint = getCurrentBreakpoint();
    
    if (typeof values === 'object' && values !== null) {
      return values[breakpoint] || values.default || values.md || Object.values(values)[0];
    }
    
    return values;
  };

  return {
    // Breakpoint booleans
    isMobile,
    isTablet,
    isDesktop,
    isXs,
    isSm,
    isMd,
    isLg,
    isXl,
    
    // Device info
    isTouchDevice,
    orientation,
    
    // Utilities
    getCurrentBreakpoint,
    getResponsiveValue,
    
    // Breakpoint values for direct use
    breakpoints: theme.breakpoints.values,
  };
};

/**
 * Hook for responsive grid columns
 */
export const useResponsiveGrid = (columns = { xs: 1, sm: 2, md: 3, lg: 4, xl: 6 }) => {
  const { getCurrentBreakpoint } = useResponsive();
  const breakpoint = getCurrentBreakpoint();
  
  return columns[breakpoint] || columns.md || 3;
};

/**
 * Hook for responsive spacing
 */
export const useResponsiveSpacing = (spacing = { xs: 1, sm: 2, md: 3, lg: 4 }) => {
  const { getCurrentBreakpoint } = useResponsive();
  const breakpoint = getCurrentBreakpoint();
  
  return spacing[breakpoint] || spacing.md || 3;
};

/**
 * Hook for responsive font sizes
 */
export const useResponsiveFontSize = (sizes = { xs: '0.875rem', sm: '1rem', md: '1.125rem', lg: '1.25rem' }) => {
  const { getCurrentBreakpoint } = useResponsive();
  const breakpoint = getCurrentBreakpoint();
  
  return sizes[breakpoint] || sizes.md || '1rem';
};

/**
 * Hook for responsive component visibility
 */
export const useResponsiveVisibility = () => {
  const responsive = useResponsive();
  
  const showOnMobile = responsive.isMobile;
  const showOnTablet = responsive.isTablet;
  const showOnDesktop = responsive.isDesktop;
  const hideOnMobile = !responsive.isMobile;
  const hideOnTablet = !responsive.isTablet;
  const hideOnDesktop = !responsive.isDesktop;
  
  return {
    showOnMobile,
    showOnTablet,
    showOnDesktop,
    hideOnMobile,
    hideOnTablet,
    hideOnDesktop,
  };
};

/**
 * Hook for responsive drawer behavior
 */
export const useResponsiveDrawer = (persistentBreakpoint = 'lg') => {
  const theme = useTheme();
  const isPersistent = useMediaQuery(theme.breakpoints.up(persistentBreakpoint));
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleDrawerClose = () => {
    setMobileOpen(false);
  };

  // Auto-close mobile drawer when switching to desktop
  useEffect(() => {
    if (isPersistent && mobileOpen) {
      setMobileOpen(false);
    }
  }, [isPersistent, mobileOpen]);

  return {
    isPersistent,
    mobileOpen,
    handleDrawerToggle,
    handleDrawerClose,
  };
};

/**
 * Hook for responsive table behavior
 */
export const useResponsiveTable = (priorityColumns = []) => {
  const { isMobile, isTablet } = useResponsive();
  
  const getVisibleColumns = (allColumns) => {
    if (isMobile) {
      // On mobile, show only priority columns (first 2-3 most important)
      return allColumns.filter((col, index) => 
        priorityColumns.includes(col.id) || index < 2
      );
    }
    
    if (isTablet) {
      // On tablet, show more columns but still limit
      return allColumns.filter((col, index) => 
        priorityColumns.includes(col.id) || index < 4
      );
    }
    
    // Desktop shows all columns
    return allColumns;
  };

  const shouldUseHorizontalScroll = isMobile || isTablet;
  
  return {
    getVisibleColumns,
    shouldUseHorizontalScroll,
    isMobile,
    isTablet,
  };
};

/**
 * Hook for responsive dialog behavior
 */
export const useResponsiveDialog = () => {
  const { isMobile } = useResponsive();
  
  return {
    fullScreen: isMobile,
    maxWidth: isMobile ? false : 'md',
    fullWidth: true,
  };
};

/**
 * Hook for responsive card layout
 */
export const useResponsiveCardLayout = () => {
  const { getCurrentBreakpoint } = useResponsive();
  const breakpoint = getCurrentBreakpoint();
  
  const cardSpacing = {
    xs: 1,
    sm: 2,
    md: 3,
    lg: 3,
    xl: 4,
  }[breakpoint];
  
  const cardsPerRow = {
    xs: 1,
    sm: 2,
    md: 2,
    lg: 3,
    xl: 4,
  }[breakpoint];
  
  const cardMinHeight = {
    xs: 200,
    sm: 220,
    md: 240,
    lg: 260,
    xl: 280,
  }[breakpoint];
  
  return {
    cardSpacing,
    cardsPerRow,
    cardMinHeight,
  };
};
