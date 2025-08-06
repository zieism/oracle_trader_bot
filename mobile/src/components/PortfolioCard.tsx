import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

interface PortfolioCardProps {
  balance: number;
  pnl: number;
  positions: any[];
}

const PortfolioCard: React.FC<PortfolioCardProps> = ({ balance, pnl, positions }) => {
  const pnlColor = pnl >= 0 ? '#4CAF50' : '#F44336';

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Portfolio</Text>
      <View style={styles.row}>
        <View style={styles.item}>
          <Text style={styles.value}>${balance.toLocaleString()}</Text>
          <Text style={styles.label}>Balance</Text>
        </View>
        <View style={styles.item}>
          <Text style={[styles.value, { color: pnlColor }]}>
            ${pnl.toLocaleString()}
          </Text>
          <Text style={styles.label}>P&L</Text>
        </View>
        <View style={styles.item}>
          <Text style={styles.value}>{positions.length}</Text>
          <Text style={styles.label}>Positions</Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#fff',
    margin: 10,
    padding: 20,
    borderRadius: 8,
    elevation: 2,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 15,
    color: '#333',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  item: {
    alignItems: 'center',
  },
  value: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#007AFF',
  },
  label: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
});

export default PortfolioCard;