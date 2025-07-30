import React, { createContext, useContext, useState, useEffect } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { createRegulensTheme } from '../theme';

const ThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeContextProvider');
  }
  return context;
};

export const ThemeContextProvider = ({ children }) => {
  // Initialize theme mode from localStorage or system preference
  const getInitialThemeMode = () => {
    const savedMode = localStorage.getItem('regulens-theme-mode');
    if (savedMode) {
      return savedMode;
    }
    
    // Check system preference
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    
    return 'light';
  };

  const [themeMode, setThemeMode] = useState(getInitialThemeMode);
  const [theme, setTheme] = useState(() => createRegulensTheme(themeMode));

  // Update theme when mode changes
  useEffect(() => {
    const newTheme = createRegulensTheme(themeMode);
    setTheme(newTheme);
    localStorage.setItem('regulens-theme-mode', themeMode);
  }, [themeMode]);

  // Listen for system theme changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    const handleChange = (e) => {
      // Only update if user hasn't manually set a preference
      const savedMode = localStorage.getItem('regulens-theme-mode');
      if (!savedMode) {
        setThemeMode(e.matches ? 'dark' : 'light');
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  const toggleTheme = () => {
    setThemeMode(prevMode => prevMode === 'light' ? 'dark' : 'light');
  };

  const setLightTheme = () => {
    setThemeMode('light');
  };

  const setDarkTheme = () => {
    setThemeMode('dark');
  };

  const value = {
    themeMode,
    theme,
    toggleTheme,
    setLightTheme,
    setDarkTheme,
    isDarkMode: themeMode === 'dark',
  };

  return (
    <ThemeContext.Provider value={value}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ThemeContext.Provider>
  );
};
