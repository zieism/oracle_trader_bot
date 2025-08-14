// src/services/apiClient.ts - Centralized API Client
import axios, { AxiosInstance } from 'axios';

// ==================== CONFIGURATION ====================
// All URLs are centralized here and come from environment variables

const CONFIG = {
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  WS_BASE_URL: import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/api/v1',
  REQUEST_TIMEOUT: 10000,
} as const;

// ==================== API CLIENT SETUP ====================

// Create axios instance with common configuration
const apiClient: AxiosInstance = axios.create({
  baseURL: CONFIG.API_BASE_URL,
  timeout: CONFIG.REQUEST_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ==================== TYPES ====================

export interface AccountBalanceDetail {
  currency: string; 
  free: number | null;
  used: number | null;
  total: number | null;
}

export interface AccountOverviewApiResponse {
  USDT?: { 
    free: number;
    used: number;
    total: number;
  };
  info?: any; 
}

export const getAccountOverview = async (): Promise<AccountBalanceDetail | null> => {
  try {
    console.log(`apiClient: Fetching account overview from ${CONFIG.API_BASE_URL}/exchange/kucoin/account-overview`);
    const response = await apiClient.get<AccountOverviewApiResponse>(`/exchange/kucoin/account-overview`);
    console.log("apiService: Raw response from /account-overview:", response);
    
    if (response.data && response.data.USDT) {
      console.log("apiService: Fetched USDT Balance from response.data.USDT:", response.data.USDT);
      return { 
        currency: 'USDT', 
        free: response.data.USDT.free,
        used: response.data.USDT.used,
        total: response.data.USDT.total,
      };
    }
    if (response.data && response.data.info && response.data.info.data && response.data.info.data.currency === 'USDT') {
        const accData = response.data.info.data;
        console.log("apiService: Fetched USDT Balance from response.data.info.data:", accData);
        return {
            currency: 'USDT',
            free: accData.availableBalance,
            used: accData.orderMargin, 
            total: accData.accountEquity,
        };
    }
    console.warn('apiService: USDT balance details not found in expected structures in account overview response:', response.data);
    return null;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      console.error('apiService: Axios error fetching account overview:', error.response?.status, error.response?.data || error.message);
    } else {
      console.error('apiService: Unexpected error fetching account overview:', error);
    }
    throw error; 
  }
};

export interface BotSettingsData {
    id: number; 
    symbols_to_trade: string[]; 
    max_concurrent_trades: number;
    trade_amount_mode: string; 
    fixed_trade_amount_usd: number;
    percentage_trade_amount: number;
    daily_loss_limit_percentage?: number | null;
    // Extended settings for comprehensive bot configuration
    kucoin_api_key?: string;
    kucoin_api_secret?: string;
    kucoin_api_passphrase?: string;
    kucoin_sandbox_mode?: boolean;
    leverage?: number;
    risk_per_trade?: number;
    atr_based_tp_enabled?: boolean;
    atr_based_sl_enabled?: boolean;
    timeframes?: string[];
    updated_at?: string; 
}

export const getBotSettings = async (): Promise<BotSettingsData | null> => {
    try {
        console.log(`apiService: Fetching bot settings from /bot-settings/`);
        const response = await apiClient.get<BotSettingsData>(`/bot-settings/`);
        console.log("apiService: Fetched Bot Settings:", response.data);
        return response.data;
    } catch (error) {
        console.error('apiService: Error fetching bot settings:', error);
        throw error;
    }
};

export const updateBotSettings = async (settingsData: Partial<BotSettingsData>): Promise<BotSettingsData | null> => {
    try {
        console.log(`apiService: Updating bot settings at /bot-settings/ with payload:`, settingsData);
        const response = await apiClient.put<BotSettingsData>(`/bot-settings/`, settingsData);
        console.log("apiService: Updated Bot Settings:", response.data);
        return response.data;
    } catch (error) {
        console.error('apiService: Error updating bot settings:', error);
        throw error;
    }
};

export interface TradeData {
    id: number;
    symbol: string;
    direction: string; 
    entry_price?: number | null;
    exit_price?: number | null;
    quantity?: number | null;
    status: string; 
    pnl?: number | null;
    pnl_percentage?: number | null;
    timestamp_opened?: string | null; 
    timestamp_closed?: string | null; 
    strategy_name?: string | null;
    entry_order_id?: string | null;
    exit_reason?: string | null; // ADDED: exit_reason field
}

export const getTradesHistory = async (skip: number = 0, limit: number = 5): Promise<TradeData[]> => {
    try {
        console.log(`apiService: Fetching trades history from /db/trades/?skip=${skip}&limit=${limit}`);
        const response = await apiClient.get<TradeData[]>(`/db/trades/?skip=${skip}&limit=${limit}`);
        console.log(`apiService: Fetched Trades History (skip: ${skip}, limit: ${limit}):`, response.data);
        return response.data || []; 
    } catch (error) {
        console.error('apiService: Error fetching trades history:', error);
        throw error;
    }
};

export const getTotalTradesCount = async (): Promise<number> => {
  try {
    console.log(`apiService: Fetching total trades count from /db/trades/total-count`);
    const response = await apiClient.get<number>(`/db/trades/total-count`);
    console.log("apiService: Fetched Total Trades Count:", response.data);
    return response.data || 0;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      console.error('apiService: Error fetching total trades count:', error.response?.status, error.response?.data || error.message);
    } else {
      console.error('apiService: Unexpected error fetching total trades count:', error);
    }
    throw error;
  }
};

