// src/pages/BotSettingsPage.tsx
import React, { useEffect, useState, useCallback } from 'react';
import { 
  getBotSettings, 
  updateBotSettings, 
  BotSettingsData,
  getAvailableSymbols 
} from '../services/apiService';
import {
  Container, Typography, Paper, Grid, TextField, Button, CircularProgress,
  Alert, Select, MenuItem, FormControl, InputLabel, Box, Autocomplete, Chip, Divider
} from '@mui/material';

enum TradeAmountModeFE {
  FIXED_USD = "FIXED_USD",
  PERCENTAGE_BALANCE = "PERCENTAGE_BALANCE"
}

const BotSettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<Partial<BotSettingsData>>({ symbols_to_trade: [] });
  const [initialSettings, setInitialSettings] = useState<BotSettingsData | null>(null);
  
  const [allSymbols, setAllSymbols] = useState<string[]>([]);
  const [loadingSymbols, setLoadingSymbols] = useState<boolean>(true);

  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

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

  const handleChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement> | SelectChangeEvent<string>) => {
    const { name, value } = event.target;
    let processedValue: string | number = value;
    if (['max_concurrent_trades', 'fixed_trade_amount_usd', 'percentage_trade_amount', 'daily_loss_limit_percentage'].includes(name)) {
      processedValue = value === '' ? '' : Number(value);
    }
    setSettings(prev => ({ ...prev, [name]: processedValue }));
    setSuccessMessage(null);
  };

  const handleSymbolsChange = (event: React.SyntheticEvent, value: string[]) => {
    setSettings(prev => ({
      ...prev,
      symbols_to_trade: value
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
    <Container maxWidth="md" sx={{ mt: 2, mb: 4 }}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" component="h1" gutterBottom color="primary">
          Bot Settings
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        {successMessage && <Alert severity="success" sx={{ mb: 2 }}>{successMessage}</Alert>}

        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Typography variant="h6" gutterBottom>Market Selection</Typography>
            <Autocomplete
              multiple
              id="symbols-to-trade-select"
              options={allSymbols.sort()}
              getOptionLabel={(option) => option}
              value={settings.symbols_to_trade || []}
              onChange={handleSymbolsChange}
              loading={loadingSymbols}
              renderInput={(params) => (
                <TextField
                  {...params}
                  variant="outlined"
                  label="Symbols to Trade"
                  placeholder="Search and select symbols..."
                  InputProps={{
                    ...params.InputProps,
                    endAdornment: (
                      <React.Fragment>
                        {loadingSymbols ? <CircularProgress color="inherit" size={20} /> : null}
                        {params.InputProps.endAdornment}
                      </React.Fragment>
                    ),
                  }}
                />
              )}
              renderTags={(value: readonly string[], getTagProps) =>
                value.map((option: string, index: number) => (
                  <Chip variant="outlined" label={option} {...getTagProps({ index })} />
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
              <InputLabel id="trade-amount-mode-label">Trade Amount Mode</InputLabel>
              <Select
                labelId="trade-amount-mode-label"
                id="trade_amount_mode"
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