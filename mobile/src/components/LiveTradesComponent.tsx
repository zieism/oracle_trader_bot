import React from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  FlatList,
  TouchableOpacity
} from 'react-native';

interface Trade {
  id: string;
  symbol: string;
  action: 'buy' | 'sell';
  amount: number;
  price: number;
  pnl?: number;
  status: 'open' | 'closed';
  timestamp: string;
}

interface LiveTradesComponentProps {
  trades: Trade[];
}

const LiveTradesComponent: React.FC<LiveTradesComponentProps> = ({ trades }) => {
  const renderTrade = ({ item }: { item: Trade }) => {
    const actionColor = item.action === 'buy' ? '#4CAF50' : '#F44336';
    const pnlColor = item.pnl && item.pnl >= 0 ? '#4CAF50' : '#F44336';

    return (
      <TouchableOpacity style={styles.tradeItem}>
        <View style={styles.tradeHeader}>
          <Text style={styles.symbol}>{item.symbol}</Text>
          <Text style={[styles.action, { color: actionColor }]}>
            {item.action.toUpperCase()}
          </Text>
        </View>
        
        <View style={styles.tradeDetails}>
          <Text style={styles.amount}>
            {item.amount} @ ${item.price.toLocaleString()}
          </Text>
          <Text style={styles.status}>{item.status}</Text>
        </View>
        
        {item.pnl !== undefined && (
          <Text style={[styles.pnl, { color: pnlColor }]}>
            P&L: ${item.pnl.toFixed(2)}
          </Text>
        )}
        
        <Text style={styles.timestamp}>
          {new Date(item.timestamp).toLocaleTimeString()}
        </Text>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Live Trades</Text>
      {trades.length > 0 ? (
        <FlatList
          data={trades.slice(0, 10)} // Show last 10 trades
          renderItem={renderTrade}
          keyExtractor={(item) => item.id}
          showsVerticalScrollIndicator={false}
        />
      ) : (
        <Text style={styles.emptyText}>No active trades</Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#fff',
    margin: 10,
    borderRadius: 8,
    elevation: 2,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    padding: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
    color: '#333',
  },
  tradeItem: {
    padding: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#f8f9fa',
  },
  tradeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  symbol: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  action: {
    fontSize: 14,
    fontWeight: 'bold',
  },
  tradeDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  amount: {
    fontSize: 14,
    color: '#666',
  },
  status: {
    fontSize: 12,
    color: '#999',
    textTransform: 'uppercase',
  },
  pnl: {
    fontSize: 14,
    fontWeight: '500',
    marginBottom: 4,
  },
  timestamp: {
    fontSize: 12,
    color: '#999',
  },
  emptyText: {
    textAlign: 'center',
    color: '#666',
    padding: 20,
    fontStyle: 'italic',
  },
});

export default LiveTradesComponent;