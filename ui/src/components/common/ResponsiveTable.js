import React, { useState, useMemo } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TableSortLabel,
  Paper,
  Box,
  TextField,
  InputAdornment,
  IconButton,
  Chip,
  Typography,
  Card,
  CardContent,
  Collapse,
  useTheme,
  Stack,
  Button,
} from '@mui/material';
import {
  Search,
  FilterList,
  ExpandMore,
  ExpandLess,
  ViewColumn,
  GetApp,
} from '@mui/icons-material';
import { useResponsiveTable } from '../../hooks/useResponsive';

/**
 * Enhanced responsive table with mobile-first design
 */
export const ResponsiveTable = ({
  data = [],
  columns = [],
  priorityColumns = [],
  title,
  searchable = true,
  sortable = true,
  filterable = false,
  exportable = false,
  pagination = true,
  pageSize = 10,
  onRowClick,
  onExport,
  sx = {},
  ...props
}) => {
  const theme = useTheme();
  const { getVisibleColumns, shouldUseHorizontalScroll, isMobile } = useResponsiveTable(priorityColumns);
  
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(pageSize);
  const [orderBy, setOrderBy] = useState('');
  const [order, setOrder] = useState('asc');
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedRows, setExpandedRows] = useState(new Set());

  // Get visible columns based on screen size
  const visibleColumns = useMemo(() => getVisibleColumns(columns), [columns, getVisibleColumns]);
  const hiddenColumns = useMemo(() => 
    columns.filter(col => !visibleColumns.includes(col)), 
    [columns, visibleColumns]
  );

  // Filter and sort data
  const processedData = useMemo(() => {
    let filtered = data;

    // Search filter
    if (searchTerm) {
      filtered = filtered.filter(row =>
        Object.values(row).some(value =>
          String(value).toLowerCase().includes(searchTerm.toLowerCase())
        )
      );
    }

    // Sort
    if (orderBy) {
      filtered = [...filtered].sort((a, b) => {
        const aValue = a[orderBy];
        const bValue = b[orderBy];
        
        if (aValue < bValue) return order === 'asc' ? -1 : 1;
        if (aValue > bValue) return order === 'asc' ? 1 : -1;
        return 0;
      });
    }

    return filtered;
  }, [data, searchTerm, orderBy, order]);

  // Paginated data
  const paginatedData = useMemo(() => {
    if (!pagination) return processedData;
    
    const startIndex = page * rowsPerPage;
    return processedData.slice(startIndex, startIndex + rowsPerPage);
  }, [processedData, page, rowsPerPage, pagination]);

  const handleSort = (columnId) => {
    if (!sortable) return;
    
    const isAsc = orderBy === columnId && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(columnId);
  };

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleRowExpand = (rowId) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(rowId)) {
      newExpanded.delete(rowId);
    } else {
      newExpanded.add(rowId);
    }
    setExpandedRows(newExpanded);
  };

  const renderCellValue = (value, column) => {
    if (column.render) {
      return column.render(value);
    }
    
    if (column.type === 'chip') {
      return (
        <Chip 
          label={value} 
          size="small" 
          color={column.chipColor?.(value) || 'default'}
        />
      );
    }
    
    if (column.type === 'date') {
      return new Date(value).toLocaleDateString();
    }
    
    return value;
  };

  // Mobile card view
  const MobileCardView = () => (
    <Stack spacing={2}>
      {paginatedData.map((row, index) => (
        <Card 
          key={row.id || index}
          sx={{ 
            cursor: onRowClick ? 'pointer' : 'default',
            '&:hover': onRowClick ? { 
              boxShadow: theme.shadows[4],
              transform: 'translateY(-1px)',
            } : {},
            transition: 'all 0.2s ease-in-out',
          }}
          onClick={() => onRowClick?.(row)}
        >
          <CardContent>
            {/* Primary columns */}
            {visibleColumns.map((column) => (
              <Box key={column.id} sx={{ mb: 1 }}>
                <Typography variant="caption" color="text.secondary" display="block">
                  {column.label}
                </Typography>
                <Typography variant="body2" fontWeight="medium">
                  {renderCellValue(row[column.id], column)}
                </Typography>
              </Box>
            ))}
            
            {/* Expandable hidden columns */}
            {hiddenColumns.length > 0 && (
              <>
                <Button
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRowExpand(row.id || index);
                  }}
                  startIcon={expandedRows.has(row.id || index) ? <ExpandLess /> : <ExpandMore />}
                  sx={{ mt: 1 }}
                >
                  {expandedRows.has(row.id || index) ? 'Show Less' : 'Show More'}
                </Button>
                
                <Collapse in={expandedRows.has(row.id || index)}>
                  <Box sx={{ mt: 2, pt: 2, borderTop: `1px solid ${theme.palette.divider}` }}>
                    {hiddenColumns.map((column) => (
                      <Box key={column.id} sx={{ mb: 1 }}>
                        <Typography variant="caption" color="text.secondary" display="block">
                          {column.label}
                        </Typography>
                        <Typography variant="body2">
                          {renderCellValue(row[column.id], column)}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                </Collapse>
              </>
            )}
          </CardContent>
        </Card>
      ))}
    </Stack>
  );

  // Desktop table view
  const DesktopTableView = () => (
    <TableContainer 
      component={Paper} 
      sx={{ 
        overflowX: shouldUseHorizontalScroll ? 'auto' : 'visible',
        '&::-webkit-scrollbar': {
          height: 8,
        },
        '&::-webkit-scrollbar-track': {
          backgroundColor: theme.palette.grey[100],
        },
        '&::-webkit-scrollbar-thumb': {
          backgroundColor: theme.palette.grey[400],
          borderRadius: 4,
        },
      }}
    >
      <Table stickyHeader>
        <TableHead>
          <TableRow>
            {visibleColumns.map((column) => (
              <TableCell
                key={column.id}
                sortDirection={orderBy === column.id ? order : false}
                sx={{ 
                  fontWeight: 'bold',
                  backgroundColor: theme.palette.background.paper,
                  minWidth: column.minWidth || 'auto',
                }}
              >
                {sortable && column.sortable !== false ? (
                  <TableSortLabel
                    active={orderBy === column.id}
                    direction={orderBy === column.id ? order : 'asc'}
                    onClick={() => handleSort(column.id)}
                  >
                    {column.label}
                  </TableSortLabel>
                ) : (
                  column.label
                )}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {paginatedData.map((row, index) => (
            <TableRow
              key={row.id || index}
              hover={!!onRowClick}
              onClick={() => onRowClick?.(row)}
              sx={{ 
                cursor: onRowClick ? 'pointer' : 'default',
                '&:hover': {
                  backgroundColor: theme.palette.action.hover,
                },
              }}
            >
              {visibleColumns.map((column) => (
                <TableCell key={column.id}>
                  {renderCellValue(row[column.id], column)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  return (
    <Box sx={{ width: '100%', ...sx }} {...props}>
      {/* Header */}
      {(title || searchable || exportable) && (
        <Box sx={{ 
          display: 'flex', 
          flexDirection: { xs: 'column', sm: 'row' },
          alignItems: { xs: 'stretch', sm: 'center' },
          justifyContent: 'space-between',
          gap: 2,
          mb: 3,
        }}>
          {title && (
            <Typography variant="h6" component="h2">
              {title}
            </Typography>
          )}
          
          <Box sx={{ 
            display: 'flex', 
            flexDirection: { xs: 'column', sm: 'row' },
            gap: 1,
            alignItems: 'stretch',
          }}>
            {searchable && (
              <TextField
                size="small"
                placeholder="Search..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search />
                    </InputAdornment>
                  ),
                }}
                sx={{ minWidth: { xs: 'auto', sm: 250 } }}
              />
            )}
            
            {filterable && (
              <IconButton>
                <FilterList />
              </IconButton>
            )}
            
            {exportable && (
              <Button
                startIcon={<GetApp />}
                onClick={onExport}
                variant="outlined"
                size="small"
              >
                Export
              </Button>
            )}
          </Box>
        </Box>
      )}

      {/* Data display */}
      {processedData.length === 0 ? (
        <Box sx={{ 
          textAlign: 'center', 
          py: 8,
          color: 'text.secondary',
        }}>
          <Typography variant="h6" gutterBottom>
            No data available
          </Typography>
          <Typography variant="body2">
            {searchTerm ? 'No results match your search criteria.' : 'No data to display.'}
          </Typography>
        </Box>
      ) : (
        <>
          {isMobile ? <MobileCardView /> : <DesktopTableView />}
          
          {/* Pagination */}
          {pagination && (
            <TablePagination
              rowsPerPageOptions={[5, 10, 25, 50]}
              component="div"
              count={processedData.length}
              rowsPerPage={rowsPerPage}
              page={page}
              onPageChange={handleChangePage}
              onRowsPerPageChange={handleChangeRowsPerPage}
              sx={{ 
                borderTop: `1px solid ${theme.palette.divider}`,
                mt: 2,
              }}
            />
          )}
        </>
      )}
    </Box>
  );
};
