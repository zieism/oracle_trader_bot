// src/pages/AnalysisLogPage.tsx
import React, { useEffect, useState, useRef, useCallback } from 'react';
import { 
    Typography, Box, CircularProgress, Alert, Paper, 
    TableContainer, Table, TableHead, TableRow, TableCell, TableBody,
    Chip, Stack, Button, TextField, MenuItem, Select, FormControl, InputLabel,
    Divider
} from '@mui/material';
import { blue, green, orange, purple, red, yellow, grey } from '@mui/material/colors'; // Added grey for default/N/A symbols
import { styled } from '@mui/system'; 
import LiveTvIcon from '@mui/icons-material/LiveTv';
import StopIcon from '@mui/icons-material/StopCircle';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import FilterListIcon from '@mui/icons-material/FilterList';

// Import necessary type from apiService (not the setupWebSocket function directly here)
import { AnalysisLogEntry, setupAnalysisLogWebSocket } from '../services/apiService'; 

// Styled component for symbol coloring
const SymbolColoredCell = styled(TableCell)<{ symbolcolor: string }>`
    color: ${(props) => props.symbolcolor};
    font-weight: bold;
`;

// Helper function to get a consistent color for each symbol
const getSymbolColor = (symbol: string): string => {
    // Return a default color if symbol is 'N/A' or empty
    if (!symbol || symbol === 'N/A') return grey[500]; 
    const colors = [blue[300], green[300], orange[300], purple[300], red[300], yellow[300]];
    let hash = 0;
    for (let i = 0; i < symbol.length; i++) {
        hash = symbol.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash % colors.length)];
};


