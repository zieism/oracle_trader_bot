# Repository X-Ray Report

## Backend (from code)

- FastAPI apps: 1
  - app var `app` in `D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\main.py`
- Routers detected: 18
- Endpoints detected: 0


### Data Models (Pydantic/SQLAlchemy guess)

- `AnalysisLogEntry@D:\GITHUB\oracle_trader_bot\backend\app\api\routers\analysis.py` bases: BaseModel
- `Settings@D:\GITHUB\oracle_trader_bot\backend\app\core\config.py` bases: BaseSettings
- `AnalysisLogEntry@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\api\endpoints\analysis_logs_websocket.py` bases: BaseModel
- `AccountBalance@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\api\endpoints\frontend_fastui.py` bases: BaseModel
- `DashboardData@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\api\endpoints\frontend_fastui.py` bases: BaseModel
- `HealthResponse@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\api\endpoints\health.py` bases: BaseModel
- `SetSLTPPayload@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\api\endpoints\order_management.py` bases: BaseModel
- `ClosePositionPayload@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\api\endpoints\order_management.py` bases: BaseModel
- `Settings@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\core\config.py` bases: BaseSettings
- `BotSettings@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\models\bot_settings.py` bases: Base
- `Trade@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\models\trade.py` bases: Base
- `BotSettingsBase@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\schemas\bot_settings.py` bases: BaseModel
- `BotSettingsCreate@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\schemas\bot_settings.py` bases: BotSettingsBase
- `BotSettingsUpdate@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\schemas\bot_settings.py` bases: BaseModel
- `BotSettings@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\schemas\bot_settings.py` bases: BotSettingsBase
- `OHLCVWithIndicatorsAndRegime@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\schemas\market_analysis.py` bases: BaseModel
- `MarketRegimeInfo@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\schemas\market_regime_schemas.py` bases: BaseModel
- `OHLCVWithIndicatorsAndRegimeResponse@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\schemas\market_regime_schemas.py` bases: BaseModel
- `TradeBase@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\schemas\trade.py` bases: BaseModel
- `TradeCreate@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\schemas\trade.py` bases: TradeBase
- `TradeUpdate@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\schemas\trade.py` bases: BaseModel
- `Trade@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\schemas\trade.py` bases: TradeBase
- `TradingSignal@D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\schemas\trading_signal.py` bases: BaseModel

### KuCoin/ccxt usage (files)

- D:\GITHUB\oracle_trader_bot\repo_xray.py
- D:\GITHUB\oracle_trader_bot\backend\app\api\routers\analysis.py
- D:\GITHUB\oracle_trader_bot\backend\app\api\routers\exchange.py
- D:\GITHUB\oracle_trader_bot\backend\app\api\routers\trading.py
- D:\GITHUB\oracle_trader_bot\backend\app\core\config.py
- D:\GITHUB\oracle_trader_bot\backend\app\exchange_clients\__init__.py
- D:\GITHUB\oracle_trader_bot\backend\app\services\kucoin_futures_client.py
- D:\GITHUB\oracle_trader_bot\backend\app\services\position_monitor.py
- D:\GITHUB\oracle_trader_bot\backend\app\services\__init__.py
- D:\GITHUB\oracle_trader_bot\oracle_trader_bot\bot_engine.py
- D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\main.py
- D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\api\dependencies.py
- D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\api\endpoints\exchange_info.py
- D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\api\endpoints\frontend_fastui.py
- D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\api\endpoints\health.py
- D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\api\endpoints\market_data.py
- D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\api\endpoints\order_management.py
- D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\api\endpoints\strategy_signals.py
- D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\api\endpoints\trading.py
- D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\core\config.py
- D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\crud\crud_bot_settings.py
- D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\exchange_clients\kucoin_futures_client.py
- D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\models\bot_settings.py
- D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\schemas\bot_settings.py
- D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\services\kucoin_futures_client.py
- D:\GITHUB\oracle_trader_bot\oracle_trader_bot\app\services\position_monitor.py
- D:\GITHUB\oracle_trader_bot\scripts\rewrite_backend_imports.py
- D:\GITHUB\oracle_trader_bot\scripts\rewrite_phase2_imports.py
- D:\GITHUB\oracle_trader_bot\tests\test_exchange_client_no_auth.py
- D:\GITHUB\oracle_trader_bot\tests\test_health_endpoints_no_auth.py
- D:\GITHUB\oracle_trader_bot\tests\test_trading_endpoint_no_auth.py

## Frontend (from code)

- Routes detected: 5
  - `/` (D:\GITHUB\oracle_trader_bot\oracle-trader-frontend\src\App.tsx)
  - `/settings` (D:\GITHUB\oracle_trader_bot\oracle-trader-frontend\src\App.tsx)
  - `/trades` (D:\GITHUB\oracle_trader_bot\oracle-trader-frontend\src\App.tsx)
  - `/server-logs` (D:\GITHUB\oracle_trader_bot\oracle-trader-frontend\src\App.tsx)
  - `/analysis-logs` (D:\GITHUB\oracle_trader_bot\oracle-trader-frontend\src\App.tsx)
- API calls detected: 0

## Integration Map (FE → BE)


## Likely Gaps & Fix-First List (heuristic)

- Ensure the frontend base API URL matches backend server origin and path prefix.
- Fix CORS if FE and BE origins differ.
- Create a Settings page if no route named like '/settings' or 'Settings' component exists.
- Align FE payloads with BE Pydantic models.
- Verify KuCoin credentials loading (env) and ccxt client instantiation flow.