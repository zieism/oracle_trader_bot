// src/pages/ServerLogPage.tsx
import React, { useEffect, useState, useCallback } from 'react';
import { 
    Typography, Box, CircularProgress, Alert, Paper, 
    TableContainer, Table, TableHead, TableRow, TableCell, TableBody,
    TextField, MenuItem, Button, Select, FormControl, InputLabel, Chip, Stack
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { getServerLogs, LogEntry } from '../services/apiService';

const ServerLogPage: React.FC = () => {
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    // Filter states
    const [logType, setLogType] = useState<'all' | 'api' | 'bot'>('all');
    const [logLimit, setLogLimit] = useState<number>(200);
    const [logLevel, setLogLevel] = useState<string>('INFO'); // Default to INFO, can be 'ALL' later
    const [searchText, setSearchText] = useState<string>('');

    const fetchLogs = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const fetchedLogs = await getServerLogs(logType, logLimit, true, logLevel === 'ALL' ? undefined : logLevel, searchText || undefined);
            setLogs(fetchedLogs);
        } catch (err: any) {
            console.error('Failed to fetch server logs:', err);
            setError(`Failed to fetch logs: ${err.response?.data?.detail || err.message}`);
        } finally {
            setLoading(false);
        }
    }, [logType, logLimit, logLevel, searchText]);

    useEffect(() => {
        fetchLogs();
        const intervalId = setInterval(fetchLogs, 15000); // Auto-refresh every 15 seconds
        return () => clearInterval(intervalId);
    }, [fetchLogs]);

    const getLevelColor = (level: string) => {
        switch (level.toUpperCase()) {
            case 'ERROR': return 'error';
            case 'CRITICAL': return 'error';
            case 'WARNING': return 'warning';
            case 'INFO': return 'info';
            case 'DEBUG': return 'primary'; // Or 'default'
            default: return 'default';
        }
    };

    return (
        <Box>
            <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
                Server Logs
            </Typography>

            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

            <Paper sx={{ p: 2, mb: 3 }}>
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }} alignItems="center">
                    <FormControl size="small" sx={{ minWidth: 120 }}>
                        <InputLabel>Log Type</InputLabel>
                        <Select
                            value={logType}
                            label="Log Type"
                            onChange={(e) => setLogType(e.target.value as 'all' | 'api' | 'bot')}
                        >
                            <MenuItem value="all">All Logs</MenuItem>
                            <MenuItem value="api">API Server</MenuItem>
                            <MenuItem value="bot">Bot Engine</MenuItem>
                        </Select>
                    </FormControl>

                    <FormControl size="small" sx={{ minWidth: 120 }}>
                        <InputLabel>Log Level</InputLabel>
                        <Select
                            value={logLevel}
                            label="Log Level"
                            onChange={(e) => setLogLevel(e.target.value as string)}
                        >
                            <MenuItem value="ALL">ALL</MenuItem>
                            <MenuItem value="INFO">INFO</MenuItem>
                            <MenuItem value="WARNING">WARNING</MenuItem>
                            <MenuItem value="ERROR">ERROR</MenuItem>
                            <MenuItem value="CRITICAL">CRITICAL</MenuItem>
                            <MenuItem value="DEBUG">DEBUG</MenuItem>
                        </Select>
                    </FormControl>

                    <TextField
                        size="small"
                        label="Limit"
                        type="number"
                        value={logLimit}
                        onChange={(e) => setLogLimit(Number(e.target.value))}
                        inputProps={{ min: 1, max: 1000 }}
                        sx={{ width: 80 }}
                    />

                    <TextField
                        size="small"
                        label="Search"
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                        placeholder="Search message..."
                        sx={{ flexGrow: 1 }}
                    />
                    
                    <Button 
                        variant="contained" 
                        onClick={fetchLogs} 
                        disabled={loading}
                        startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <RefreshIcon />}
                    >
                        {loading ? "Refreshing..." : "Refresh"}
                    </Button>
                </Stack>
            </Paper>

            {loading && logs.length === 0 ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}><CircularProgress /></Box>
            ) : (
                <TableContainer component={Paper}>
                    <Table size="small" stickyHeader>
                        <TableHead>
                            <TableRow>
                                <TableCell sx={{ width: '150px' }}>Timestamp</TableCell>
                                <TableCell sx={{ width: '80px' }}>Level</TableCell>
                                <TableCell sx={{ width: '150px' }}>Source</TableCell>
                                <TableCell>Message</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {logs.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={4} align="center">No logs found matching criteria.</TableCell>
                                </TableRow>
                            ) : (
                                logs.map((log, index) => (
                                    <TableRow key={index} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                                        <TableCell component="th" scope="row">
                                            <Typography variant="body2" color="text.secondary">
                                                {log.timestamp}
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
                                        <TableCell>
                                            <Typography variant="body2">{log.name}</Typography>
                                        </TableCell>
                                        <TableCell sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                                            <Typography variant="body2">{log.message}</Typography>
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

export default ServerLogPage;