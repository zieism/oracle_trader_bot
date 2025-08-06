import React from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  FlatList
} from 'react-native';

interface Discussion {
  id: string;
  title: string;
  author: string;
  replies: number;
  likes: number;
  timestamp: string;
}

const TradingDiscussions: React.FC = () => {
  // Mock data
  const discussions: Discussion[] = [
    {
      id: '1',
      title: 'BTC Technical Analysis - Bull Run Incoming?',
      author: 'CryptoAnalyst',
      replies: 24,
      likes: 18,
      timestamp: '2024-01-01T10:30:00Z'
    },
    {
      id: '2',
      title: 'Risk Management Strategies for Volatile Markets',
      author: 'RiskMaster',
      replies: 15,
      likes: 32,
      timestamp: '2024-01-01T09:15:00Z'
    },
    {
      id: '3',
      title: 'Best AI Trading Signals This Week',
      author: 'AITrader',
      replies: 8,
      likes: 12,
      timestamp: '2024-01-01T08:45:00Z'
    }
  ];

  const renderDiscussion = ({ item }: { item: Discussion }) => (
    <View style={styles.discussionItem}>
      <Text style={styles.title}>{item.title}</Text>
      <Text style={styles.author}>by {item.author}</Text>
      <View style={styles.stats}>
        <Text style={styles.stat}>💬 {item.replies}</Text>
        <Text style={styles.stat}>👍 {item.likes}</Text>
        <Text style={styles.timestamp}>
          {new Date(item.timestamp).toLocaleDateString()}
        </Text>
      </View>
    </View>
  );

  return (
    <View style={styles.container}>
      <FlatList
        data={discussions}
        renderItem={renderDiscussion}
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
  discussionItem: {
    backgroundColor: '#fff',
    margin: 10,
    padding: 15,
    borderRadius: 8,
    elevation: 2,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  title: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 8,
  },
  author: {
    fontSize: 14,
    color: '#666',
    marginBottom: 12,
  },
  stats: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  stat: {
    fontSize: 12,
    color: '#999',
  },
  timestamp: {
    fontSize: 12,
    color: '#999',
  },
});

export default TradingDiscussions;