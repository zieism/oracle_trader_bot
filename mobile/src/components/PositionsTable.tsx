import React from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  FlatList
} from 'react-native';

interface Position {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  size: number;
  entryPrice: number;
  markPrice: number;
  pnl: number;
  pnlPercent: number;
}

interface PositionsTableProps {
  positions: Position[];
}

const PositionsTable: React.FC<PositionsTableProps> = ({ positions }) => {
  const renderPosition = ({ item }: { item: Position }) => {
    const sideColor = item.side === 'long' ? '#4CAF50' : '#F44336';
    const pnlColor = item.pnl >= 0 ? '#4CAF50' : '#F44336';

    return (
      <View style={styles.positionRow}>
        <View style={styles.symbolContainer}>
          <Text style={styles.symbol}>{item.symbol}</Text>
          <Text style={[styles.side, { color: sideColor }]}>
            {item.side.toUpperCase()}
          </Text>
        </View>
        
        <View style={styles.priceContainer}>
          <Text style={styles.price}>Entry: ${item.entryPrice}</Text>
          <Text style={styles.price}>Mark: ${item.markPrice}</Text>
        </View>
        
        <View style={styles.pnlContainer}>
          <Text style={[styles.pnl, { color: pnlColor }]}>
            ${item.pnl.toFixed(2)}
          </Text>
          <Text style={[styles.pnlPercent, { color: pnlColor }]}>
            {item.pnlPercent >= 0 ? '+' : ''}{item.pnlPercent.toFixed(2)}%
          </Text>
        </View>
        
        <View style={styles.sizeContainer}>
          <Text style={styles.size}>{item.size}</Text>
        </View>
      </View>
    );
  };

  if (positions.length === 0) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Positions</Text>
        <Text style={styles.emptyText}>No open positions</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Positions</Text>
      
      {/* Header */}
      <View style={styles.headerRow}>
        <Text style={styles.headerText}>Symbol/Side</Text>
        <Text style={styles.headerText}>Prices</Text>
        <Text style={styles.headerText}>P&L</Text>
        <Text style={styles.headerText}>Size</Text>
      </View>
      
      <FlatList
        data={positions}
        renderItem={renderPosition}
        keyExtractor={(item) => item.id}
        showsVerticalScrollIndicator={false}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    padding: 15,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 15,
  },
  headerRow: {
    flexDirection: 'row',
    paddingVertical: 10,
    borderBottomWidth: 2,
    borderBottomColor: '#007AFF',
    marginBottom: 10,
  },
  headerText: {
    flex: 1,
    fontSize: 12,
    fontWeight: 'bold',
    color: '#007AFF',
    textAlign: 'center',
  },
  positionRow: {
    flexDirection: 'row',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
    alignItems: 'center',
  },
  symbolContainer: {
    flex: 1,
    alignItems: 'center',
  },
  symbol: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#333',
  },
  side: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  priceContainer: {
    flex: 1,
    alignItems: 'center',
  },
  price: {
    fontSize: 12,
    color: '#666',
  },
  pnlContainer: {
    flex: 1,
    alignItems: 'center',
  },
  pnl: {
    fontSize: 14,
    fontWeight: 'bold',
  },
  pnlPercent: {
    fontSize: 12,
    fontWeight: '500',
  },
  sizeContainer: {
    flex: 1,
    alignItems: 'center',
  },
  size: {
    fontSize: 14,
    color: '#333',
  },
  emptyText: {
    textAlign: 'center',
    color: '#666',
    padding: 20,
    fontStyle: 'italic',
  },
});

export default PositionsTable;