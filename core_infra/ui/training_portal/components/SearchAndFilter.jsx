import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Button,
  Paper,
  Typography,
  Collapse,
  Grid,
  Autocomplete,
  Slider,
  Switch,
  FormControlLabel,
  Divider,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Search,
  FilterList,
  Clear,
  ExpandMore,
  ExpandLess,
  Tune,
  BookmarkBorder,
  Schedule,
  TrendingUp,
  School
} from '@mui/icons-material';
import { useTheme } from '@mui/material/styles';

const SearchAndFilter = ({
  searchQuery,
  onSearchChange,
  filters,
  onFiltersChange,
  categories,
  onSaveSearch,
  savedSearches = []
}) => {
  const theme = useTheme();
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [searchSuggestions, setSearchSuggestions] = useState([]);
  const [durationRange, setDurationRange] = useState([0, 240]); // 0-4 hours
  const [localFilters, setLocalFilters] = useState(filters);

  // Search suggestions based on common terms
  const commonSearchTerms = [
    'notification management',
    'external data providers',
    'API usage',
    'compliance',
    'security',
    'operational procedures',
    'risk assessment',
    'data integration',
    'user management',
    'reporting',
    'monitoring',
    'troubleshooting'
  ];

  useEffect(() => {
    // Update search suggestions based on query
    if (searchQuery.length > 0) {
      const suggestions = commonSearchTerms.filter(term =>
        term.toLowerCase().includes(searchQuery.toLowerCase())
      );
      setSearchSuggestions(suggestions);
    } else {
      setSearchSuggestions([]);
    }
  }, [searchQuery]);

  useEffect(() => {
    setLocalFilters(filters);
  }, [filters]);

  const handleFilterChange = (key, value) => {
    const newFilters = { ...localFilters, [key]: value };
    setLocalFilters(newFilters);
    onFiltersChange(newFilters);
  };

  const handleDurationChange = (event, newValue) => {
    setDurationRange(newValue);
    handleFilterChange('durationRange', newValue);
  };

  const clearAllFilters = () => {
    const clearedFilters = {
      category: 'all',
      difficulty: 'all',
      status: 'all',
      contentType: 'all',
      mandatory: 'all',
      durationRange: [0, 240],
      sortBy: 'title',
      sortOrder: 'asc'
    };
    setLocalFilters(clearedFilters);
    setDurationRange([0, 240]);
    onFiltersChange(clearedFilters);
    onSearchChange('');
  };

  const getActiveFilterCount = () => {
    let count = 0;
    if (localFilters.category !== 'all') count++;
    if (localFilters.difficulty !== 'all') count++;
    if (localFilters.status !== 'all') count++;
    if (localFilters.contentType !== 'all') count++;
    if (localFilters.mandatory !== 'all') count++;
    if (searchQuery.length > 0) count++;
    return count;
  };

  const handleSaveCurrentSearch = () => {
    if (onSaveSearch) {
      const searchConfig = {
        query: searchQuery,
        filters: localFilters,
        name: `Search: ${searchQuery || 'Custom Filter'}`,
        timestamp: new Date().toISOString()
      };
      onSaveSearch(searchConfig);
    }
  };

  return (
    <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
      {/* Main Search Bar */}
      <Box mb={2}>
        <Autocomplete
          freeSolo
          options={searchSuggestions}
          value={searchQuery}
          onInputChange={(event, newValue) => onSearchChange(newValue || '')}
          renderInput={(params) => (
            <TextField
              {...params}
              fullWidth
              placeholder="Search training modules, topics, or keywords..."
              InputProps={{
                ...params.InputProps,
                startAdornment: (
                  <InputAdornment position="start">
                    <Search />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    {searchQuery && (
                      <IconButton
                        size="small"
                        onClick={() => onSearchChange('')}
                      >
                        <Clear />
                      </IconButton>
                    )}
                  </InputAdornment>
                )
              }}
            />
          )}
        />
      </Box>

      {/* Quick Filters */}
      <Box display="flex" alignItems="center" gap={2} mb={2} flexWrap="wrap">
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Category</InputLabel>
          <Select
            value={localFilters.category}
            label="Category"
            onChange={(e) => handleFilterChange('category', e.target.value)}
          >
            <MenuItem value="all">All Categories</MenuItem>
            {categories.map((category) => (
              <MenuItem key={category.id} value={category.id}>
                {category.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Difficulty</InputLabel>
          <Select
            value={localFilters.difficulty}
            label="Difficulty"
            onChange={(e) => handleFilterChange('difficulty', e.target.value)}
          >
            <MenuItem value="all">All Levels</MenuItem>
            <MenuItem value="beginner">Beginner</MenuItem>
            <MenuItem value="intermediate">Intermediate</MenuItem>
            <MenuItem value="advanced">Advanced</MenuItem>
            <MenuItem value="expert">Expert</MenuItem>
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Status</InputLabel>
          <Select
            value={localFilters.status}
            label="Status"
            onChange={(e) => handleFilterChange('status', e.target.value)}
          >
            <MenuItem value="all">All Modules</MenuItem>
            <MenuItem value="enrolled">Enrolled</MenuItem>
            <MenuItem value="in_progress">In Progress</MenuItem>
            <MenuItem value="completed">Completed</MenuItem>
            <MenuItem value="not_enrolled">Not Enrolled</MenuItem>
          </Select>
        </FormControl>

        <Button
          variant="outlined"
          startIcon={<Tune />}
          onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
          endIcon={showAdvancedFilters ? <ExpandLess /> : <ExpandMore />}
        >
          Advanced Filters
          {getActiveFilterCount() > 0 && (
            <Chip
              label={getActiveFilterCount()}
              size="small"
              color="primary"
              sx={{ ml: 1 }}
            />
          )}
        </Button>

        {getActiveFilterCount() > 0 && (
          <Button
            variant="text"
            startIcon={<Clear />}
            onClick={clearAllFilters}
            color="secondary"
          >
            Clear All
          </Button>
        )}
      </Box>

      {/* Advanced Filters */}
      <Collapse in={showAdvancedFilters}>
        <Divider sx={{ mb: 3 }} />
        
        <Grid container spacing={3}>
          {/* Content Type Filter */}
          <Grid item xs={12} md={6}>
            <FormControl fullWidth size="small">
              <InputLabel>Content Type</InputLabel>
              <Select
                value={localFilters.contentType || 'all'}
                label="Content Type"
                onChange={(e) => handleFilterChange('contentType', e.target.value)}
              >
                <MenuItem value="all">All Types</MenuItem>
                <MenuItem value="interactive">Interactive</MenuItem>
                <MenuItem value="video">Video</MenuItem>
                <MenuItem value="document">Document</MenuItem>
                <MenuItem value="hands_on">Hands-on</MenuItem>
                <MenuItem value="mixed">Mixed</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          {/* Mandatory Filter */}
          <Grid item xs={12} md={6}>
            <FormControl fullWidth size="small">
              <InputLabel>Training Type</InputLabel>
              <Select
                value={localFilters.mandatory || 'all'}
                label="Training Type"
                onChange={(e) => handleFilterChange('mandatory', e.target.value)}
              >
                <MenuItem value="all">All Training</MenuItem>
                <MenuItem value="mandatory">Required Only</MenuItem>
                <MenuItem value="optional">Optional Only</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          {/* Duration Range */}
          <Grid item xs={12}>
            <Typography gutterBottom>
              Duration Range: {durationRange[0]} - {durationRange[1]} minutes
            </Typography>
            <Slider
              value={durationRange}
              onChange={handleDurationChange}
              valueLabelDisplay="auto"
              min={0}
              max={240}
              step={15}
              marks={[
                { value: 0, label: '0m' },
                { value: 60, label: '1h' },
                { value: 120, label: '2h' },
                { value: 180, label: '3h' },
                { value: 240, label: '4h+' }
              ]}
            />
          </Grid>

          {/* Sort Options */}
          <Grid item xs={12} md={6}>
            <FormControl fullWidth size="small">
              <InputLabel>Sort By</InputLabel>
              <Select
                value={localFilters.sortBy || 'title'}
                label="Sort By"
                onChange={(e) => handleFilterChange('sortBy', e.target.value)}
              >
                <MenuItem value="title">Title</MenuItem>
                <MenuItem value="difficulty">Difficulty</MenuItem>
                <MenuItem value="duration">Duration</MenuItem>
                <MenuItem value="category">Category</MenuItem>
                <MenuItem value="created_at">Date Created</MenuItem>
                <MenuItem value="popularity">Popularity</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={6}>
            <FormControl fullWidth size="small">
              <InputLabel>Sort Order</InputLabel>
              <Select
                value={localFilters.sortOrder || 'asc'}
                label="Sort Order"
                onChange={(e) => handleFilterChange('sortOrder', e.target.value)}
              >
                <MenuItem value="asc">Ascending</MenuItem>
                <MenuItem value="desc">Descending</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          {/* Additional Options */}
          <Grid item xs={12}>
            <Box display="flex" gap={2} flexWrap="wrap">
              <FormControlLabel
                control={
                  <Switch
                    checked={localFilters.showBookmarkedOnly || false}
                    onChange={(e) => handleFilterChange('showBookmarkedOnly', e.target.checked)}
                  />
                }
                label="Bookmarked Only"
              />
              
              <FormControlLabel
                control={
                  <Switch
                    checked={localFilters.showNewModules || false}
                    onChange={(e) => handleFilterChange('showNewModules', e.target.checked)}
                  />
                }
                label="New Modules"
              />
              
              <FormControlLabel
                control={
                  <Switch
                    checked={localFilters.showRecommended || false}
                    onChange={(e) => handleFilterChange('showRecommended', e.target.checked)}
                  />
                }
                label="Recommended"
              />
            </Box>
          </Grid>
        </Grid>

        {/* Save Search */}
        <Box mt={3} display="flex" justifyContent="space-between" alignItems="center">
          <Box>
            {savedSearches.length > 0 && (
              <Box>
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  Saved Searches:
                </Typography>
                <Box display="flex" gap={1} flexWrap="wrap">
                  {savedSearches.slice(0, 3).map((search, index) => (
                    <Chip
                      key={index}
                      label={search.name}
                      size="small"
                      onClick={() => {
                        onSearchChange(search.query);
                        onFiltersChange(search.filters);
                      }}
                      icon={<BookmarkBorder />}
                    />
                  ))}
                </Box>
              </Box>
            )}
          </Box>
          
          <Button
            variant="outlined"
            startIcon={<BookmarkBorder />}
            onClick={handleSaveCurrentSearch}
            disabled={!searchQuery && getActiveFilterCount() === 0}
          >
            Save Search
          </Button>
        </Box>
      </Collapse>

      {/* Active Filters Display */}
      {getActiveFilterCount() > 0 && (
        <Box mt={2}>
          <Typography variant="body2" color="textSecondary" gutterBottom>
            Active Filters:
          </Typography>
          <Box display="flex" gap={1} flexWrap="wrap">
            {searchQuery && (
              <Chip
                label={`Search: "${searchQuery}"`}
                onDelete={() => onSearchChange('')}
                size="small"
                color="primary"
              />
            )}
            {localFilters.category !== 'all' && (
              <Chip
                label={`Category: ${categories.find(c => c.id === localFilters.category)?.label}`}
                onDelete={() => handleFilterChange('category', 'all')}
                size="small"
                color="primary"
              />
            )}
            {localFilters.difficulty !== 'all' && (
              <Chip
                label={`Difficulty: ${localFilters.difficulty}`}
                onDelete={() => handleFilterChange('difficulty', 'all')}
                size="small"
                color="primary"
              />
            )}
            {localFilters.status !== 'all' && (
              <Chip
                label={`Status: ${localFilters.status.replace('_', ' ')}`}
                onDelete={() => handleFilterChange('status', 'all')}
                size="small"
                color="primary"
              />
            )}
          </Box>
        </Box>
      )}
    </Paper>
  );
};

export default SearchAndFilter;