const AnalysisLogPage: React.FC = () => {
    // Load logs from localStorage on initial render
    const [logs, setLogs] = useState<AnalysisLogEntry[]>(() => {
        try {
            const savedLogs = localStorage.getItem('analysisLogs');
            return savedLogs ? JSON.parse(savedLogs) : [];
        } catch (error) {
            console.error("Failed to load logs from localStorage:", error);
            return [];
        }
    });

    const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
    const [error, setError] = useState<string | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const tableContainerRef = useRef<HTMLDivElement>(null);

    // Filter states
    const [filterSymbol, setFilterSymbol] = useState<string>('ALL');
    const [filterStrategy, setFilterStrategy] = useState<string>('ALL');
    const [filterDecision, setFilterDecision] = useState<string>('ALL');
    const [filterLevel, setFilterLevel] = useState<string>('ALL');
    const [filterText, setFilterText] = useState<string>('');

    // Unique values for filter dropdowns - computed from current logs
    // These need to be re-computed whenever 'logs' state changes
    const uniqueSymbols = ['ALL', ...Array.from(new Set(logs.map(log => log.symbol))).sort()];
    const uniqueStrategies = ['ALL', ...Array.from(new Set(logs.map(log => log.strategy))).sort()];
    const uniqueDecisions = ['ALL', ...Array.from(new Set(logs.map(log => log.decision))).sort()];
    const uniqueLevels = ['ALL', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'DEBUG', 'SUCCESS']; 

    // Filtered logs based on state
    const filteredLogs = logs.filter(log => {
        if (filterSymbol !== 'ALL' && log.symbol !== filterSymbol) return false;
        if (filterStrategy !== 'ALL' && log.strategy !== filterStrategy) return false;
        if (filterDecision !== 'ALL' && log.decision !== filterDecision) return false;
        // Case-insensitive comparison for log level
        if (filterLevel !== 'ALL' && log.level.toUpperCase() !== filterLevel.toUpperCase()) return false; 
        // Case-insensitive search within message
        if (filterText && !log.message.toLowerCase().includes(filterText.toLowerCase())) return false;
        return true;
    });

    // Auto-scroll to the top to see the latest log (since logs are reversed)
    const scrollToTop = useCallback(() => {
        if (tableContainerRef.current) {
            tableContainerRef.current.scrollTop = 0;
        }
    }, []);

    const connectWebSocket = useCallback(() => {
        if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
            console.log("WebSocket already open or connecting.");
            return;
        }
        
        setError(null);
        setConnectionStatus('connecting');
        console.log("Attempting to connect WebSocket...");

        // Ensure setupAnalysisLogWebSocket is correctly imported and available
        const ws = setupAnalysisLogWebSocket(
            (logEntry) => {
                setLogs((prevLogs) => {
                    const newLogs = [logEntry, ...prevLogs]; // Prepend new log for reverse order
                    const limitedLogs = newLogs.slice(0, 500); // Keep latest 500 logs to prevent excessive memory usage
                    localStorage.setItem('analysisLogs', JSON.stringify(limitedLogs)); // Save to localStorage
                    return limitedLogs;
                });
                setTimeout(scrollToTop, 100); // Scroll to top after logs are rendered
            },
            (event) => {
                console.error('WebSocket connection error:', event);
                setError('WebSocket connection error. See console for details. Attempting reconnect...');
                setConnectionStatus('error');
            },
            (event) => {
                setConnectionStatus('disconnected');
                console.log('WebSocket connection closed:', event);
                // Only attempt to reconnect if it wasn't a deliberate close by the user
                if (!(wsRef.current && wsRef.current.readyState === WebSocket.CLOSED)) {
                    setError('WebSocket connection closed unexpectedly. Attempting to reconnect in 5 seconds...');
                    setTimeout(connectWebSocket, 5000); // Attempt to reconnect after a delay
                } else {
                    setError(null); // Clear error if disconnected manually
                }
            },
            () => {
                setConnectionStatus('connected');
                console.log('WebSocket connection opened.');
            }
        );
        wsRef.current = ws;
    }, [scrollToTop]); // Dependency array for useCallback

    const disconnectWebSocket = useCallback(() => {
        if (wsRef.current) {
            // Explicitly set a flag or state to prevent auto-reconnect
            // For this simple example, we'll rely on the readyState check inside onclose
            // But a more robust solution would involve a separate state like `isManualDisconnect`
            if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
                wsRef.current.close(1000, "Manual Disconnect"); // Code 1000 for normal closure
            }
            wsRef.current = null;
            setConnectionStatus('disconnected');
            setError(null); // Clear any existing errors
            console.log("WebSocket explicitly disconnected.");
        }
    }, []);

    useEffect(() => {
        // Initial connection attempt on component mount
        connectWebSocket(); 

        // Cleanup function for when the component unmounts
        return () => {
            // Ensure the WebSocket is closed when the component is removed from DOM
            if (wsRef.current) {
                // Use a different close code or a flag to differentiate from unexpected closes
                wsRef.current.close(1000, "Component Unmount"); 
                wsRef.current = null;
            }
        };
    }, [connectWebSocket]); // Dependency array to ensure effect runs once or if connectWebSocket changes

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'connected': return 'success';
            case 'disconnected': return 'error';
            case 'connecting': return 'info';
            case 'error': return 'warning';
            default: return 'default';
        }
    };

    const getLevelColor = (level: string) => {
        switch (level.toUpperCase()) {
            case 'ERROR': return 'error';
            case 'CRITICAL': return 'error';
            case 'WARNING': return 'warning';
            case 'INFO': return 'info';
            case 'DEBUG': 'default'; // primary for DEBUG if you prefer
            case 'SUCCESS': return 'success';
            default: return 'default';
        }
    };

    return (
        <Box>
            <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
                Bot Analysis Logs
            </Typography>

            <Paper sx={{ p: 2, mb: 3 }}>
                <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
                    <Typography variant="body1">Connection Status:</Typography>
                    <Chip 
                        label={connectionStatus.toUpperCase()} 
                        color={getStatusColor(connectionStatus)} 
                        size="small" 
                        icon={<LiveTvIcon />}
                    />
                    <Box sx={{ flexGrow: 1 }} /> 
                    <Button 
                        variant="outlined" 
                        color="success" 
                        onClick={connectWebSocket} 
                        disabled={connectionStatus === 'connected' || connectionStatus === 'connecting'}
                        startIcon={<PlayArrowIcon />}
                    >
                        Connect
                    </Button>
                    <Button 
                        variant="outlined" 
                        color="error" 
                        onClick={disconnectWebSocket} 
                        disabled={connectionStatus === 'disconnected'}
                        startIcon={<StopIcon />}
                    >
                        Disconnect
                    </Button>
                </Stack>
                {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}

                {/* Filters Section */}
                <Divider sx={{ my: 2 }} />
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="center" flexWrap="wrap">
                    <FilterListIcon sx={{ color: 'text.secondary' }} />
                    <FormControl size="small" sx={{ minWidth: 120 }}>
                        <InputLabel>Symbol</InputLabel>
                        <Select
                            value={filterSymbol}
                            label="Symbol"
                            onChange={(e) => setFilterSymbol(e.target.value as string)}
                        >
                            {uniqueSymbols.map((sym) => (
                                <MenuItem key={sym} value={sym}>{sym === 'ALL' ? 'ALL' : sym.replace('/USDT:USDT', '')}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>

                    <FormControl size="small" sx={{ minWidth: 120 }}>
                        <InputLabel>Strategy</InputLabel>
                        <Select
                            value={filterStrategy}
                            label="Strategy"
                            onChange={(e) => setFilterStrategy(e.target.value as string)}
                        >
                            {uniqueStrategies.map((strat) => (
                                <MenuItem key={strat} value={strat}>{strat}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>

                    <FormControl size="small" sx={{ minWidth: 120 }}>
                        <InputLabel>Decision</InputLabel>
                        <Select
                            value={filterDecision}
                            label="Decision"
                            onChange={(e) => setFilterDecision(e.target.value as string)}
                        >
                            {uniqueDecisions.map((dec) => (
                                <MenuItem key={dec} value={dec}>{dec}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>

                    <FormControl size="small" sx={{ minWidth: 120 }}>
                        <InputLabel>Level</InputLabel>
                        <Select
                            value={filterLevel}
                            label="Level"
                            onChange={(e) => setFilterLevel(e.target.value as string)}
                        >
                            {uniqueLevels.map((lvl) => (
                                <MenuItem key={lvl} value={lvl}>{lvl}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>

                    <TextField
                        size="small"
                        label="Filter Text"
                        value={filterText}
                        onChange={(e) => setFilterText(e.target.value)}
                        placeholder="Search message..."
                        sx={{ flexGrow: 1 }}
                    />
                </Stack>
            </Paper>

            {connectionStatus === 'connecting' && logs.length === 0 ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}><CircularProgress /></Box>
            ) : (
                <TableContainer component={Paper} ref={tableContainerRef} sx={{ maxHeight: '70vh', overflowY: 'auto' }}>
                    <Table size="small" stickyHeader>
                        <TableHead>
                            <TableRow>
                                <TableCell sx={{ minWidth: '100px' }}>Time</TableCell>
                                <TableCell sx={{ minWidth: '80px' }}>Level</TableCell>
                                <TableCell sx={{ minWidth: '120px' }}>Symbol</TableCell>
                                <TableCell sx={{ minWidth: '120px' }}>Strategy</TableCell>
                                <TableCell sx={{ minWidth: '120px' }}>Decision</TableCell>
                                <TableCell>Message</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {filteredLogs.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} align="center">No live analysis logs found or matching criteria. Ensure bot is running and connected.</TableCell>
                                </TableRow>
                            ) : (
                                filteredLogs.map((log, index) => (
                                    <TableRow key={index} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                                        <TableCell component="th" scope="row">
                                            <Typography variant="body2" color="text.secondary">
                                                {new Date(log.timestamp).toLocaleTimeString('en-US', { hour12: false })}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Chip 
                                                label={log.level.toUpperCase()} 
                                                size="small" 
                                                color={getLevelColor(log.level)} 
                                                variant="outlined"
                                            />
                                        </TableCell>
                                        <SymbolColoredCell symbolcolor={getSymbolColor(log.symbol)}>
                                            {log.symbol.replace('/USDT:USDT', '')}
                                        </SymbolColoredCell>
                                        <TableCell>
                                            <Typography variant="body2">{log.strategy}</Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="body2" sx={{ fontWeight: 'bold' }}>{log.decision}</Typography>
                                        </TableCell>
                                        <TableCell sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                                            <Typography variant="body2">{log.message}</Typography>
                                            {log.details && Object.keys(log.details).length > 0 && (
                                                <Typography variant="caption" color="text.disabled" sx={{ mt: 0.5, display: 'block' }}>
                                                    Details: {JSON.stringify(log.details, null, 2)}
                                                </Typography>
                                            )}
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </TableContainer>
            )}
        </Box>
    );
};

export default AnalysisLogPage;