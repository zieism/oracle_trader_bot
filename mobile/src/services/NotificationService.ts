import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import Constants from 'expo-constants';

interface NotificationContextType {
  hasPermission: boolean;
  pushToken: string | null;
  notifications: any[];
  requestPermission: () => Promise<boolean>;
  scheduleNotification: (title: string, body: string, data?: any) => Promise<void>;
  clearNotifications: () => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

// Configure notifications
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

interface NotificationProviderProps {
  children: ReactNode;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const [hasPermission, setHasPermission] = useState(false);
  const [pushToken, setPushToken] = useState<string | null>(null);
  const [notifications, setNotifications] = useState<any[]>([]);

  useEffect(() => {
    initializeNotifications();
  }, []);

  const initializeNotifications = async () => {
    // Request permissions on startup
    const permitted = await requestPermission();
    if (permitted) {
      const token = await registerForPushNotificationsAsync();
      setPushToken(token);
    }

    // Listen for notifications
    const notificationListener = Notifications.addNotificationReceivedListener(notification => {
      setNotifications(prev => [notification, ...prev.slice(0, 99)]);
    });

    const responseListener = Notifications.addNotificationResponseReceivedListener(response => {
      console.log('Notification response:', response);
      // Handle notification tap
    });

    return () => {
      Notifications.removeNotificationSubscription(notificationListener);
      Notifications.removeNotificationSubscription(responseListener);
    };
  };

  const requestPermission = async (): Promise<boolean> => {
    if (!Device.isDevice) {
      console.log('Must use physical device for Push Notifications');
      return false;
    }

    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;
    
    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }
    
    if (finalStatus !== 'granted') {
      console.log('Failed to get push token for push notification!');
      setHasPermission(false);
      return false;
    }
    
    setHasPermission(true);
    return true;
  };

  const registerForPushNotificationsAsync = async (): Promise<string | null> => {
    if (!Device.isDevice) {
      return null;
    }

    try {
      const token = (await Notifications.getExpoPushTokenAsync({
        projectId: Constants.expoConfig?.extra?.eas?.projectId,
      })).data;
      
      console.log('Push token:', token);
      return token;
    } catch (error) {
      console.error('Error getting push token:', error);
      return null;
    }
  };

  const scheduleNotification = async (title: string, body: string, data?: any) => {
    try {
      await Notifications.scheduleNotificationAsync({
        content: {
          title,
          body,
          data,
        },
        trigger: null, // Show immediately
      });
    } catch (error) {
      console.error('Error scheduling notification:', error);
    }
  };

  const clearNotifications = () => {
    setNotifications([]);
    Notifications.dismissAllNotificationsAsync();
  };

  const value: NotificationContextType = {
    hasPermission,
    pushToken,
    notifications,
    requestPermission,
    scheduleNotification,
    clearNotifications,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};

export const useNotifications = (): NotificationContextType => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};