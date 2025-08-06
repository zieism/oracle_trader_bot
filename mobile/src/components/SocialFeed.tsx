import React from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  FlatList,
  TouchableOpacity,
  RefreshControl
} from 'react-native';

interface SocialPost {
  id: string;
  trader: {
    id: string;
    username: string;
    avatar?: string;
    verified: boolean;
  };
  trade?: {
    symbol: string;
    action: 'buy' | 'sell';
    price: number;
    amount: number;
    timestamp: string;
  };
  content?: string;
  likes: number;
  comments: number;
  timestamp: string;
}

interface SocialFeedProps {
  trades: any[];
  discussions: any[];
  leaderboard: any[];
  isLoading: boolean;
}

const SocialFeed: React.FC<SocialFeedProps> = ({ 
  trades, 
  discussions, 
  leaderboard, 
  isLoading 
}) => {
  const [refreshing, setRefreshing] = React.useState(false);

  // Mock social posts data
  const socialPosts: SocialPost[] = [
    {
      id: '1',
      trader: {
        id: 'trader1',
        username: 'CryptoMaster',
        verified: true,
      },
      trade: {
        symbol: 'BTCUSDT',
        action: 'buy',
        price: 42300,
        amount: 0.5,
        timestamp: '2024-01-01T10:30:00Z',
      },
      likes: 24,
      comments: 8,
      timestamp: '2024-01-01T10:30:00Z',
    },
    {
      id: '2',
      trader: {
        id: 'trader2',
        username: 'TradeAnalyst',
        verified: false,
      },
      content: 'BTC showing strong support at $42k. Expecting bounce to $45k resistance.',
      likes: 15,
      comments: 5,
      timestamp: '2024-01-01T09:15:00Z',
    },
  ];

  const onRefresh = React.useCallback(() => {
    setRefreshing(true);
    setTimeout(() => {
      setRefreshing(false);
    }, 2000);
  }, []);

  const copyTrade = (trade: any) => {
    console.log('Copying trade:', trade);
    // Implement copy trading logic
  };

  const renderSocialPost = ({ item }: { item: SocialPost }) => {
    return (
      <View style={styles.postContainer}>
        <View style={styles.postHeader}>
          <View style={styles.traderInfo}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>
                {item.trader.username.charAt(0).toUpperCase()}
              </Text>
            </View>
            <View>
              <View style={styles.usernameContainer}>
                <Text style={styles.username}>{item.trader.username}</Text>
                {item.trader.verified && (
                  <Text style={styles.verifiedBadge}>✓</Text>
                )}
              </View>
              <Text style={styles.timestamp}>
                {new Date(item.timestamp).toLocaleTimeString()}
              </Text>
            </View>
          </View>
        </View>

        {item.trade && (
          <View style={styles.tradeContainer}>
            <View style={styles.tradeHeader}>
              <Text style={styles.tradeTitle}>
                {item.trade.action.toUpperCase()} {item.trade.symbol}
              </Text>
              <TouchableOpacity 
                style={styles.copyButton}
                onPress={() => copyTrade(item.trade)}
              >
                <Text style={styles.copyButtonText}>Copy</Text>
              </TouchableOpacity>
            </View>
            <View style={styles.tradeDetails}>
              <Text style={styles.tradeDetail}>
                Price: ${item.trade.price.toLocaleString()}
              </Text>
              <Text style={styles.tradeDetail}>
                Amount: {item.trade.amount} {item.trade.symbol.replace('USDT', '')}
              </Text>
            </View>
          </View>
        )}

        {item.content && (
          <Text style={styles.content}>{item.content}</Text>
        )}

        <View style={styles.postActions}>
          <TouchableOpacity style={styles.actionButton}>
            <Text style={styles.actionText}>👍 {item.likes}</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionButton}>
            <Text style={styles.actionText}>💬 {item.comments}</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionButton}>
            <Text style={styles.actionText}>📤 Share</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  };

  return (
    <FlatList
      data={socialPosts}
      renderItem={renderSocialPost}
      keyExtractor={(item) => item.id}
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
      showsVerticalScrollIndicator={false}
    />
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  postContainer: {
    backgroundColor: '#fff',
    margin: 10,
    borderRadius: 8,
    padding: 15,
    elevation: 2,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  postHeader: {
    marginBottom: 10,
  },
  traderInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 10,
  },
  avatarText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 16,
  },
  usernameContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  username: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  verifiedBadge: {
    marginLeft: 4,
    color: '#4CAF50',
    fontSize: 12,
  },
  timestamp: {
    fontSize: 12,
    color: '#666',
  },
  tradeContainer: {
    backgroundColor: '#f8f9fa',
    padding: 12,
    borderRadius: 6,
    marginBottom: 10,
  },
  tradeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  tradeTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#007AFF',
  },
  copyButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4,
  },
  copyButtonText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  tradeDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  tradeDetail: {
    fontSize: 14,
    color: '#666',
  },
  content: {
    fontSize: 14,
    color: '#333',
    lineHeight: 20,
    marginBottom: 10,
  },
  postActions: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
    paddingTop: 10,
  },
  actionButton: {
    paddingVertical: 5,
  },
  actionText: {
    fontSize: 14,
    color: '#666',
  },
});

export default SocialFeed;