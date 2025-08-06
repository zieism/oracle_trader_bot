import React from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  ScrollView
} from 'react-native';

const CommunityAnalysis: React.FC = () => {
  const sentiment = {
    bullish: 65,
    bearish: 35,
    symbols: [
      { symbol: 'BTCUSDT', sentiment: 'bullish', score: 0.8 },
      { symbol: 'ETHUSDT', sentiment: 'bullish', score: 0.6 },
      { symbol: 'ADAUSDT', sentiment: 'bearish', score: -0.4 }
    ]
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Market Sentiment</Text>
        <View style={styles.sentimentBar}>
          <View style={[styles.bullishBar, { width: `${sentiment.bullish}%` }]}>
            <Text style={styles.sentimentText}>{sentiment.bullish}% Bullish</Text>
          </View>
          <View style={[styles.bearishBar, { width: `${sentiment.bearish}%` }]}>
            <Text style={styles.sentimentText}>{sentiment.bearish}% Bearish</Text>
          </View>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Symbol Sentiment</Text>
        {sentiment.symbols.map((item, index) => (
          <View key={index} style={styles.symbolItem}>
            <Text style={styles.symbol}>{item.symbol}</Text>
            <View style={styles.sentimentInfo}>
              <Text style={[
                styles.sentimentLabel,
                { color: item.sentiment === 'bullish' ? '#4CAF50' : '#F44336' }
              ]}>
                {item.sentiment}
              </Text>
              <Text style={styles.score}>
                {item.score > 0 ? '+' : ''}{(item.score * 100).toFixed(0)}%
              </Text>
            </View>
          </View>
        ))}
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Trending Analysis</Text>
        <View style={styles.trendingItem}>
          <Text style={styles.trendingTitle}>Bitcoin Breakout Pattern</Text>
          <Text style={styles.trendingDesc}>
            Community consensus: 78% expect bullish breakout above $45k
          </Text>
        </View>
        <View style={styles.trendingItem}>
          <Text style={styles.trendingTitle}>DeFi Season Incoming</Text>
          <Text style={styles.trendingDesc}>
            Increased discussion around DeFi tokens, 65% positive sentiment
          </Text>
        </View>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  section: {
    backgroundColor: '#fff',
    margin: 10,
    padding: 15,
    borderRadius: 8,
    elevation: 2,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 15,
  },
  sentimentBar: {
    flexDirection: 'row',
    height: 40,
    borderRadius: 20,
    overflow: 'hidden',
    backgroundColor: '#f0f0f0',
  },
  bullishBar: {
    backgroundColor: '#4CAF50',
    justifyContent: 'center',
    alignItems: 'center',
  },
  bearishBar: {
    backgroundColor: '#F44336',
    justifyContent: 'center',
    alignItems: 'center',
  },
  sentimentText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 12,
  },
  symbolItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  symbol: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  sentimentInfo: {
    alignItems: 'flex-end',
  },
  sentimentLabel: {
    fontSize: 14,
    fontWeight: '500',
    textTransform: 'capitalize',
  },
  score: {
    fontSize: 12,
    color: '#666',
  },
  trendingItem: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  trendingTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  trendingDesc: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
});

export default CommunityAnalysis;