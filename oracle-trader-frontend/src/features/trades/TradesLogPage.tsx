// src/pages/TradesLogPage.tsx
import React, { useEffect, useState, useCallback } from 'react';
import { getTradesHistory, TradeData, getTotalTradesCount } from '@services/apiService'; // getTotalTradesCount added

import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import TableContainer from '@mui/material/TableContainer';
import Table from '@mui/material/Table';
import TableHead from '@mui/material/TableHead';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import TablePagination from '@mui/material/TablePagination';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip'; 

const TradesLogPage: React.FC = () => {
  const [trades, setTrades] = useState<TradeData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  const [page, setPage] = useState(0); 
  const [rowsPerPage, setRowsPerPage] = useState(10); 
  const [totalTrades, setTotalTrades] = useState(0); // Will be fetched from API

  const fetchTradesAndCount = useCallback(async (currentPage: number, currentRowsPerPage: number) => {
    setLoading(true);
    setError(null);
    try {
      // Fetch total count first (or in parallel)
      const totalCount = await getTotalTradesCount();
      setTotalTrades(totalCount);

      // Then fetch the trades for the current page
      const tradesData = await getTradesHistory(currentPage * currentRowsPerPage, currentRowsPerPage);
      setTrades(tradesData || []);
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "An unknown error occurred";
      setError(`Failed to load trades history. Error: ${errorMessage}`);
      console.error("TradesLogPage fetch error:", err);
    } finally {
      setLoading(false);
    }
  }, []); 

  useEffect(() => {
    fetchTradesAndCount(page, rowsPerPage);
  }, [fetchTradesAndCount, page, rowsPerPage]); 

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0); 
  };

  if (loading && trades.length === 0 && page === 0) { 
    return (
      <Container sx={{ display: 'flex', justifyContent: 'center', mt: 5 }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 2, mb: 4 }}>
      <Typography variant="h5" component="h1" gutterBottom color="primary" sx={{ mb: 2 }}>
        Trades History Log
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Paper sx={{ width: '100%', overflow: 'hidden' }}>
        <TableContainer sx={{ maxHeight: 700 }}> 
          <Table stickyHeader size="small" aria-label="trades history table">
            <TableHead>
              <TableRow>
                <TableCell sx={{fontWeight: 'bold'}}>ID</TableCell>
                <TableCell sx={{fontWeight: 'bold'}}>Symbol</TableCell>
                <TableCell sx={{fontWeight: 'bold'}} align="center">Direction</TableCell>
                <TableCell sx={{fontWeight: 'bold'}} align="center">Status</TableCell>
                <TableCell sx={{fontWeight: 'bold'}} align="right">Entry Price</TableCell>
                <TableCell sx={{fontWeight: 'bold'}} align="right">Exit Price</TableCell>
                <TableCell sx={{fontWeight: 'bold'}} align="right">Quantity</TableCell>
                <TableCell sx={{fontWeight: 'bold'}} align="right">PNL</TableCell>
                <TableCell sx={{fontWeight: 'bold'}} align="right">PNL %</TableCell>
                <TableCell sx={{fontWeight: 'bold'}}>Strategy</TableCell>
                <TableCell sx={{fontWeight: 'bold'}}>Opened At</TableCell>
                <TableCell sx={{fontWeight: 'bold'}}>Closed At</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading && ( 
                <TableRow>
                    <TableCell colSpan={12} align="center">
                        <CircularProgress size={24} sx={{my: 2}} />
                    </TableCell>
                </TableRow>
              )}
              {!loading && trades.length === 0 && !error && (
                <TableRow>
                    <TableCell colSpan={12} align="center">
                        No trades found in history.
                    </TableCell>
                </TableRow>
              )}
              {!loading && trades.map((trade) => (
                <TableRow hover key={trade.id}>
                  <TableCell>{trade.id}</TableCell>
                  <TableCell component="th" scope="row">
                    {trade.symbol?.replace('/USDT:USDT', '')}
                  </TableCell>
                  <TableCell align="center">
                    <Chip 
                        label={trade.direction} 
                        size="small" 
                        color={trade.direction === 'LONG' ? 'success' : 'error'} 
                        variant="outlined"
                        sx={{minWidth: 60, textTransform: 'capitalize'}}
                    />
                  </TableCell>
                  <TableCell align="center">
                     <Chip 
                        label={trade.status?.replace('CLOSED_', '').replace('_EXCHANGE','').replace('_INFERRED','')} 
                        size="small" 
                        color={trade.status?.includes('OPEN') ? 'info' : (trade.pnl ?? 0) >= 0 ? 'success' : 'error'}
                        variant="filled"
                        sx={{minWidth: 80, textTransform: 'capitalize'}}
                    />
                  </TableCell>
                  <TableCell align="right">{trade.entry_price?.toFixed(4) ?? 'N/A'}</TableCell>
                  <TableCell align="right">{trade.exit_price?.toFixed(4) ?? 'N/A'}</TableCell>
                  <TableCell align="right">{trade.quantity?.toFixed(4) ?? 'N/A'}</TableCell>
                  <TableCell 
                    align="right" 
                    sx={{ color: (trade.pnl ?? 0) >= 0 ? 'success.main' : 'error.main', fontWeight: 'medium' }}
                  >
                    {trade.pnl?.toFixed(2) ?? 'N/A'}
                  </TableCell>
                  <TableCell 
                    align="right"
                    sx={{ color: (trade.pnl_percentage ?? 0) >= 0 ? 'success.main' : 'error.main', fontWeight: 'medium' }}
                  >
                    {trade.pnl_percentage?.toFixed(1) ?? 'N/A'}%
                  </TableCell>
                  <TableCell>{trade.strategy_name ?? 'N/A'}</TableCell>
                  <TableCell>
                    {trade.timestamp_opened ? new Date(trade.timestamp_opened).toLocaleString() : 'N/A'}
                  </TableCell>
                  <TableCell>
                    {trade.timestamp_closed ? new Date(trade.timestamp_closed).toLocaleString() : 'N/A'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          rowsPerPageOptions={[5, 10, 25, 50, 100]}
          component="div"
          count={totalTrades} 
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </Paper>
    </Container>
  );
};

export default TradesLogPage;
