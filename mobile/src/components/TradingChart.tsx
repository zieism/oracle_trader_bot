import React from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  Dimensions,
  TouchableOpacity 
} from 'react-native';
import { LineChart } from 'react-native-chart-kit';

interface TradingChartProps {
  symbol: string;
  height?: number;
}

const { width } = Dimensions.get('window');

const TradingChart: React.FC<TradingChartProps> = ({ 
  symbol, 
  height = 220 
}) => {
  // Mock data - in real app, this would come from WebSocket
  const data = {
    labels: ['1h', '2h', '3h', '4h', '5h', '6h'],
    datasets: [
      {
        data: [42000, 42100, 41900, 42200, 42150, 42300],
        strokeWidth: 2,
      },
    ],
  };

  const chartConfig = {
    backgroundColor: '#ffffff',
    backgroundGradientFrom: '#ffffff',
    backgroundGradientTo: '#ffffff',
    decimalPlaces: 0,
    color: (opacity = 1) => `rgba(0, 122, 255, ${opacity})`,
    labelColor: (opacity = 1) => `rgba(102, 102, 102, ${opacity})`,
    style: {
      borderRadius: 8,
    },
    propsForDots: {
      r: '4',
      strokeWidth: '2',
      stroke: '#007AFF',
    },
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.symbol}>{symbol}</Text>
        <View style={styles.priceContainer}>
          <Text style={styles.price}>$42,300</Text>
          <Text style={[styles.change, { color: '#4CAF50' }]}>+1.2%</Text>
        </View>
      </View>
      
      <LineChart
        data={data}
        width={width - 40}
        height={height}
        chartConfig={chartConfig}
        bezier
        style={styles.chart}
      />

      <View style={styles.controls}>
        <TouchableOpacity style={styles.timeButton}>
          <Text style={styles.timeButtonText}>1m</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.timeButton, styles.activeTimeButton]}>
          <Text style={[styles.timeButtonText, styles.activeTimeButtonText]}>1h</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.timeButton}>
          <Text style={styles.timeButtonText}>1d</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.timeButton}>
          <Text style={styles.timeButtonText}>1w</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    padding: 15,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 15,
  },
  symbol: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  priceContainer: {
    alignItems: 'flex-end',
  },
  price: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  change: {
    fontSize: 14,
    fontWeight: '500',
  },
  chart: {
    marginVertical: 8,
    borderRadius: 8,
  },
  controls: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: 15,
  },
  timeButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 4,
    backgroundColor: '#f0f0f0',
  },
  activeTimeButton: {
    backgroundColor: '#007AFF',
  },
  timeButtonText: {
    fontSize: 14,
    color: '#666',
  },
  activeTimeButtonText: {
    color: '#fff',
    fontWeight: '500',
  },
});

export default TradingChart;