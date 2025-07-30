import React, { useState } from 'react';
import {
  AppBar,
  Toolbar,
  IconButton,
  Typography,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemButton,
  Box,
  useTheme,
  Avatar,
  Menu,
  MenuItem,
  Divider,
  Switch,
  FormControlLabel,
  Collapse,
  Badge,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Close as CloseIcon,
  Dashboard,
  Security,
  School,
  People,
  Settings,
  Logout,
  Brightness4,
  Brightness7,
  ExpandLess,
  ExpandMore,
  Notifications,
  AccountCircle,
} from '@mui/icons-material';
import { useResponsiveDrawer } from '../../hooks/useResponsive';
import { useTheme as useCustomTheme } from '../../contexts/ThemeContext';

const navigationItems = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: <Dashboard />,
    path: '/dashboard',
  },
  {
    id: 'compliance',
    label: 'Compliance',
    icon: <Security />,
    path: '/compliance',
    children: [
      { id: 'overview', label: 'Overview', path: '/compliance/overview' },
      { id: 'tasks', label: 'Tasks', path: '/compliance/tasks' },
      { id: 'reports', label: 'Reports', path: '/compliance/reports' },
    ],
  },
  {
    id: 'training',
    label: 'Training Portal',
    icon: <School />,
    path: '/training',
    children: [
      { id: 'modules', label: 'Modules', path: '/training/modules' },
      { id: 'assessments', label: 'Assessments', path: '/training/assessments' },
      { id: 'certificates', label: 'Certificates', path: '/training/certificates' },
    ],
  },
  {
    id: 'users',
    label: 'User Management',
    icon: <People />,
    path: '/users',
  },
  {
    id: 'operations',
    label: 'Operations',
    icon: <Settings />,
    path: '/operations',
  },
];

