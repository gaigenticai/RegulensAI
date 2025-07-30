# RegulensAI Responsive Design Guide

## 🎯 Overview

The RegulensAI web application implements a comprehensive responsive design system that ensures optimal user experience across all devices and screen sizes. This guide covers the design principles, implementation patterns, and best practices for maintaining consistency and accessibility.

## 📱 Responsive Breakpoints

### Breakpoint System

```javascript
const breakpoints = {
  xs: 0,      // Mobile portrait (320px+)
  sm: 600,    // Mobile landscape (600px+)
  md: 900,    // Tablet (900px+)
  lg: 1200,   // Desktop (1200px+)
  xl: 1536,   // Large desktop (1536px+)
};
```

### Device Categories

- **Mobile**: 320px - 768px (xs, sm)
- **Tablet**: 768px - 1024px (md)
- **Desktop**: 1024px+ (lg, xl)

## 🎨 Design Principles

### Mobile-First Approach

All components are designed mobile-first, then enhanced for larger screens:

```jsx
// Mobile-first styling
sx={{
  fontSize: '0.875rem',        // Mobile default
  sm: { fontSize: '1rem' },    // Tablet enhancement
  lg: { fontSize: '1.125rem' } // Desktop enhancement
}}
```

### Progressive Enhancement

- **Core functionality** works on all devices
- **Enhanced features** added for larger screens
- **Touch-friendly** interactions on mobile
- **Keyboard navigation** support for accessibility

### Consistent Visual Hierarchy

- **Typography scales** responsively
- **Spacing system** adapts to screen size
- **Color contrast** meets WCAG 2.1 AA standards
- **Interactive elements** maintain minimum touch targets (44px)

## 🧩 Component Architecture

### Responsive Containers

```jsx
import { ResponsiveContainer, ResponsiveGrid } from '../components/common/ResponsiveContainer';

// Automatic responsive padding and max-width
<ResponsiveContainer maxWidth="xl">
  <ResponsiveGrid spacing={{ xs: 2, sm: 3, md: 4 }}>
    {/* Content automatically adapts */}
  </ResponsiveGrid>
</ResponsiveContainer>
```

### Responsive Hooks

```jsx
import { useResponsive } from '../hooks/useResponsive';

const { isMobile, isTablet, isDesktop, getCurrentBreakpoint } = useResponsive();

// Conditional rendering based on screen size
{isMobile ? <MobileComponent /> : <DesktopComponent />}
```

### Adaptive Navigation

```jsx
// Navigation automatically adapts
<ResponsiveNavigation 
  currentPath="/operations"
  user={user}
  onNavigate={handleNavigation}
  notifications={5}
/>
```

## 📊 Component Patterns

### Cards and Layouts

```jsx
// Responsive card grid
<ResponsiveCardGrid 
  minCardWidth={{ xs: 280, sm: 320, md: 360 }}
  spacing={{ xs: 2, sm: 3, md: 4 }}
>
  {items.map(item => (
    <Card key={item.id}>
      <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
        {/* Card content */}
      </CardContent>
    </Card>
  ))}
</ResponsiveCardGrid>
```

### Tables and Data Display

```jsx
// Responsive table with mobile card view
<ResponsiveTable
  data={tableData}
  columns={columns}
  priorityColumns={['name', 'status']} // Shown on mobile
  searchable
  pagination
  onRowClick={handleRowClick}
/>
```

### Forms and Inputs

```jsx
// Responsive form layout
<ResponsiveFlex 
  direction={{ xs: 'column', md: 'row' }}
  spacing={2}
>
  <TextField 
    fullWidth
    size={isMobile ? "medium" : "small"}
    label="Search"
  />
  <Button 
    variant="contained"
    size={isMobile ? "medium" : "small"}
    fullWidth={isMobile}
  >
    Submit
  </Button>
</ResponsiveFlex>
```

## 🎭 Theme System

### Dark/Light Mode Support

```jsx
import { useTheme } from '../contexts/ThemeContext';

const { isDarkMode, toggleTheme, themeMode } = useTheme();

// Automatic theme switching
<IconButton onClick={toggleTheme}>
  {isDarkMode ? <Brightness7 /> : <Brightness4 />}
</IconButton>
```

### Typography Scale

```javascript
const typography = {
  h1: { fontSize: '2.5rem', lineHeight: 1.2 },
  h2: { fontSize: '2rem', lineHeight: 1.3 },
  h3: { fontSize: '1.75rem', lineHeight: 1.4 },
  h4: { fontSize: '1.5rem', lineHeight: 1.4 },
  h5: { fontSize: '1.25rem', lineHeight: 1.5 },
  h6: { fontSize: '1.125rem', lineHeight: 1.5 },
  body1: { fontSize: '1rem', lineHeight: 1.6 },
  body2: { fontSize: '0.875rem', lineHeight: 1.5 },
};
```

### Spacing System

```javascript
// Consistent spacing scale
const spacing = (factor) => `${0.25 * factor}rem`;

// Usage in components
sx={{
  p: { xs: 2, sm: 3, md: 4 },  // 0.5rem, 0.75rem, 1rem
  m: { xs: 1, sm: 2, md: 3 },  // 0.25rem, 0.5rem, 0.75rem
}}
```

## 🔧 Implementation Guidelines

### Component Development

1. **Start with mobile design**
2. **Use responsive hooks** for conditional logic
3. **Implement progressive enhancement**
4. **Test across all breakpoints**
5. **Ensure touch-friendly interactions**

