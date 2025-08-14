// src/pages/BotSettingsPage.tsx
import React, { useEffect, useState, useCallback } from 'react';
import { 
  getBotSettings, 
  updateBotSettings, 
  BotSettingsData,
  getAvailableSymbols 
} from '@services/apiClient';
import {
  Container, Typography, Paper, Grid, TextField, Button, CircularProgress,
  Alert, Select, MenuItem, FormControl, InputLabel, Box, Autocomplete, Chip, 
  Divider, Switch, FormControlLabel, Tabs, Tab
} from '@mui/material';

enum TradeAmountModeFE {
  FIXED_USD = "FIXED_USD",
  PERCENTAGE_BALANCE = "PERCENTAGE_BALANCE"
}

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

const BotSettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<Partial<BotSettingsData>>({ 
    symbols_to_trade: [],
    timeframes: [] 
  });
  const [initialSettings, setInitialSettings] = useState<BotSettingsData | null>(null);
  const [tabValue, setTabValue] = useState(0);
  
  const [allSymbols, setAllSymbols] = useState<string[]>([]);
  const [loadingSymbols, setLoadingSymbols] = useState<boolean>(true);

  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const availableTimeframes = ['1m', '5m', '15m', '1h', '4h', '1d', '1w'];

  const fetchData = useCallback(async () => {
    setLoading(true);
    setLoadingSymbols(true);
    setError(null);
    try {
      const [settingsData, symbolsData] = await Promise.all([
        getBotSettings(),
        getAvailableSymbols()
      ]);

      if (settingsData) {
        setSettings(settingsData);
        setInitialSettings(settingsData);
      } else {
        setError("Could not load bot settings.");
      }
      
      if (symbolsData) {
        setAllSymbols(symbolsData);
      } else {
        setError(prev => prev ? `${prev} Could not load symbol list.` : "Could not load symbol list.");
      }

    } catch (err) {
      setError("Failed to fetch data from the server.");
      console.error(err);
    } finally {
      setLoading(false);
      setLoadingSymbols(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement> | any) => {
    const { name, value } = event.target;
    let processedValue: string | number = value;
    if (['max_concurrent_trades', 'fixed_trade_amount_usd', 'percentage_trade_amount', 'daily_loss_limit_percentage', 'leverage', 'risk_per_trade'].includes(name)) {
      processedValue = value === '' ? '' : Number(value);
    }
    setSettings((prev: any) => ({ ...prev, [name]: processedValue }));
    setSuccessMessage(null);
  };

  const handleSwitchChange = (name: string) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setSettings((prev: any) => ({ ...prev, [name]: event.target.checked }));
    setSuccessMessage(null);
  };

  const handleSymbolsChange = (_event: React.SyntheticEvent, value: string[]) => {
    setSettings((prev: any) => ({
      ...prev,
      symbols_to_trade: value
    }));
    setSuccessMessage(null);
  };

  const handleTimeframesChange = (_event: React.SyntheticEvent, value: string[]) => {
    setSettings((prev: any) => ({
      ...prev,
      timeframes: value
    }));
    setSuccessMessage(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const settingsToUpdate: Partial<BotSettingsData> = {
        ...settings,
        max_concurrent_trades: Number(settings.max_concurrent_trades),
        fixed_trade_amount_usd: Number(settings.fixed_trade_amount_usd),
        percentage_trade_amount: Number(settings.percentage_trade_amount),
        daily_loss_limit_percentage: settings.daily_loss_limit_percentage ? Number(settings.daily_loss_limit_percentage) : null,
        leverage: settings.leverage ? Number(settings.leverage) : undefined,
        risk_per_trade: settings.risk_per_trade ? Number(settings.risk_per_trade) : undefined,
      };

      const updatedSettings = await updateBotSettings(settingsToUpdate);
      if (updatedSettings) {
        setSettings(updatedSettings);
        setInitialSettings(updatedSettings);
        setSuccessMessage("Settings updated successfully!");
      } else {
        setError("Failed to save settings. Please try again.");
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || "An error occurred while saving settings.";
      setError(errorMessage);
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Container sx={{ display: 'flex', justifyContent: 'center', mt: 5 }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 2, mb: 4 }}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" component="h1" gutterBottom color="primary">
          Bot Settings
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        {successMessage && <Alert severity="success" sx={{ mb: 2 }}>{successMessage}</Alert>}

        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
            <Tab label="Trading" />
            <Tab label="KuCoin API" />
            <Tab label="Risk Management" />
          </Tabs>
        </Box>

        {/* Trading Configuration Tab */}
        <TabPanel value={tabValue} index={0}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Market Selection</Typography>
              <Autocomplete
                multiple
                options={allSymbols.sort()}
                getOptionLabel={(option: any) => option}
                value={settings.symbols_to_trade || []}
                onChange={handleSymbolsChange}
                loading={loadingSymbols}
                renderInput={(params: any) => (
                  <TextField
                    {...params}
                    variant="outlined"
                    label="Symbols to Trade"
                    placeholder="Search and select symbols..."
                    InputProps={{
                      ...params.InputProps,
                      endAdornment: (
                        <>
                          {loadingSymbols ? <CircularProgress color="inherit" size={20} /> : null}
                          {params.InputProps.endAdornment}
                        </>
                      ),
                    }}
                  />
                )}
                renderTags={(value: readonly string[], getTagProps: any) =>
                  value.map((option: string, index: number) => (
                    <Chip variant="outlined" label={option} {...getTagProps({ index })} key={index} />
                  ))
                }
              />
            </Grid>

            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Timeframes</Typography>
              <Autocomplete
                multiple
                options={availableTimeframes}
                getOptionLabel={(option: any) => option}
                value={settings.timeframes || []}
                onChange={handleTimeframesChange}
                renderInput={(params: any) => (
                  <TextField
                    {...params}
                    variant="outlined"
                    label="Trading Timeframes"
                    placeholder="Select timeframes..."
                  />
                )}
                renderTags={(value: readonly string[], getTagProps: any) =>
                  value.map((option: string, index: number) => (
                    <Chip variant="outlined" label={option} {...getTagProps({ index })} key={index} />
                  ))
                }
              />
            </Grid>
            
            <Grid item xs={12}>
              <Divider sx={{ my: 1 }} />
            </Grid>

            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Trading Rules</Typography>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Max Concurrent Trades"
                name="max_concurrent_trades"
                value={settings.max_concurrent_trades ?? ''}
                onChange={handleChange}
                variant="outlined"
                InputProps={{ inputProps: { min: 0 } }}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControl fullWidth variant="outlined">
                <InputLabel>Trade Amount Mode</InputLabel>
                <Select
                  name="trade_amount_mode"
                  value={settings.trade_amount_mode ?? ''}
                  onChange={handleChange}
                  label="Trade Amount Mode"
                >
                  <MenuItem value={TradeAmountModeFE.FIXED_USD}>Fixed USD Amount</MenuItem>
                  <MenuItem value={TradeAmountModeFE.PERCENTAGE_BALANCE}>Percentage of Balance</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            {settings.trade_amount_mode === TradeAmountModeFE.FIXED_USD && (
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Fixed Trade Amount (USD)"
                  name="fixed_trade_amount_usd"
                  value={settings.fixed_trade_amount_usd ?? ''}
                  onChange={handleChange}
                  variant="outlined"
                  InputProps={{ inputProps: { min: 0.01, step: "0.01" } }}
                />
              </Grid>
            )}

            {settings.trade_amount_mode === TradeAmountModeFE.PERCENTAGE_BALANCE && (
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Percentage of Balance (%)"
                  name="percentage_trade_amount"
                  value={settings.percentage_trade_amount ?? ''}
                  onChange={handleChange}
                  variant="outlined"
                  InputProps={{ inputProps: { min: 0.01, max: 100, step: "0.01" } }}
                />
              </Grid>
            )}

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Daily Loss Limit (%) (Optional)"
                name="daily_loss_limit_percentage"
                value={settings.daily_loss_limit_percentage ?? ''}
                onChange={handleChange}
                variant="outlined"
                helperText="Leave blank to disable"
                InputProps={{ inputProps: { min: 0.01, max: 100, step: "0.01" } }}
              />
            </Grid>
          </Grid>
        </TabPanel>

        {/* KuCoin API Configuration Tab */}
        <TabPanel value={tabValue} index={1}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>KuCoin API Credentials</Typography>
              <Alert severity="warning" sx={{ mb: 2 }}>
                API credentials are stored securely. Never share these values.
              </Alert>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="API Key"
                name="kucoin_api_key"
                value={settings.kucoin_api_key ?? ''}
                onChange={handleChange}
                variant="outlined"
                type="password"
                helperText="Your KuCoin API Key"
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="API Secret"
                name="kucoin_api_secret"
                value={settings.kucoin_api_secret ?? ''}
                onChange={handleChange}
                variant="outlined"
                type="password"
                helperText="Your KuCoin API Secret"
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="API Passphrase"
                name="kucoin_api_passphrase"
                value={settings.kucoin_api_passphrase ?? ''}
                onChange={handleChange}
                variant="outlined"
                type="password"
                helperText="Your KuCoin API Passphrase"
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.kucoin_sandbox_mode ?? true}
                    onChange={handleSwitchChange('kucoin_sandbox_mode')}
                  />
                }
                label="Sandbox Mode (Test Environment)"
              />
            </Grid>
          </Grid>
        </TabPanel>

        {/* Risk Management Tab */}
        <TabPanel value={tabValue} index={2}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Risk Management Settings</Typography>
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Leverage"
                name="leverage"
                value={settings.leverage ?? ''}
                onChange={handleChange}
                variant="outlined"
                InputProps={{ inputProps: { min: 1, max: 100 } }}
                helperText="Trading leverage (1-100x)"
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Risk Per Trade (%)"
                name="risk_per_trade"
                value={settings.risk_per_trade ?? ''}
                onChange={handleChange}
                variant="outlined"
                InputProps={{ inputProps: { min: 0.1, max: 10, step: "0.1" } }}
                helperText="Percentage of balance to risk per trade"
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <Box sx={{ mt: 2 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.atr_based_tp_enabled ?? true}
                      onChange={handleSwitchChange('atr_based_tp_enabled')}
                    />
                  }
                  label="ATR-based Take Profit"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.atr_based_sl_enabled ?? true}
                      onChange={handleSwitchChange('atr_based_sl_enabled')}
                    />
                  }
                  label="ATR-based Stop Loss"
                />
              </Box>
            </Grid>
          </Grid>
        </TabPanel>
        
        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button 
            variant="contained" 
            color="primary" 
            onClick={handleSave}
            disabled={saving || JSON.stringify(settings) === JSON.stringify(initialSettings)}
          >
            {saving ? <CircularProgress size={24} color="inherit" /> : "Save Settings"}
          </Button>
        </Box>
      </Paper>
    </Container>
  );
};

export default BotSettingsPage;