import React, { useState } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  SafeAreaView,
  Dimensions
} from 'react-native';
import TradingChart from '../components/TradingChart';
import OrderPanel from '../components/OrderPanel';
import PositionsTable from '../components/PositionsTable';
import { useWebSocket } from '../hooks/useWebSocket';

const { width, height } = Dimensions.get('window');

export default function TradingScreen() {
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT');
  const { positions, marketData } = useWebSocket();

  const handlePlaceOrder = async (orderData: any) => {
    try {
      // Place order through API
      console.log('Placing order:', orderData);
    } catch (error) {
      console.error('Failed to place order:', error);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Trading</Text>
        <Text style={styles.symbol}>{selectedSymbol}</Text>
      </View>

      {/* Trading Chart */}
      <View style={styles.chartContainer}>
        <TradingChart 
          symbol={selectedSymbol}
          height={height * 0.4}
        />
      </View>

      {/* Order Panel */}
      <View style={styles.orderContainer}>
        <OrderPanel 
          symbol={selectedSymbol}
          currentPrice={marketData?.[selectedSymbol]?.price || 0}
          onPlaceOrder={handlePlaceOrder}
        />
      </View>

      {/* Positions Table */}
      <View style={styles.positionsContainer}>
        <PositionsTable positions={positions || []} />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#fff',
    elevation: 2,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  symbol: {
    fontSize: 18,
    fontWeight: '600',
    color: '#007AFF',
  },
  chartContainer: {
    backgroundColor: '#fff',
    margin: 10,
    borderRadius: 8,
    elevation: 2,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  orderContainer: {
    backgroundColor: '#fff',
    margin: 10,
    borderRadius: 8,
    elevation: 2,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  positionsContainer: {
    flex: 1,
    backgroundColor: '#fff',
    margin: 10,
    borderRadius: 8,
    elevation: 2,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
});