// src/features/dashboard/DashboardPage.tsx
import React, { useEffect, useState, useCallback } from 'react';
import { 
    getAccountOverview, 
    AccountBalanceDetail, 
    getBotSettings, 
    BotSettingsData, 
    getTradesHistory, 
    TradeData,
    getOpenPositions, 
    OpenPositionData,
    closePosition,
    ClosePositionPayload,
    getBotStatus,
    startBot,
    stopBot,
    BotStatusResponse
} from '@services/apiClient';
import {
    Typography, CircularProgress, Alert, Box, Grid, Paper,
    List, ListItem, ListItemText, Divider, TableContainer, Table,
    TableHead, TableBody, TableRow, TableCell, Button, Chip, Stack
} from '@mui/material';
import { green, red, blue, orange, yellow } from '@mui/material/colors'; // Import additional colors if needed for specific statuses


const DashboardPage: React.FC = () => {
  const [usdtBalance, setUsdtBalance] = useState<AccountBalanceDetail | null>(null);
  const [botSettings, setBotSettings] = useState<BotSettingsData | null>(null);
  const [recentTrades, setRecentTrades] = useState<TradeData[]>([]);
  const [openPositions, setOpenPositions] = useState<OpenPositionData[]>([]); 

  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<{[key: string]: boolean}>({});
  const [errorMessages, setErrorMessages] = useState<string[]>([]);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  const [botStatus, setBotStatus] = useState<BotStatusResponse | null>(null);
  const [isBotStatusLoading, setIsBotStatusLoading] = useState<boolean>(true);
  const [isBotActionLoading, setIsBotActionLoading] = useState<boolean>(false);

  const fetchData = useCallback(async () => {
    // No need to set sub-loaders if the main loader is already active
    if (!loading) {
        setIsBotStatusLoading(true);
    }
    setErrorMessages([]);
    
    // Fetch status separately to not block UI
    getBotStatus().then(status => {
        setBotStatus(status);
    }).catch(error => {
        console.error("Failed to fetch bot status", error);
        setErrorMessages(prev => [...prev.filter(m => !m.includes('status')), 'Could not fetch bot status.']);
    }).finally(() => setIsBotStatusLoading(false));

    // Fetch the rest of the data
    const results = await Promise.allSettled([
      getAccountOverview(),
      getBotSettings(),
      getTradesHistory(0, 5), // Fetch 5 most recent trades
      getOpenPositions() // Fetch open positions
    ]);

    const newErrorMessages: string[] = [];
    if (results[0].status === 'fulfilled') setUsdtBalance(results[0].value); else newErrorMessages.push('Balance fetch failed.');
    if (results[1].status === 'fulfilled') setBotSettings(results[1].value); else newErrorMessages.push('Settings fetch failed.');
    if (results[2].status === 'fulfilled') setRecentTrades(results[2].value || []); else newErrorMessages.push('Recent trades fetch failed.');
    if (results[3].status === 'fulfilled') setOpenPositions(results[3].value || []); else newErrorMessages.push('Open positions fetch failed.');

    if (newErrorMessages.length > 0) {
      setErrorMessages(prev => [...prev.filter(m => !newErrorMessages.includes(m.split(':')[0])), ...newErrorMessages]);
    }
    setLoading(false); // Turn off main loader after the first fetch
  }, [loading]);

  useEffect(() => {
    fetchData(); 
    const intervalId = setInterval(() => {
        // On interval, we don't want to set the main 'loading' to true
        // fetchData will handle its own sub-loaders
        fetchData();
    }, 30000); // Refresh data every 30 seconds
    return () => clearInterval(intervalId); // Cleanup interval on component unmount
  }, [fetchData]);

  const handleStartBot = async () => {
    setIsBotActionLoading(true);
    setSuccessMessage(null); // Clear any previous success message
    try {
        const response = await startBot();
        setSuccessMessage(response.message);
        await fetchData(); // Refresh data to reflect bot status change
    } catch (err: any) {
        setErrorMessages(prev => [...prev, `Failed to start bot: ${err.response?.data?.detail || err.message}`]);
    } finally {
        setIsBotActionLoading(false);
    }
  };

  const handleStopBot = async () => {
    setIsBotActionLoading(true);
    setSuccessMessage(null); // Clear any previous success message
    try {
        const response = await stopBot();
        setSuccessMessage(response.message);
        await fetchData(); // Refresh data to reflect bot status change
    } 
    // Don't throw error if bot is already stopped, as per bot_process_manager
    catch (err: any) {
        const detail = err.response?.data?.detail || err.message;
        if (!detail.toLowerCase().includes("already stopped") && !detail.toLowerCase().includes("stale pid")) {
            setErrorMessages(prev => [...prev, `Failed to stop bot: ${detail}`]);
        } else {
            setSuccessMessage(detail); // Show message that it's already stopped
            fetchData(); // Refresh data to get correct status
        }
    } finally {
        setIsBotActionLoading(false);
    }
  };
  
  const handleClosePosition = async (symbol: string) => {
    setActionLoading(prev => ({ ...prev, [symbol]: true }));
    try {
      const response = await closePosition({ symbol });
      setSuccessMessage(response.message || `Close signal for ${symbol} sent.`);
      await fetchData(); // Refresh data to reflect closed position
    } catch (err: any) {
      setErrorMessages(prev => [...prev, `Failed to close ${symbol}: ${err.message}`]);
    } finally {
      setActionLoading(prev => ({ ...prev, [symbol]: false }));
    }
  };

  const isRunning = botStatus?.status === 'running';

  // Helper function to calculate TP/SL percentage and dollar value
  const calculatePnLAtPrice = (
    entryPrice: number | null | undefined, 
    targetPrice: number | null | undefined, 
    initialMargin: number | null | undefined, 
    leverage: number | null | undefined,
    side: 'long' | 'short' | undefined
  ): { percentage: string; dollar: string; color: string } => { // Added color to return type
    if (entryPrice == null || targetPrice == null || initialMargin == null || leverage == null || entryPrice === 0 || initialMargin === 0 || leverage === 0 || side == null) {
      return { percentage: 'N/A', dollar: 'N/A', color: 'text.secondary' }; // Default color for N/A
    }

    let pnlPercentage = 0;
    // Calculate percentage based on trade direction
    if (side === 'long') {
      pnlPercentage = ((targetPrice - entryPrice) / entryPrice) * 100;
    } else { // short
      pnlPercentage = ((entryPrice - targetPrice) / entryPrice) * 100;
    }
    
    // Calculate dollar PnL based on initial margin and leverage
    // Note: This calculation assumes a direct relationship and might need adjustment
    // based on exact exchange PnL calculation logic (e.g., funding fees, exact contract value)
    const dollarPnL = (initialMargin * leverage * pnlPercentage) / 100;

    // Determine color based on PnL value (green for profit, red for loss)
    const color = dollarPnL >= 0 ? 'success.main' : 'error.main';

    return { 
      percentage: `${dollarPnL >= 0 ? '+' : ''}${pnlPercentage.toFixed(2)}%`, // Added + for positive percentage
      dollar: `${dollarPnL >= 0 ? '+' : ''}$${dollarPnL.toFixed(2)}`, // Added + for positive dollar
      color: color // Return the determined color
    };
  };

  // Helper function to get status chip details for recent trades
  const getTradeStatusChip = (status: string, exitReason?: string | null) => {
    let label = status.replace(/_/g, ' '); // Replace underscores for display
    let color: 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' = 'default';

    switch (status) {
      case 'PENDING_OPEN':
        color = 'info';
        label = "PENDING OPEN";
        break;
      case 'OPEN':
        color = 'info';
        label = "OPEN";
        break;
      case 'CLOSED_TP':
        color = 'success';
        label = "CLOSED (TP)";
        break;
      case 'CLOSED_SL':
        color = 'error';
        label = "CLOSED (SL)";
        break;
      case 'CLOSED_MANUAL':
        color = 'primary'; // Or another color
        label = "CLOSED (Manual)";
        break;
      case 'CLOSED_EXCHANGE':
        color = 'default'; // Or gray
        label = "CLOSED (Exchange)";
        break;
      case 'CLOSED_LIQUIDATION':
        color = 'error';
        label = "LIQUIDATED";
        break;
      case 'ERROR':
        color = 'error';
        break;
      case 'CANCELLED':
        color = 'warning';
        break;
      default:
        color = 'default';
        break;
    }

    // Override label and color based on exitReason if available for more specificity in CLOSED_EXCHANGE cases
    // This assumes exitReason is consistently set by bot_engine.py
    if (status === 'CLOSED_EXCHANGE' && exitReason) {
      if (exitReason === 'StopLoss_Hit_Inferred') {
          label = "CLOSED (SL)"; // Override to SL
          color = 'error';
      } else if (exitReason === 'TakeProfit_Hit_Inferred') {
          label = "CLOSED (TP)"; // Override to TP
          color = 'success';
      } else if (exitReason === 'Manual_Close_Inferred' || exitReason === 'Closed_by_Manual_Action') {
          label = "CLOSED (Manual)"; // Override to Manual
          color = 'primary'; // Or other suitable color
      }
      // Add other exit reasons if needed
    }


    return <Chip label={label.toUpperCase()} size="small" color={color} variant="outlined" />;
  };


  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
        Dashboard
      </Typography>

      {errorMessages.length > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {Array.from(new Set(errorMessages)).map((msg, idx) => <div key={idx}>{msg}</div>)}
        </Alert>
      )}
      {successMessage && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccessMessage(null)}>{successMessage}</Alert>}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}><CircularProgress /></Box>
      ) : (
        <Grid container spacing={3}>
          {/* Left Column */}
          <Grid item xs={12} md={5} lg={4}>
            <Stack spacing={3}>
              <Paper sx={{ p: 2 }}>
                  <Typography variant="h6" gutterBottom>Bot Control</Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 2 }}> {/* FIXED: Missing closing bracket here */}
                      <Typography variant="body1">Status:</Typography>
                      {isBotStatusLoading ? <CircularProgress size={20} /> : (
                          <Chip 
                              label={botStatus?.status.toUpperCase().replace("_", " ") || 'UNKNOWN'}
                              color={isRunning ? 'success' : 'error'}
                              size="small"
                          />
                      )}
                  </Box>
                  <Stack direction="row" spacing={2}>
                      <Button variant="contained" color="success" onClick={handleStartBot} disabled={isRunning || isBotActionLoading}>{isBotActionLoading && !isRunning ? <CircularProgress size={24} color="inherit" /> : "Start Bot"}</Button>
                      <Button variant="contained" color="error" onClick={handleStopBot} disabled={!isRunning || isBotActionLoading}>{isBotActionLoading && isRunning ? <CircularProgress size={24} color="inherit" /> : "Stop Bot"}</Button>
                  </Stack>
              </Paper>
              <Paper sx={{ p: 2 }}>
                  <Typography variant="h6" gutterBottom>USDT Account</Typography>
                  {usdtBalance ? (
                    <List dense>
                      <ListItem disablePadding><ListItemText primary="Available:" secondary={`${usdtBalance.free?.toFixed(2) ?? 'N/A'} USDT`} /></ListItem>
                      <ListItem disablePadding><ListItemText primary="In Orders:" secondary={`${usdtBalance.used?.toFixed(2) ?? 'N/A'} USDT`} /></ListItem>
                      <Divider sx={{ my: 1, borderColor: 'rgba(255,255,255,0.2)' }} />
                      <ListItem disablePadding><ListItemText primaryTypographyProps={{fontWeight: 'bold'}} primary="Total:" secondaryTypographyProps={{fontWeight: 'bold'}} secondary={`${usdtBalance.total?.toFixed(2) ?? 'N/A'} USDT`} /></ListItem>
                    </List>
                  ) : (<Typography variant="body2" color="text.secondary">No balance data available.</Typography>)}
              </Paper>
            </Stack>
          </Grid>
          
          {/* Right Column */}
          <Grid item xs={12} md={7} lg={8}>
            <Paper sx={{ p: 2, height: '100%' }}>
              <Typography variant="h6" gutterBottom>Current Settings</Typography>
              {botSettings ? (
                <Grid container spacing={2} sx={{p: 1}}>
                  <Grid item xs={12}><ListItemText primary="Active Symbols" secondary={botSettings.symbols_to_trade.join(', ') || 'None selected'} /></Grid>
                  <Grid item xs={6} sm={4}><ListItemText primary="Max Trades:" secondary={botSettings.max_concurrent_trades} /></Grid>
                  <Grid item xs={6} sm={4}><ListItemText primary="Amount Mode:" secondary={botSettings.trade_amount_mode.replace("_", " ")} /></Grid>
                  <Grid item xs={6} sm={4}><ListItemText primary="Fixed Amount:" secondary={`$${botSettings.fixed_trade_amount_usd.toFixed(2)}`} /></Grid>
                  <Grid item xs={6} sm={4}><ListItemText primary="Percent Amount:" secondary={`${botSettings.percentage_trade_amount.toFixed(1)}%`} /></Grid>
                  <Grid item xs={6} sm={4}><ListItemText primary="Daily Loss Limit:" secondary={`${botSettings.daily_loss_limit_percentage ? botSettings.daily_loss_limit_percentage + '%' : 'Not Set' }`} /></Grid>
                </Grid>
              ) : (<Typography variant="body2" color="text.secondary">Could not load bot settings.</Typography>)}
            </Paper>
          </Grid>

          {/* Open Positions Table */}
          <Grid item xs={12}>
            <Paper sx={{ p: 2, mt: 1 }}>
                <Typography variant="h6" gutterBottom>Open Positions</Typography>
                {openPositions.length > 0 ? (
                <TableContainer>
                    <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>Symbol</TableCell>
                            <TableCell align="right">Side</TableCell>
                            <TableCell align="right">Contracts</TableCell>
                            <TableCell align="right">Entry Price</TableCell>
                            <TableCell align="right">Mark Price</TableCell>
                            <TableCell align="right">Unrealized PNL</TableCell>
                            <TableCell align="right">PNL (%)</TableCell>
                            <TableCell align="right">Engaged Margin</TableCell>
                            <TableCell align="right">Leverage</TableCell>
                            <TableCell align="right">TP</TableCell>
                            <TableCell align="right">TP PNL ($)</TableCell>
                            <TableCell align="right">SL</TableCell>
                            <TableCell align="right">SL PNL ($)</TableCell>
                            <TableCell align="center">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {openPositions.map((pos) => {
                            const tpPnL = calculatePnLAtPrice(pos.entryPrice, pos.takeProfitPrice, pos.initialMargin, pos.leverage, pos.side);
                            const slPnL = calculatePnLAtPrice(pos.entryPrice, pos.stopLossPrice, pos.initialMargin, pos.leverage, pos.side);
                            const currentPnLPercentage = (pos.unrealizedPnl != null && pos.initialMargin != null && pos.initialMargin !== 0) 
                                ? `${((pos.unrealizedPnl / pos.initialMargin) * 100).toFixed(2)}%`
                                : 'N/A';

                            return (
                                <TableRow hover key={pos.id || pos.symbol}>
                                    <TableCell>{pos.symbol.replace('/USDT:USDT', '')}</TableCell>
                                    <TableCell align="right"><Chip label={pos.side?.toUpperCase()} size="small" color={pos.side === 'long' ? 'success' : 'error'} variant="outlined" /></TableCell>
                                    <TableCell align="right">{pos.contracts?.toFixed(4)}</TableCell>
                                    <TableCell align="right">{pos.entryPrice?.toFixed(4)}</TableCell>
                                    <TableCell align="right">{pos.markPrice?.toFixed(4)}</TableCell>
                                    <TableCell align="right" sx={{ color: (pos.unrealizedPnl ?? 0) >= 0 ? 'success.main' : 'error.main' }}>{pos.unrealizedPnl?.toFixed(2)}</TableCell>
                                    <TableCell align="right" sx={{ color: (pos.unrealizedPnl ?? 0) >= 0 ? 'success.main' : 'error.main' }}>{currentPnLPercentage}</TableCell>
                                    <TableCell align="right">{pos.initialMargin?.toFixed(2) ?? 'N/A'}</TableCell>
                                    <TableCell align="right">{pos.leverage ?? 'N/A'}x</TableCell>
                                    <TableCell align="right" sx={{ color: 'success.main' }}> {/* Changed TP price to green */}
                                        {pos.takeProfitPrice?.toFixed(4) ?? 'N/A'}
                                        {pos.takeProfitPrice && tpPnL.percentage !== 'N/A' && <Typography variant="caption" display="block">{tpPnL.percentage}</Typography>}
                                    </TableCell>
                                    <TableCell align="right" sx={{ color: tpPnL.color, fontWeight: 'bold' }}>{tpPnL.dollar}</TableCell> {/* Applied color and bold */}
                                    <TableCell align="right" sx={{ color: 'error.main' }}> {/* Changed SL price to red */}
                                        {pos.stopLossPrice?.toFixed(4) ?? 'N/A'}
                                        {pos.stopLossPrice && slPnL.percentage !== 'N/A' && <Typography variant="caption" display="block">{slPnL.percentage}</Typography>}
                                    </TableCell>
                                    <TableCell align="right" sx={{ color: slPnL.color, fontWeight: 'bold' }}>{slPnL.dollar}</TableCell> {/* Applied color and bold */}
                                    <TableCell align="center">
                                        <Button variant="outlined" color="warning" size="small" onClick={() => handleClosePosition(pos.symbol)} disabled={actionLoading[pos.symbol]}>
                                            {actionLoading[pos.symbol] ? <CircularProgress size={16} /> : "Close"}
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            );
                        })}
                    </TableBody>
                    </Table>
                </TableContainer>
                ) : (
                <Typography variant="body2" color="text.secondary">No open positions found.</Typography>
                )}
            </Paper>
          </Grid>

          {/* Recent Trades Table */}
          <Grid item xs={12}>
            <Paper sx={{ p: 2, mt: 1 }}>
                <Typography variant="h6" gutterBottom>Recent Trades</Typography>
                {recentTrades.length > 0 ? (
                <TableContainer>
                    <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>Symbol</TableCell>
                            <TableCell align="right">Side</TableCell>
                            <TableCell align="right">Status</TableCell> {/* Will be dynamically set by getTradeStatusChip */}
                            <TableCell align="right">Entry Price</TableCell>
                            <TableCell align="right">PNL</TableCell>
                            <TableCell>Opened At</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {recentTrades.map((trade) => (
                        <TableRow hover key={trade.id}>
                            <TableCell>{trade.symbol.replace('/USDT:USDT', '')}</TableCell>
                            <TableCell align="right"><Chip label={trade.direction} size="small" color={trade.direction === 'LONG' ? 'success' : 'error'} variant="outlined" /></TableCell>
                            {/* MODIFIED: Use getTradeStatusChip for dynamic status display */}
                            <TableCell align="right">{getTradeStatusChip(trade.status, trade.exit_reason)}</TableCell> 
                            <TableCell align="right">{trade.entry_price?.toFixed(4) ?? 'N/A'}</TableCell>
                            <TableCell align="right" sx={{ color: (trade.pnl ?? 0) >= 0 ? 'success.main' : 'error.main' }}>{trade.pnl?.toFixed(2) ?? 'N/A'}</TableCell>
                            <TableCell>{trade.timestamp_opened ? new Date(trade.timestamp_opened).toLocaleString() : 'N/A'}</TableCell>
                        </TableRow>
                        ))}
                    </TableBody>
                    </Table>
                </TableContainer>
                ) : (
                <Typography variant="body2" color="text.secondary">No recent trades found.</Typography>
                )}
            </Paper>
          </Grid>

        </Grid>
      )}
    </Box>
  );
};

export default DashboardPage;
