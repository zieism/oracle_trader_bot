import React from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  FlatList,
  SafeAreaView
} from 'react-native';
import SocialFeed from '../components/SocialFeed';
import { useSocialData } from '../hooks/useSocialData';

export default function SocialScreen() {
  const { trades, discussions, leaderboard, isLoading } = useSocialData();

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Social Trading</Text>
      </View>

      <SocialFeed 
        trades={trades}
        discussions={discussions}
        leaderboard={leaderboard}
        isLoading={isLoading}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
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
});