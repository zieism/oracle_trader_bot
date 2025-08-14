// src/features/settings/SettingsPage.tsx
import React, { useEffect, useState, useCallback } from 'react';
import { 
  getSystemSettings, 
  updateSystemSettings, 
  resetSystemSettings,
  SystemSettings,
  SystemSettingsUpdate
} from '@services/apiClient';
import { CONFIG } from '@services/apiClient';
import {
  Container, Typography, Paper, Grid, TextField, Button, CircularProgress,
  Alert, FormControl, InputLabel, Box, Tabs, Tab, Switch, FormControlLabel,
  Divider, IconButton, InputAdornment, Dialog, DialogTitle, DialogContent,
  DialogActions, Chip, Autocomplete
} from '@mui/material';
import { Visibility, VisibilityOff, RestartAlt } from '@mui/icons-material';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [originalSettings, setOriginalSettings] = useState<SystemSettings | null>(null);
  const [tabValue, setTabValue] = useState(0);
  
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [resetting, setResetting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  // Secret visibility toggles
  const [showSecrets, setShowSecrets] = useState<{[key: string]: boolean}>({
    KUCOIN_API_KEY: false,
    KUCOIN_API_SECRET: false,
    KUCOIN_API_PASSPHRASE: false,
    POSTGRES_PASSWORD: false,
  });

  // Reset confirmation dialog
  const [resetDialogOpen, setResetDialogOpen] = useState<boolean>(false);

  const fetchSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const settingsData = await getSystemSettings();
      setSettings(settingsData);
      setOriginalSettings(JSON.parse(JSON.stringify(settingsData))); // Deep clone
    } catch (err: any) {
      setError(`Failed to fetch settings: ${err?.response?.data?.detail || err.message}`);
      console.error('Error fetching settings:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const handleChange = (field: keyof SystemSettings) => (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement> | any
  ) => {
    if (!settings) return;

    const value = event.target.value;
    let processedValue: any = value;

    // Type conversion for numeric fields
    const numericFields = [
      'CANDLE_LIMIT_BOT', 'LOOP_SLEEP_DURATION_SECONDS_BOT', 'DELAY_BETWEEN_SYMBOL_PROCESSING_SECONDS_BOT',
      'FIXED_USD_AMOUNT_PER_TRADE', 'BOT_DEFAULT_LEVERAGE', 'MAX_CONCURRENT_TRADES_BOT_CONFIG',
      'PERCENTAGE_TRADE_AMOUNT_BOT_CONFIG', 'DAILY_LOSS_LIMIT_PERCENTAGE_BOT_CONFIG',
      'REGIME_ADX_PERIOD', 'REGIME_ADX_WEAK_TREND_THRESHOLD', 'REGIME_ADX_STRONG_TREND_THRESHOLD',
      'REGIME_BBW_PERIOD', 'REGIME_BBW_STD_DEV', 'REGIME_BBW_LOW_THRESHOLD', 'REGIME_BBW_HIGH_THRESHOLD',
      'TREND_EMA_FAST_PERIOD', 'TREND_EMA_MEDIUM_PERIOD', 'TREND_EMA_SLOW_PERIOD',
      'TREND_RSI_PERIOD', 'TREND_RSI_OVERBOUGHT', 'TREND_RSI_OVERSOLD',
      'TREND_RSI_BULL_ZONE_MIN', 'TREND_RSI_BEAR_ZONE_MAX',
      'TREND_MACD_FAST', 'TREND_MACD_SLOW', 'TREND_MACD_SIGNAL',
      'TREND_ATR_PERIOD_SL_TP', 'TREND_ATR_MULTIPLIER_SL', 'TREND_TP_RR_RATIO', 'TREND_MIN_SIGNAL_STRENGTH',
      'RANGE_RSI_PERIOD', 'RANGE_RSI_OVERBOUGHT', 'RANGE_RSI_OVERSOLD',
      'RANGE_BBANDS_PERIOD', 'RANGE_BBANDS_STD_DEV', 'RANGE_ATR_PERIOD_SL_TP',
      'RANGE_ATR_MULTIPLIER_SL', 'RANGE_TP_RR_RATIO', 'RANGE_MIN_SIGNAL_STRENGTH',
      'MAX_LOG_FILE_SIZE_MB', 'LOG_FILE_BACKUP_COUNT'
    ];

    if (numericFields.includes(field)) {
      processedValue = value === '' ? '' : Number(value);
    }

    setSettings(prev => ({
      ...prev!,
      [field]: processedValue
    }));
    setSuccessMessage(null);
  };

  const handleSwitchChange = (field: keyof SystemSettings) => (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    if (!settings) return;

    setSettings(prev => ({
      ...prev!,
      [field]: event.target.checked
    }));
    setSuccessMessage(null);
  };

  const handleArrayChange = (field: keyof SystemSettings) => (
    _event: React.SyntheticEvent, value: string[]
  ) => {
    if (!settings) return;

    setSettings(prev => ({
      ...prev!,
      [field]: value
    }));
    setSuccessMessage(null);
  };

  const toggleSecretVisibility = (field: string) => {
    setShowSecrets(prev => ({
      ...prev,
      [field]: !prev[field]
    }));
  };

  const handleSave = async () => {
    if (!settings || !originalSettings) return;

    setSaving(true);
    setError(null);
    setSuccessMessage(null);

    try {
      // Create update payload with only changed fields
      const updates: SystemSettingsUpdate = {};
      
      (Object.keys(settings) as (keyof SystemSettings)[]).forEach(key => {
        if (settings[key] !== originalSettings[key]) {
          // Skip updating secrets that are still showing "***"
          if (['KUCOIN_API_KEY', 'KUCOIN_API_SECRET', 'KUCOIN_API_PASSPHRASE', 'POSTGRES_PASSWORD'].includes(key)) {
            if (settings[key] !== '***' && settings[key] !== '') {
              (updates as any)[key] = settings[key];
            }
          } else {
            (updates as any)[key] = settings[key];
          }
        }
      });

      if (Object.keys(updates).length === 0) {
        setSuccessMessage("No changes to save");
        return;
      }

      const updatedSettings = await updateSystemSettings(updates);
      setSettings(updatedSettings);
      setOriginalSettings(JSON.parse(JSON.stringify(updatedSettings)));
      setSuccessMessage(`Settings updated successfully! Updated: ${Object.keys(updates).join(', ')}`);
      
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err.message || "Failed to save settings";
      setError(errorMessage);
      console.error('Error saving settings:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    setResetting(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await resetSystemSettings();
      await fetchSettings(); // Reload settings
      setSuccessMessage("Settings reset to defaults successfully!");
      setResetDialogOpen(false);
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err.message || "Failed to reset settings";
      setError(errorMessage);
      console.error('Error resetting settings:', err);
    } finally {
      setResetting(false);
    }
  };

  const hasChanges = settings && originalSettings ? 
    JSON.stringify(settings) !== JSON.stringify(originalSettings) : false;

  if (loading) {
    return (
      <Container sx={{ display: 'flex', justifyContent: 'center', mt: 5 }}>
        <CircularProgress />
      </Container>
    );
  }

  if (!settings) {
    return (
      <Container maxWidth="lg" sx={{ mt: 2 }}>
        <Alert severity="error">Failed to load settings</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 2, mb: 4 }}>
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h5" component="h1" color="primary">
            System Settings
          </Typography>
          <Button
            variant="outlined"
            color="warning"
            startIcon={<RestartAlt />}
            onClick={() => setResetDialogOpen(true)}
            disabled={saving || resetting}
          >
            Reset to Defaults
          </Button>
        </Box>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        {successMessage && <Alert severity="success" sx={{ mb: 2 }}>{successMessage}</Alert>}

        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)} variant="scrollable">
            <Tab label="Exchange" />
            <Tab label="Trading" />
            <Tab label="Analysis" />
            <Tab label="Connectivity" />
            <Tab label="Database" />
            <Tab label="Logging" />
            <Tab label="System" />
          </Tabs>
        </Box>

        {/* Exchange Configuration Tab */}
        <TabPanel value={tabValue} index={0}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>KuCoin API Configuration</Typography>
              <Alert severity="warning" sx={{ mb: 2 }}>
                API credentials are stored securely. Values showing *** are masked for security.
              </Alert>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="API Key"
                value={settings.KUCOIN_API_KEY || ''}
                onChange={handleChange('KUCOIN_API_KEY')}
                variant="outlined"
                type={showSecrets.KUCOIN_API_KEY ? 'text' : 'password'}
                helperText="Your KuCoin API Key"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={() => toggleSecretVisibility('KUCOIN_API_KEY')} edge="end">
                        {showSecrets.KUCOIN_API_KEY ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="API Secret"
                value={settings.KUCOIN_API_SECRET || ''}
                onChange={handleChange('KUCOIN_API_SECRET')}
                variant="outlined"
                type={showSecrets.KUCOIN_API_SECRET ? 'text' : 'password'}
                helperText="Your KuCoin API Secret"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={() => toggleSecretVisibility('KUCOIN_API_SECRET')} edge="end">
                        {showSecrets.KUCOIN_API_SECRET ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="API Passphrase"
                value={settings.KUCOIN_API_PASSPHRASE || ''}
                onChange={handleChange('KUCOIN_API_PASSPHRASE')}
                variant="outlined"
                type={showSecrets.KUCOIN_API_PASSPHRASE ? 'text' : 'password'}
                helperText="Your KuCoin API Passphrase"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={() => toggleSecretVisibility('KUCOIN_API_PASSPHRASE')} edge="end">
                        {showSecrets.KUCOIN_API_PASSPHRASE ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.KUCOIN_SANDBOX}
                    onChange={handleSwitchChange('KUCOIN_SANDBOX')}
                  />
                }
                label="Sandbox Mode (Test Environment)"
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="KuCoin API Base URL"
                value={settings.KUCOIN_API_BASE_URL}
                onChange={handleChange('KUCOIN_API_BASE_URL')}
                variant="outlined"
                helperText="Base URL for KuCoin API"
              />
            </Grid>
          </Grid>
        </TabPanel>

        {/* Trading Configuration Tab */}
        <TabPanel value={tabValue} index={1}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Bot Trading Settings</Typography>
            </Grid>

            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom>Symbol Configuration</Typography>
              <Autocomplete
                multiple
                freeSolo
                options={['BTC/USDT:USDT', 'ETH/USDT:USDT', 'BNB/USDT:USDT']}
                value={settings.SYMBOLS_TO_TRADE_BOT}
                onChange={handleArrayChange('SYMBOLS_TO_TRADE_BOT')}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    variant="outlined"
                    label="Trading Symbols"
                    placeholder="Add trading pairs..."
                  />
                )}
                renderTags={(value: readonly string[], getTagProps) =>
                  value.map((option: string, index: number) => (
                    <Chip variant="outlined" label={option} {...getTagProps({ index })} key={index} />
                  ))
                }
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Primary Timeframe"
                value={settings.PRIMARY_TIMEFRAME_BOT}
                onChange={handleChange('PRIMARY_TIMEFRAME_BOT')}
                variant="outlined"
                helperText="e.g., 1h, 4h, 1d"
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Candle Limit"
                value={settings.CANDLE_LIMIT_BOT}
                onChange={handleChange('CANDLE_LIMIT_BOT')}
                variant="outlined"
                InputProps={{ inputProps: { min: 1 } }}
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Loop Sleep Duration (seconds)"
                value={settings.LOOP_SLEEP_DURATION_SECONDS_BOT}
                onChange={handleChange('LOOP_SLEEP_DURATION_SECONDS_BOT')}
                variant="outlined"
                InputProps={{ inputProps: { min: 1 } }}
              />
            </Grid>

            <Grid item xs={12}>
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle1" gutterBottom>Trade Parameters</Typography>
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Fixed USD per Trade"
                value={settings.FIXED_USD_AMOUNT_PER_TRADE}
                onChange={handleChange('FIXED_USD_AMOUNT_PER_TRADE')}
                variant="outlined"
                InputProps={{ inputProps: { min: 0.01, step: "0.01" } }}
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Default Leverage"
                value={settings.BOT_DEFAULT_LEVERAGE}
                onChange={handleChange('BOT_DEFAULT_LEVERAGE')}
                variant="outlined"
                InputProps={{ inputProps: { min: 1, max: 100 } }}
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Max Concurrent Trades"
                value={settings.MAX_CONCURRENT_TRADES_BOT_CONFIG}
                onChange={handleChange('MAX_CONCURRENT_TRADES_BOT_CONFIG')}
                variant="outlined"
                InputProps={{ inputProps: { min: 0 } }}
              />
            </Grid>
          </Grid>
        </TabPanel>

        {/* Analysis Configuration Tab */}
        <TabPanel value={tabValue} index={2}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Market Analysis Parameters</Typography>
            </Grid>

            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom>Market Regime Analysis</Typography>
            </Grid>

            <Grid item xs={12} sm={3}>
              <TextField
                fullWidth
                type="number"
                label="ADX Period"
                value={settings.REGIME_ADX_PERIOD}
                onChange={handleChange('REGIME_ADX_PERIOD')}
                variant="outlined"
                InputProps={{ inputProps: { min: 1 } }}
              />
            </Grid>

            <Grid item xs={12} sm={3}>
              <TextField
                fullWidth
                type="number"
                label="ADX Weak Trend Threshold"
                value={settings.REGIME_ADX_WEAK_TREND_THRESHOLD}
                onChange={handleChange('REGIME_ADX_WEAK_TREND_THRESHOLD')}
                variant="outlined"
                InputProps={{ inputProps: { min: 0, step: "0.1" } }}
              />
            </Grid>

            <Grid item xs={12} sm={3}>
              <TextField
                fullWidth
                type="number"
                label="ADX Strong Trend Threshold"
                value={settings.REGIME_ADX_STRONG_TREND_THRESHOLD}
                onChange={handleChange('REGIME_ADX_STRONG_TREND_THRESHOLD')}
                variant="outlined"
                InputProps={{ inputProps: { min: 0, step: "0.1" } }}
              />
            </Grid>

            <Grid item xs={12} sm={3}>
              <TextField
                fullWidth
                type="number"
                label="Bollinger Band Width Period"
                value={settings.REGIME_BBW_PERIOD}
                onChange={handleChange('REGIME_BBW_PERIOD')}
                variant="outlined"
                InputProps={{ inputProps: { min: 1 } }}
              />
            </Grid>

            <Grid item xs={12}>
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle1" gutterBottom>Trend Following Strategy</Typography>
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Fast EMA Period"
                value={settings.TREND_EMA_FAST_PERIOD}
                onChange={handleChange('TREND_EMA_FAST_PERIOD')}
                variant="outlined"
                InputProps={{ inputProps: { min: 1 } }}
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Medium EMA Period"
                value={settings.TREND_EMA_MEDIUM_PERIOD}
                onChange={handleChange('TREND_EMA_MEDIUM_PERIOD')}
                variant="outlined"
                InputProps={{ inputProps: { min: 1 } }}
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Slow EMA Period"
                value={settings.TREND_EMA_SLOW_PERIOD}
                onChange={handleChange('TREND_EMA_SLOW_PERIOD')}
                variant="outlined"
                InputProps={{ inputProps: { min: 1 } }}
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="RSI Period"
                value={settings.TREND_RSI_PERIOD}
                onChange={handleChange('TREND_RSI_PERIOD')}
                variant="outlined"
                InputProps={{ inputProps: { min: 1 } }}
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="RSI Overbought"
                value={settings.TREND_RSI_OVERBOUGHT}
                onChange={handleChange('TREND_RSI_OVERBOUGHT')}
                variant="outlined"
                InputProps={{ inputProps: { min: 0, max: 100 } }}
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="RSI Oversold"
                value={settings.TREND_RSI_OVERSOLD}
                onChange={handleChange('TREND_RSI_OVERSOLD')}
                variant="outlined"
                InputProps={{ inputProps: { min: 0, max: 100 } }}
              />
            </Grid>

            <Grid item xs={12}>
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle1" gutterBottom>Range Trading Strategy</Typography>
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Range RSI Period"
                value={settings.RANGE_RSI_PERIOD}
                onChange={handleChange('RANGE_RSI_PERIOD')}
                variant="outlined"
                InputProps={{ inputProps: { min: 1 } }}
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Bollinger Bands Period"
                value={settings.RANGE_BBANDS_PERIOD}
                onChange={handleChange('RANGE_BBANDS_PERIOD')}
                variant="outlined"
                InputProps={{ inputProps: { min: 1 } }}
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="ATR Period"
                value={settings.RANGE_ATR_PERIOD_SL_TP}
                onChange={handleChange('RANGE_ATR_PERIOD_SL_TP')}
                variant="outlined"
                InputProps={{ inputProps: { min: 1 } }}
              />
            </Grid>
          </Grid>
        </TabPanel>

        {/* Connectivity Tab */}
        <TabPanel value={tabValue} index={3}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Network & API Configuration</Typography>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Server Public IP"
                value={settings.SERVER_PUBLIC_IP}
                onChange={handleChange('SERVER_PUBLIC_IP')}
                variant="outlined"
                helperText="Public IP for CORS and external access"
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Internal API Base URL"
                value={settings.API_INTERNAL_BASE_URL}
                onChange={handleChange('API_INTERNAL_BASE_URL')}
                variant="outlined"
                helperText="Internal API URL for bot communication"
              />
            </Grid>

            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom>Frontend Configuration</Typography>
              <Alert severity="info" sx={{ mb: 2 }}>
                These values are read-only and configured via environment variables.
              </Alert>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Frontend API Base URL"
                value={CONFIG.API_BASE_URL}
                variant="outlined"
                disabled
                helperText="Configured via VITE_API_BASE_URL"
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Frontend WebSocket Base URL"
                value={CONFIG.WS_BASE_URL}
                variant="outlined"
                disabled
                helperText="Configured via VITE_WS_BASE_URL"
              />
            </Grid>

            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom>CORS Origins</Typography>
              <Autocomplete
                multiple
                freeSolo
                options={[]}
                value={settings.CORS_ALLOWED_ORIGINS}
                onChange={handleArrayChange('CORS_ALLOWED_ORIGINS')}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    variant="outlined"
                    label="Allowed Origins"
                    placeholder="Add CORS origins..."
                  />
                )}
                renderTags={(value: readonly string[], getTagProps) =>
                  value.map((option: string, index: number) => (
                    <Chip variant="outlined" label={option} {...getTagProps({ index })} key={index} />
                  ))
                }
              />
            </Grid>
          </Grid>
        </TabPanel>

        {/* Database Tab */}
        <TabPanel value={tabValue} index={4}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Database Configuration</Typography>
              <Alert severity="info" sx={{ mb: 2 }}>
                Database settings control the PostgreSQL connection. Password is masked for security.
              </Alert>
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Server"
                value={settings.POSTGRES_SERVER}
                onChange={handleChange('POSTGRES_SERVER')}
                variant="outlined"
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Port"
                value={settings.POSTGRES_PORT}
                onChange={handleChange('POSTGRES_PORT')}
                variant="outlined"
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Database Name"
                value={settings.POSTGRES_DB}
                onChange={handleChange('POSTGRES_DB')}
                variant="outlined"
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Username"
                value={settings.POSTGRES_USER}
                onChange={handleChange('POSTGRES_USER')}
                variant="outlined"
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Password"
                value={settings.POSTGRES_PASSWORD}
                onChange={handleChange('POSTGRES_PASSWORD')}
                variant="outlined"
                type={showSecrets.POSTGRES_PASSWORD ? 'text' : 'password'}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={() => toggleSecretVisibility('POSTGRES_PASSWORD')} edge="end">
                        {showSecrets.POSTGRES_PASSWORD ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>
          </Grid>
        </TabPanel>

        {/* Logging Tab */}
        <TabPanel value={tabValue} index={5}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Logging Configuration</Typography>
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Log Directory"
                value={settings.LOG_DIR}
                onChange={handleChange('LOG_DIR')}
                variant="outlined"
                helperText="Directory where log files are stored"
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Bot Engine Log File"
                value={settings.BOT_ENGINE_LOG_FILE}
                onChange={handleChange('BOT_ENGINE_LOG_FILE')}
                variant="outlined"
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="API Server Log File"
                value={settings.API_SERVER_LOG_FILE}
                onChange={handleChange('API_SERVER_LOG_FILE')}
                variant="outlined"
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Max Log File Size (MB)"
                value={settings.MAX_LOG_FILE_SIZE_MB}
                onChange={handleChange('MAX_LOG_FILE_SIZE_MB')}
                variant="outlined"
                InputProps={{ inputProps: { min: 1 } }}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Log File Backup Count"
                value={settings.LOG_FILE_BACKUP_COUNT}
                onChange={handleChange('LOG_FILE_BACKUP_COUNT')}
                variant="outlined"
                InputProps={{ inputProps: { min: 0 } }}
              />
            </Grid>
          </Grid>
        </TabPanel>

        {/* System Tab */}
        <TabPanel value={tabValue} index={6}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>System Configuration</Typography>
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Project Name"
                value={settings.PROJECT_NAME}
                onChange={handleChange('PROJECT_NAME')}
                variant="outlined"
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Version"
                value={settings.VERSION}
                onChange={handleChange('VERSION')}
                variant="outlined"
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <FormControl fullWidth variant="outlined">
                <InputLabel>App Startup Mode</InputLabel>
                <Autocomplete
                  options={['lite', 'full']}
                  value={settings.APP_STARTUP_MODE}
                  onChange={(_, value) => {
                    if (value) {
                      setSettings(prev => ({ ...prev!, APP_STARTUP_MODE: value }));
                      setSuccessMessage(null);
                    }
                  }}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      variant="outlined"
                      label="App Startup Mode"
                    />
                  )}
                />
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.DEBUG}
                    onChange={handleSwitchChange('DEBUG')}
                  />
                }
                label="Debug Mode"
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.SKIP_DB_INIT}
                    onChange={handleSwitchChange('SKIP_DB_INIT')}
                  />
                }
                label="Skip Database Initialization"
              />
            </Grid>
          </Grid>
        </TabPanel>
        
        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
          <Button 
            variant="contained" 
            color="primary" 
            onClick={handleSave}
            disabled={saving || !hasChanges}
          >
            {saving ? <CircularProgress size={24} color="inherit" /> : "Save Settings"}
          </Button>
        </Box>
      </Paper>

      {/* Reset Confirmation Dialog */}
      <Dialog open={resetDialogOpen} onClose={() => setResetDialogOpen(false)}>
        <DialogTitle>Reset Settings to Defaults</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to reset all settings to their default values? 
            This action cannot be undone and will remove any custom configuration.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetDialogOpen(false)}>Cancel</Button>
          <Button 
            onClick={handleReset} 
            color="warning" 
            disabled={resetting}
            autoFocus
          >
            {resetting ? <CircularProgress size={24} /> : "Reset Settings"}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default SettingsPage;
