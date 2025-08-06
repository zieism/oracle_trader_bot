import { useState, useEffect } from 'react';

interface SocialData {
  trades: any[];
  discussions: any[];
  leaderboard: any[];
  isLoading: boolean;
}

export const useSocialData = (): SocialData => {
  const [socialData, setSocialData] = useState<SocialData>({
    trades: [],
    discussions: [],
    leaderboard: [],
    isLoading: false
  });

  useEffect(() => {
    // Mock data for now
    setSocialData({
      trades: [
        {
          id: '1',
          trader: 'CryptoMaster',
          symbol: 'BTCUSDT',
          action: 'buy',
          price: 42300,
          timestamp: new Date().toISOString()
        }
      ],
      discussions: [
        {
          id: '1',
          title: 'BTC Analysis',
          author: 'TradeAnalyst',
          content: 'Strong support at 42k...',
          timestamp: new Date().toISOString()
        }
      ],
      leaderboard: [
        {
          id: '1',
          username: 'TopTrader',
          roi: 25.5,
          followers: 1250,
          rank: 1
        }
      ],
      isLoading: false
    });
  }, []);

  return socialData;
};