import React from 'react';
import { 
  View, 
  Text, 
  ScrollView, 
  StyleSheet, 
  Dimensions,
  RefreshControl
} from 'react-native';
import { useWebSocket } from '../hooks/useWebSocket';
import { useNotifications } from '../hooks/useNotifications';
import TradingChart from '../components/TradingChart';
import PortfolioCard from '../components/PortfolioCard';
import LiveTradesComponent from '../components/LiveTradesComponent';
import AlertsComponent from '../components/AlertsComponent';

const { width } = Dimensions.get('window');

export default function DashboardScreen() {
  const { portfolio, trades, alerts, connected } = useWebSocket();
  const { hasPermission } = useNotifications();
  const [refreshing, setRefreshing] = React.useState(false);

  const onRefresh = React.useCallback(() => {
    setRefreshing(true);
    // Trigger data refresh
    setTimeout(() => {
      setRefreshing(false);
    }, 2000);
  }, []);

  return (
    <ScrollView 
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <View style={styles.header}>
        <Text style={styles.title}>Oracle Trader Dashboard</Text>
        <View style={[styles.connectionStatus, { 
          backgroundColor: connected ? '#4CAF50' : '#F44336' 
        }]}>
          <Text style={styles.connectionText}>
            {connected ? 'Connected' : 'Disconnected'}
          </Text>
        </View>
      </View>

      {/* Portfolio Overview */}
      <PortfolioCard 
        balance={portfolio?.balance || 0}
        pnl={portfolio?.pnl || 0}
        positions={portfolio?.positions || []}
      />

      {/* Trading Chart */}
      <View style={styles.chartContainer}>
        <TradingChart symbol="BTCUSDT" />
      </View>

      {/* Live Trades */}
      <LiveTradesComponent trades={trades || []} />

      {/* Alerts */}
      <AlertsComponent 
        alerts={alerts || []} 
        hasNotificationPermission={hasPermission}
      />

      {/* Quick Stats */}
      <View style={styles.statsContainer}>
        <View style={styles.statItem}>
          <Text style={styles.statValue}>{trades?.length || 0}</Text>
          <Text style={styles.statLabel}>Active Trades</Text>
        </View>
        <View style={styles.statItem}>
          <Text style={styles.statValue}>{alerts?.length || 0}</Text>
          <Text style={styles.statLabel}>Alerts</Text>
        </View>
        <View style={styles.statItem}>
          <Text style={styles.statValue}>
            {portfolio?.winRate ? `${portfolio.winRate}%` : '0%'}
          </Text>
          <Text style={styles.statLabel}>Win Rate</Text>
        </View>
      </View>
    </ScrollView>
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
    paddingTop: 60,
    backgroundColor: '#fff',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  connectionStatus: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  connectionText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
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
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    backgroundColor: '#fff',
    margin: 10,
    padding: 20,
    borderRadius: 8,
    elevation: 2,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#007AFF',
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
});