export interface OpenPositionData {
  id?: string; 
  symbol: string;
  side: 'long' | 'short';
  contracts: number | null; 
  contractSize?: number | null;
  entryPrice: number | null;
  markPrice?: number | null;
  notional?: number | null; 
  leverage: number | null; 
  unrealizedPnl: number | null;
  initialMargin?: number | null; 
  maintenanceMargin?: number | null;
  liquidationPrice?: number | null;
  marginMode?: 'isolated' | 'cross' | string; 
  timestamp?: number; 
  datetime?: string; 
  stopLossPrice?: number | null; 
  takeProfitPrice?: number | null; 
  info?: any; 
}

export const getOpenPositions = async (symbol?: string): Promise<OpenPositionData[]> => {
  try {
    let url = `/orders/positions`;
    if (symbol) {
      url += `?symbol=${encodeURIComponent(symbol)}`;
    }
    const response = await apiClient.get<OpenPositionData[]>(url);
    console.log(`apiService: Fetched Open Positions (symbol: ${symbol || 'All'}):`, response.data);
    return response.data || [];
  } catch (error) {
    console.error('apiService: Error fetching open positions:', error);
    throw error;
  }
};

export interface ClosePositionPayload {
  symbol: string; 
}

export interface ClosePositionResponse {
  status: string;
  message: string;
  closing_order_details?: any; 
  db_error?: string;
}

export const closePosition = async (payload: ClosePositionPayload): Promise<ClosePositionResponse> => {
  try {
    console.log(`apiService: Attempting to close position for symbol: ${payload.symbol}`);
    const response = await apiClient.post<ClosePositionResponse>(`/orders/positions/close`, payload);
    console.log(`apiService: Close position response for ${payload.symbol}:`, response.data);
    return response.data;
  } catch (error) {
    console.error('apiService: Error closing position:', error);
    throw error;
  }
};

export interface ExchangeContract {
    symbol: string;
}

export const getAvailableSymbols = async (): Promise<string[]> => {
    try {
        const response = await apiClient.get<ExchangeContract[]>(`/exchange/kucoin/contracts`);
        return response.data.map((contract: ExchangeContract) => contract.symbol);
    } catch (error) {
        console.error('apiService: Error fetching available symbols:', error);
        throw error;
    }
};

// ===============================================
// EXCHANGE HEALTH CHECK & ADDITIONAL ENDPOINTS
// ===============================================

export interface ExchangeHealthResponse {
  status: string;
  message: string;
  server_time_ms?: number;
  local_time_ms?: number;
  time_difference_ms?: number;
}

export const getExchangeHealth = async (): Promise<ExchangeHealthResponse> => {
  try {
    const response = await apiClient.get<ExchangeHealthResponse>(`/exchange/health`);
    console.log("apiService: Fetched Exchange Health:", response.data);
    return response.data;
  } catch (error) {
    console.error('apiService: Error fetching exchange health:', error);
    throw error;
  }
};

export interface ExchangeSymbolsResponse {
  symbols: string[];
  count: number;
}