export const ResponsiveNavigation = ({ 
  currentPath = '/',
  user,
  onNavigate,
  notifications = 0,
  ...props 
}) => {
  const theme = useTheme();
  const { isDarkMode, toggleTheme } = useCustomTheme();
  const { isPersistent, mobileOpen, handleDrawerToggle, handleDrawerClose } = useResponsiveDrawer();
  
  const [userMenuAnchor, setUserMenuAnchor] = useState(null);
  const [expandedItems, setExpandedItems] = useState({});

  const handleUserMenuOpen = (event) => {
    setUserMenuAnchor(event.currentTarget);
  };

  const handleUserMenuClose = () => {
    setUserMenuAnchor(null);
  };

  const handleItemExpand = (itemId) => {
    setExpandedItems(prev => ({
      ...prev,
      [itemId]: !prev[itemId],
    }));
  };

  const handleNavigation = (path) => {
    if (onNavigate) {
      onNavigate(path);
    }
    if (!isPersistent) {
      handleDrawerClose();
    }
  };

  const isActive = (path) => {
    return currentPath === path || currentPath.startsWith(path + '/');
  };

  const drawerWidth = theme.custom?.sidebar?.width || 280;

  const DrawerContent = () => (
    <Box sx={{ width: drawerWidth, height: '100%' }}>
      {/* Mobile header */}
      {!isPersistent && (
        <Box sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          p: 2,
          borderBottom: `1px solid ${theme.palette.divider}`,
        }}>
          <Typography variant="h6" color="primary" fontWeight="bold">
            RegulensAI
          </Typography>
          <IconButton onClick={handleDrawerClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      )}

      {/* Navigation items */}
      <List sx={{ pt: isPersistent ? 2 : 1 }}>
        {navigationItems.map((item) => (
          <React.Fragment key={item.id}>
            <ListItem disablePadding>
              <ListItemButton
                onClick={() => {
                  if (item.children) {
                    handleItemExpand(item.id);
                  } else {
                    handleNavigation(item.path);
                  }
                }}
                selected={isActive(item.path)}
                sx={{
                  mx: 1,
                  borderRadius: 1,
                  '&.Mui-selected': {
                    backgroundColor: theme.palette.primary.main + '20',
                    '&:hover': {
                      backgroundColor: theme.palette.primary.main + '30',
                    },
                  },
                }}
              >
                <ListItemIcon
                  sx={{
                    color: isActive(item.path) ? theme.palette.primary.main : 'inherit',
                    minWidth: 40,
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                <ListItemText 
                  primary={item.label}
                  primaryTypographyProps={{
                    fontWeight: isActive(item.path) ? 600 : 400,
                    color: isActive(item.path) ? theme.palette.primary.main : 'inherit',
                  }}
                />
                {item.children && (
                  expandedItems[item.id] ? <ExpandLess /> : <ExpandMore />
                )}
              </ListItemButton>
            </ListItem>

            {/* Submenu items */}
            {item.children && (
              <Collapse in={expandedItems[item.id]} timeout="auto" unmountOnExit>
                <List component="div" disablePadding>
                  {item.children.map((child) => (
                    <ListItem key={child.id} disablePadding>
                      <ListItemButton
                        onClick={() => handleNavigation(child.path)}
                        selected={isActive(child.path)}
                        sx={{
                          pl: 4,
                          mx: 1,
                          borderRadius: 1,
                          '&.Mui-selected': {
                            backgroundColor: theme.palette.primary.main + '15',
                          },
                        }}
                      >
                        <ListItemText 
                          primary={child.label}
                          primaryTypographyProps={{
                            fontSize: '0.875rem',
                            fontWeight: isActive(child.path) ? 600 : 400,
                            color: isActive(child.path) ? theme.palette.primary.main : 'inherit',
                          }}
                        />
                      </ListItemButton>
                    </ListItem>
                  ))}
                </List>
              </Collapse>
            )}
          </React.Fragment>
        ))}
      </List>

      {/* Theme toggle */}
      <Box sx={{ mt: 'auto', p: 2 }}>
        <FormControlLabel
          control={
            <Switch
              checked={isDarkMode}
              onChange={toggleTheme}
              icon={<Brightness7 />}
              checkedIcon={<Brightness4 />}
            />
          }
          label={
            <Typography variant="body2">
              {isDarkMode ? 'Dark' : 'Light'} Mode
            </Typography>
          }
        />
      </Box>
    </Box>
  );

  return (
    <>
      {/* App Bar */}
      <AppBar
        position="fixed"
        sx={{
          width: { lg: isPersistent ? `calc(100% - ${drawerWidth}px)` : '100%' },
          ml: { lg: isPersistent ? `${drawerWidth}px` : 0 },
          zIndex: theme.zIndex.drawer + 1,
        }}
        {...props}
      >
        <Toolbar>
          {/* Mobile menu button */}
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ 
              mr: 2, 
              display: { lg: isPersistent ? 'none' : 'block' } 
            }}
          >
            <MenuIcon />
          </IconButton>

          {/* Logo/Title */}
          <Typography 
            variant="h6" 
            noWrap 
            component="div" 
            sx={{ 
              flexGrow: 1,
              fontWeight: 'bold',
              display: { xs: 'none', sm: 'block' }
            }}
          >
            RegulensAI
          </Typography>

          {/* Mobile logo */}
          <Typography 
            variant="h6" 
            noWrap 
            component="div" 
            sx={{ 
              flexGrow: 1,
              fontWeight: 'bold',
              display: { xs: 'block', sm: 'none' }
            }}
          >
            RegulensAI
          </Typography>

          {/* Right side actions */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {/* Notifications */}
            <IconButton color="inherit">
              <Badge badgeContent={notifications} color="error">
                <Notifications />
              </Badge>
            </IconButton>

            {/* User menu */}
            <IconButton
              color="inherit"
              onClick={handleUserMenuOpen}
              sx={{ p: 0.5 }}
            >
              {user?.avatar ? (
                <Avatar 
                  src={user.avatar} 
                  alt={user.name}
                  sx={{ width: 32, height: 32 }}
                />
              ) : (
                <AccountCircle sx={{ fontSize: 32 }} />
              )}
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Navigation Drawer */}
      <Box
        component="nav"
        sx={{ width: { lg: isPersistent ? drawerWidth : 0 }, flexShrink: { lg: 0 } }}
      >
        {/* Mobile drawer */}
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerClose}
          ModalProps={{
            keepMounted: true, // Better open performance on mobile
          }}
          sx={{
            display: { xs: 'block', lg: isPersistent ? 'none' : 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
              borderRight: `1px solid ${theme.palette.divider}`,
            },
          }}
        >
          <DrawerContent />
        </Drawer>

        {/* Desktop drawer */}
        {isPersistent && (
          <Drawer
            variant="permanent"
            sx={{
              display: { xs: 'none', lg: 'block' },
              '& .MuiDrawer-paper': {
                boxSizing: 'border-box',
                width: drawerWidth,
                borderRight: `1px solid ${theme.palette.divider}`,
                top: theme.custom?.header?.height || 64,
                height: `calc(100% - ${theme.custom?.header?.height || 64}px)`,
              },
            }}
            open
          >
            <DrawerContent />
          </Drawer>
        )}
      </Box>

      {/* User Menu */}
      <Menu
        anchorEl={userMenuAnchor}
        open={Boolean(userMenuAnchor)}
        onClose={handleUserMenuClose}
        onClick={handleUserMenuClose}
        PaperProps={{
          elevation: 3,
          sx: {
            mt: 1.5,
            minWidth: 200,
            '& .MuiMenuItem-root': {
              px: 2,
              py: 1,
            },
          },
        }}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        {user && (
          <>
            <Box sx={{ px: 2, py: 1.5 }}>
              <Typography variant="subtitle2" fontWeight="bold">
                {user.name}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {user.email}
              </Typography>
            </Box>
            <Divider />
          </>
        )}
        
        <MenuItem onClick={() => handleNavigation('/profile')}>
          <ListItemIcon>
            <AccountCircle fontSize="small" />
          </ListItemIcon>
          Profile
        </MenuItem>
        
        <MenuItem onClick={() => handleNavigation('/settings')}>
          <ListItemIcon>
            <Settings fontSize="small" />
          </ListItemIcon>
          Settings
        </MenuItem>
        
        <Divider />
        
        <MenuItem onClick={() => console.log('Logout')}>
          <ListItemIcon>
            <Logout fontSize="small" />
          </ListItemIcon>
          Logout
        </MenuItem>
      </Menu>
    </>
  );
};
