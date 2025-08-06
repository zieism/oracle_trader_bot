import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';

interface WebSocketContextType {
  connected: boolean;
  portfolio: any;
  trades: any[];
  alerts: any[];
  marketData: any;
  positions: any[];
  subscribe: (channel: string) => void;
  unsubscribe: (channel: string) => void;
  sendMessage: (message: any) => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const [connected, setConnected] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [portfolio, setPortfolio] = useState(null);
  const [trades, setTrades] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [marketData, setMarketData] = useState<any>({});
  const [positions, setPositions] = useState<any[]>([]);

  const WS_URL = 'wss://api.oracletrader.com/ws'; // Replace with actual WebSocket URL

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    try {
      const websocket = new WebSocket(WS_URL);
      
      websocket.onopen = () => {
        console.log('WebSocket connected');
        setConnected(true);
        setWs(websocket);
        
        // Subscribe to default channels
        websocket.send(JSON.stringify({
          type: 'subscribe',
          channels: ['portfolio', 'trades', 'alerts', 'market_data']
        }));
      };

      websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleMessage(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      websocket.onclose = () => {
        console.log('WebSocket disconnected');
        setConnected(false);
        setWs(null);
        
        // Attempt to reconnect after 3 seconds
        setTimeout(() => {
          connectWebSocket();
        }, 3000);
      };

      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  };

  const handleMessage = (data: any) => {
    switch (data.type) {
      case 'portfolio_update':
        setPortfolio(data.data);
        break;
      case 'trade_update':
        setTrades(prevTrades => {
          const updatedTrades = [...prevTrades];
          const existingIndex = updatedTrades.findIndex(t => t.id === data.data.id);
          if (existingIndex >= 0) {
            updatedTrades[existingIndex] = data.data;
          } else {
            updatedTrades.unshift(data.data);
          }
          return updatedTrades.slice(0, 100); // Keep last 100 trades
        });
        break;
      case 'alert':
        setAlerts(prevAlerts => [data.data, ...prevAlerts.slice(0, 49)]);
        break;
      case 'market_data':
        setMarketData(prevData => ({
          ...prevData,
          [data.data.symbol]: data.data
        }));
        break;
      case 'positions_update':
        setPositions(data.data);
        break;
      default:
        console.log('Unknown message type:', data.type);
    }
  };

  const subscribe = (channel: string) => {
    if (ws && connected) {
      ws.send(JSON.stringify({
        type: 'subscribe',
        channel
      }));
    }
  };

  const unsubscribe = (channel: string) => {
    if (ws && connected) {
      ws.send(JSON.stringify({
        type: 'unsubscribe',
        channel
      }));
    }
  };

  const sendMessage = (message: any) => {
    if (ws && connected) {
      ws.send(JSON.stringify(message));
    }
  };

  const value: WebSocketContextType = {
    connected,
    portfolio,
    trades,
    alerts,
    marketData,
    positions,
    subscribe,
    unsubscribe,
    sendMessage
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};