export const getExchangeSymbols = async (): Promise<ExchangeSymbolsResponse> => {
  try {
    const response = await apiClient.get<ExchangeSymbolsResponse>(`/exchange/symbols`);
    console.log("apiService: Fetched Exchange Symbols:", response.data);
    return response.data;
  } catch (error) {
    console.error('apiService: Error fetching exchange symbols:', error);
    throw error;
  }
};

// ===============================================
// BOT MANAGEMENT API FUNCTIONS
// ===============================================

export interface BotStatusResponse {
  status: 'running' | 'stopped' | 'stopped_stale_pid' | string;
  pid: string | null;
}

export const getBotStatus = async (): Promise<BotStatusResponse> => {
  try {
    const response = await apiClient.get<BotStatusResponse>(`/bot-management/status`);
    console.log("apiService: Fetched Bot Status:", response.data);
    return response.data;
  } catch (error) {
    console.error('apiService: Error fetching bot status:', error);
    throw error;
  }
};

export const startBot = async (): Promise<{ status: string; message: string }> => {
  try {
    const response = await apiClient.post<{ status: string; message: string }>(`/bot-management/start`);
    console.log("apiService: Start bot response:", response.data);
    return response.data;
  } catch (error) {
    console.error('apiService: Error starting bot:', error);
    throw error;
  }
};

export const stopBot = async (): Promise<{ status: string; message: string }> => {
  try {
    const response = await apiClient.post<{ status: string; message: string }>(`/bot-management/stop`);
    console.log("apiService: Stop bot response:", response.data);
    return response.data;
  } catch (error) {
    console.error('apiService: Error stopping bot:', error);
    throw error;
  }
};

// ===============================================
// SERVER LOGS API FUNCTIONS
// ===============================================

export interface LogEntry {
  timestamp: string;
  level: string;
  name: string;
  message: string;
}

export const getServerLogs = async (
  logType: 'api' | 'bot' | 'all' = 'all',
  limit: number = 200,
  tail: boolean = true,
  level?: string,
  search?: string
): Promise<LogEntry[]> => {
  try {
    const params = new URLSearchParams();
    params.append('log_type', logType);
    params.append('limit', String(limit));
    params.append('tail', String(tail));
    if (level) {
      params.append('level', level);
    }
    if (search) {
      params.append('search', search);
    }

    const url = `/logs/server-logs?${params.toString()}`;
    console.log(`apiService: Fetching server logs from ${url}`);
    const response = await apiClient.get<LogEntry[]>(url);
    console.log("apiService: Fetched Server Logs:", response.data);
    return response.data;
  } catch (error) {
    console.error('apiService: Error fetching server logs:', error);
    throw error;
  }
};

// ===============================================
// ANALYSIS LOGS WEBSOCKET FUNCTIONS
// ===============================================

export interface AnalysisLogEntry {
  timestamp: string;
  level: string; // e.g., "INFO", "WARNING", "ERROR", "CRITICAL", "SUCCESS" (custom)
  symbol: string; // e.g., "BTC/USDT:USDT", "N/A"
  strategy: string; // e.g., "TrendFollowing", "MarketRegime", "N/A"
  message: string;
  decision: string; // e.g., "ANALYZE_START", "SIGNAL_GENERATED", "ORDER_PLACED", "SKIPPED_MAX_TRADES"
  details?: Record<string, any>; // For any additional JSON details
}

// Function to establish and manage the WebSocket connection
export const setupAnalysisLogWebSocket = (
  onMessage: (logEntry: AnalysisLogEntry) => void,
  onError: (event: Event) => void,
  onClose: (event: CloseEvent) => void,
  onOpen?: (event: Event) => void
): WebSocket => {
  const ws = new WebSocket(`${CONFIG.WS_BASE_URL}/ws/analysis-logs`);

  ws.onopen = (event) => {
    console.log('WebSocket connection for analysis logs opened.', event);
    onOpen && onOpen(event);
  };

  ws.onmessage = (event) => {
    try {
      const data: AnalysisLogEntry = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error('Error parsing WebSocket message:', e, event.data);
    }
  };

  ws.onerror = (event) => {
    console.error('WebSocket error for analysis logs:', event);
    onError(event);
  };

  ws.onclose = (event) => {
    console.log('WebSocket connection for analysis logs closed:', event);
    onClose(event);
  };

  return ws;
};
