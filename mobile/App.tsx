import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { StatusBar } from 'expo-status-bar';
import { View, Text } from 'react-native';

// Import screens
import DashboardScreen from './src/screens/Dashboard';
import TradingScreen from './src/screens/Trading';
import SocialScreen from './src/screens/Social';
import CommunityScreen from './src/screens/Community';
import ProfileScreen from './src/screens/Profile';

// Import services
import { WebSocketProvider } from './src/services/WebSocketService';
import { NotificationProvider } from './src/services/NotificationService';

const Tab = createBottomTabNavigator();

export default function App() {
  return (
    <WebSocketProvider>
      <NotificationProvider>
        <NavigationContainer>
          <StatusBar style="auto" />
          <Tab.Navigator
            screenOptions={{
              tabBarActiveTintColor: '#007AFF',
              tabBarInactiveTintColor: 'gray',
              headerShown: false,
            }}
          >
            <Tab.Screen 
              name="Dashboard" 
              component={DashboardScreen}
              options={{
                tabBarLabel: 'Dashboard',
                tabBarIcon: ({ color, size }) => (
                  <View style={{ width: size, height: size, backgroundColor: color }} />
                ),
              }}
            />
            <Tab.Screen 
              name="Trading" 
              component={TradingScreen}
              options={{
                tabBarLabel: 'Trading',
                tabBarIcon: ({ color, size }) => (
                  <View style={{ width: size, height: size, backgroundColor: color }} />
                ),
              }}
            />
            <Tab.Screen 
              name="Social" 
              component={SocialScreen}
              options={{
                tabBarLabel: 'Social',
                tabBarIcon: ({ color, size }) => (
                  <View style={{ width: size, height: size, backgroundColor: color }} />
                ),
              }}
            />
            <Tab.Screen 
              name="Community" 
              component={CommunityScreen}
              options={{
                tabBarLabel: 'Community',
                tabBarIcon: ({ color, size }) => (
                  <View style={{ width: size, height: size, backgroundColor: color }} />
                ),
              }}
            />
            <Tab.Screen 
              name="Profile" 
              component={ProfileScreen}
              options={{
                tabBarLabel: 'Profile',
                tabBarIcon: ({ color, size }) => (
                  <View style={{ width: size, height: size, backgroundColor: color }} />
                ),
              }}
            />
          </Tab.Navigator>
        </NavigationContainer>
      </NotificationProvider>
    </WebSocketProvider>
  );
}