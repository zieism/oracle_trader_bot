# Routes and API Inventory (Baseline)

## Frontend Routes
| Path | File | Line |
|------|------|------|
| `/` | App.tsx | 143 |
| `/analysis-logs` | App.tsx | 149 |
| `/server-logs` | App.tsx | 147 |
| `/settings` | App.tsx | 144 |
| `/trades` | App.tsx | 145 |

**Total Frontend Routes:** 5

## Backend API Endpoints
| Method | Path | Router File | Line |
|--------|------|-------------|------|
| DELETE | `/api/v1/db/trades/{trade_id}` | trades.py | 79 |
| DELETE | `/api/v1/orders/cancel/{symbol}/{order_id}` | order_management.py | 66 |
| GET | `/api/ui/` | frontend_fastui.py | 30 |
| GET | `/api/v1/bot-management/status` | bot_management_api.py | 23 |
| GET | `/api/v1/bot-settings/` | bot_settings_api.py | 13 |
| GET | `/api/v1/db/trades/` | trades.py | 26 |
| GET | `/api/v1/db/trades/total-count` | trades.py | 39 |
| GET | `/api/v1/db/trades/{trade_id}` | trades.py | 50 |
| GET | `/api/v1/exchange/health` | exchange_info.py | 11 |
| GET | `/api/v1/exchange/kucoin/account-overview` | exchange_info.py | 128 |
| GET | `/api/v1/exchange/kucoin/contracts` | exchange_info.py | 107 |
| GET | `/api/v1/exchange/kucoin/time` | exchange_info.py | 79 |
| GET | `/api/v1/exchange/symbols` | exchange_info.py | 52 |
| GET | `/api/v1/logs/server-logs` | server_logs_api.py | 31 |
| GET | `/api/v1/market/ohlcv-with-indicators/{symbol}` | market_data.py | 58 |
| GET | `/api/v1/market/ohlcv/{symbol}` | market_data.py | 19 |
| GET | `/api/v1/orders/positions` | order_management.py | 108 |
| GET | `/api/v1/orders/status/{symbol}/{order_id}` | order_management.py | 31 |
| GET | `/api/v1/signals/generate-signal/{symbol}` | strategy_signals.py | 22 |
| POST | `/api/v1/analysis-logs/internal-publish` | analysis_logs_websocket.py | 75 |
| POST | `/api/v1/bot-management/start` | bot_management_api.py | 9 |
| POST | `/api/v1/bot-management/stop` | bot_management_api.py | 16 |
| POST | `/api/v1/db/trades/` | trades.py | 13 |
| POST | `/api/v1/orders/positions/close` | order_management.py | 250 |
| POST | `/api/v1/orders/positions/set-sl-tp` | order_management.py | 232 |
| POST | `/api/v1/trading/execute-signal` | trading.py | 23 |
| PUT | `/api/v1/bot-settings/` | bot_settings_api.py | 35 |
| PUT | `/api/v1/db/trades/{trade_id}` | trades.py | 63 |

**Total Backend Endpoints:** 28

## Frontend API Calls
| Method | URL/Path | Type | File | Line |
|--------|----------|------|------|------|
| GET | `/bot-management/status` | apiClient | apiService.ts | 294 |
| GET | `/bot-settings/` | apiClient | apiService.ts | 104 |
| GET | `/db/trades/?skip=${skip}&limit=${limit}` | apiClient | apiService.ts | 145 |
| GET | `/db/trades/total-count` | apiClient | apiService.ts | 157 |
| GET | `/exchange/health` | apiClient | apiService.ts | 258 |
| GET | `/exchange/kucoin/account-overview` | apiClient | apiService.ts | 46 |
| GET | `/exchange/kucoin/contracts` | apiClient | apiService.ts | 236 |
| GET | `/exchange/symbols` | apiClient | apiService.ts | 274 |
| POST | `/bot-management/start` | apiClient | apiService.ts | 305 |
| POST | `/bot-management/stop` | apiClient | apiService.ts | 316 |
| POST | `/orders/positions/close` | apiClient | apiService.ts | 221 |
| PUT | `/bot-settings/` | apiClient | apiService.ts | 116 |

**Total API Calls:** 12

## Integration Analysis

### URL Matching (Frontend → Backend)
- **Matched calls:** 0/12
- **Unmatched calls:** 12

### Potentially Unmatched API Calls
- `GET /exchange/kucoin/account-overview` in apiService.ts:46
- `GET /bot-settings/` in apiService.ts:104
- `PUT /bot-settings/` in apiService.ts:116
- `GET /db/trades/?skip=${skip}&limit=${limit}` in apiService.ts:145
- `GET /db/trades/total-count` in apiService.ts:157
- `POST /orders/positions/close` in apiService.ts:221
- `GET /exchange/kucoin/contracts` in apiService.ts:236
- `GET /exchange/health` in apiService.ts:258
- `GET /exchange/symbols` in apiService.ts:274
- `GET /bot-management/status` in apiService.ts:294