### Performance Optimization

```jsx
// Lazy loading for heavy components
const HeavyComponent = React.lazy(() => import('./HeavyComponent'));

// Conditional loading based on screen size
{!isMobile && (
  <Suspense fallback={<LoadingSpinner />}>
    <HeavyComponent />
  </Suspense>
)}
```

### Loading States

```jsx
// Responsive loading components
<FadeInContent 
  loading={loading}
  skeleton={<CardSkeleton height={{ xs: 200, sm: 240 }} />}
>
  <ActualContent />
</FadeInContent>
```

## ♿ Accessibility Features

### ARIA Support

```jsx
// Proper ARIA labels and roles
<Button
  aria-label="Open navigation menu"
  aria-expanded={drawerOpen}
  aria-controls="navigation-drawer"
>
  <MenuIcon />
</Button>
```

### Keyboard Navigation

```jsx
// Focus management
const handleKeyDown = (event) => {
  if (event.key === 'Enter' || event.key === ' ') {
    handleClick();
  }
};

<div
  role="button"
  tabIndex={0}
  onKeyDown={handleKeyDown}
  onClick={handleClick}
>
  Interactive Element
</div>
```

### Screen Reader Support

```jsx
// Descriptive text for screen readers
<Typography variant="srOnly">
  Loading configuration validation results
</Typography>

// Live regions for dynamic content
<div aria-live="polite" aria-atomic="true">
  {statusMessage}
</div>
```

## 📱 Mobile-Specific Features

### Touch Interactions

```jsx
// Touch-friendly button sizes
<Button
  sx={{
    minHeight: 44,  // Minimum touch target
    minWidth: 44,
    p: { xs: 2, sm: 1 },
  }}
>
  Touch Me
</Button>
```

### Swipe Gestures

```jsx
// Swipe support for mobile
const handleSwipe = useSwipeable({
  onSwipedLeft: () => nextTab(),
  onSwipedRight: () => prevTab(),
  preventDefaultTouchmoveEvent: true,
  trackMouse: true
});

<div {...handleSwipe}>
  <SwipeableContent />
</div>
```

### Mobile Navigation

```jsx
// Collapsible mobile navigation
<Drawer
  variant="temporary"
  open={mobileOpen}
  onClose={handleDrawerClose}
  ModalProps={{ keepMounted: true }} // Better mobile performance
  sx={{
    display: { xs: 'block', lg: 'none' },
    '& .MuiDrawer-paper': {
      width: 280,
      boxSizing: 'border-box',
    },
  }}
>
  <NavigationContent />
</Drawer>
```

## 🧪 Testing Guidelines

### Responsive Testing

```javascript
// Test different viewport sizes
const viewports = [
  { width: 320, height: 568 },   // iPhone SE
  { width: 375, height: 667 },   // iPhone 6/7/8
  { width: 768, height: 1024 },  // iPad
  { width: 1200, height: 800 },  // Desktop
];

viewports.forEach(viewport => {
  test(`renders correctly at ${viewport.width}x${viewport.height}`, () => {
    // Test implementation
  });
});
```

### Accessibility Testing

```javascript
// Test keyboard navigation
test('supports keyboard navigation', () => {
  const { getByRole } = render(<Component />);
  const button = getByRole('button');
  
  button.focus();
  fireEvent.keyDown(button, { key: 'Enter' });
  
  expect(mockHandler).toHaveBeenCalled();
});
```

### Performance Testing

```javascript
// Test loading performance
test('loads within performance budget', async () => {
  const startTime = performance.now();
  render(<Component />);
  await waitFor(() => expect(screen.getByText('Content')).toBeInTheDocument());
  const loadTime = performance.now() - startTime;
  
  expect(loadTime).toBeLessThan(1000); // 1 second budget
});
```

## 🚀 Best Practices

### Do's

✅ **Use responsive hooks** for conditional logic  
✅ **Test on real devices** when possible  
✅ **Implement progressive enhancement**  
✅ **Maintain consistent spacing**  
✅ **Ensure touch targets are ≥44px**  
✅ **Use semantic HTML elements**  
✅ **Provide alternative text for images**  
✅ **Test with screen readers**  

### Don'ts

❌ **Don't rely solely on CSS media queries**  
❌ **Don't ignore touch interactions**  
❌ **Don't use fixed pixel values**  
❌ **Don't forget keyboard navigation**  
❌ **Don't assume mouse interactions**  
❌ **Don't ignore loading states**  
❌ **Don't skip accessibility testing**  
❌ **Don't use color alone to convey information**  

## 📞 Support and Resources

### Development Tools

- **Chrome DevTools**: Device emulation and responsive testing
- **React Developer Tools**: Component inspection and debugging
- **axe DevTools**: Accessibility testing and validation
- **Lighthouse**: Performance and accessibility auditing

### Testing Resources

- **Google Mobile-Friendly Test**: https://search.google.com/test/mobile-friendly
- **WebAIM WAVE**: https://wave.webaim.org/
- **Colour Contrast Analyser**: https://www.tpgi.com/color-contrast-checker/

### Documentation

- **Material-UI Responsive**: https://mui.com/system/display/
- **WCAG Guidelines**: https://www.w3.org/WAI/WCAG21/quickref/
- **MDN Responsive Design**: https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Responsive_Design

---

**Last Updated**: January 29, 2024  
**Version**: 1.0.0  
**Maintainer**: Frontend Team <frontend@regulens.ai>
