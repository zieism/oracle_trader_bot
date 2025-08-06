import React from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  FlatList,
  TouchableOpacity
} from 'react-native';

interface TradingSignal {
  id: string;
  trader: string;
  symbol: string;
  action: 'buy' | 'sell';
  confidence: number;
  targetPrice: number;
  stopLoss?: number;
  reasoning: string;
  timestamp: string;
}

const TradingSignals: React.FC = () => {
  const signals: TradingSignal[] = [
    {
      id: '1',
      trader: 'ProTrader99',
      symbol: 'BTCUSDT',
      action: 'buy',
      confidence: 85,
      targetPrice: 45000,
      stopLoss: 40000,
      reasoning: 'Strong support at 42k, RSI oversold, expecting bounce',
      timestamp: '2024-01-01T10:30:00Z'
    },
    {
      id: '2',
      trader: 'CryptoWhale',
      symbol: 'ETHUSDT',
      action: 'sell',
      confidence: 72,
      targetPrice: 2800,
      stopLoss: 3200,
      reasoning: 'Resistance at 3k level, high volume selling pressure',
      timestamp: '2024-01-01T09:45:00Z'
    }
  ];

  const renderSignal = ({ item }: { item: TradingSignal }) => {
    const actionColor = item.action === 'buy' ? '#4CAF50' : '#F44336';
    const confidenceColor = item.confidence >= 80 ? '#4CAF50' : 
                           item.confidence >= 60 ? '#FF9800' : '#F44336';

    return (
      <View style={styles.signalItem}>
        <View style={styles.signalHeader}>
          <View style={styles.traderInfo}>
            <Text style={styles.trader}>{item.trader}</Text>
            <View style={[styles.confidenceBadge, { backgroundColor: confidenceColor }]}>
              <Text style={styles.confidenceText}>{item.confidence}%</Text>
            </View>
          </View>
          <Text style={styles.timestamp}>
            {new Date(item.timestamp).toLocaleTimeString()}
          </Text>
        </View>

        <View style={styles.signalContent}>
          <View style={styles.tradeInfo}>
            <Text style={styles.symbol}>{item.symbol}</Text>
            <Text style={[styles.action, { color: actionColor }]}>
              {item.action.toUpperCase()}
            </Text>
          </View>

          <View style={styles.priceInfo}>
            <Text style={styles.priceLabel}>Target: ${item.targetPrice.toLocaleString()}</Text>
            {item.stopLoss && (
              <Text style={styles.priceLabel}>Stop: ${item.stopLoss.toLocaleString()}</Text>
            )}
          </View>

          <Text style={styles.reasoning}>{item.reasoning}</Text>

          <View style={styles.actions}>
            <TouchableOpacity style={[styles.actionButton, styles.copyButton]}>
              <Text style={styles.actionButtonText}>Copy Trade</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.actionButton, styles.followButton]}>
              <Text style={styles.actionButtonText}>Follow</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <FlatList
        data={signals}
        renderItem={renderSignal}
        keyExtractor={(item) => item.id}
        showsVerticalScrollIndicator={false}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  signalItem: {
    backgroundColor: '#fff',
    margin: 10,
    borderRadius: 8,
    elevation: 2,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  signalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  traderInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  trader: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginRight: 10,
  },
  confidenceBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  confidenceText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  timestamp: {
    fontSize: 12,
    color: '#666',
  },
  signalContent: {
    padding: 15,
  },
  tradeInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  symbol: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  action: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  priceInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  priceLabel: {
    fontSize: 14,
    color: '#666',
  },
  reasoning: {
    fontSize: 14,
    color: '#333',
    lineHeight: 20,
    marginBottom: 15,
  },
  actions: {
    flexDirection: 'row',
    gap: 10,
  },
  actionButton: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 6,
    alignItems: 'center',
  },
  copyButton: {
    backgroundColor: '#007AFF',
  },
  followButton: {
    backgroundColor: '#4CAF50',
  },
  actionButtonText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 14,
  },
});

export default TradingSignals;