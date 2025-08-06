import React from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  FlatList,
  TouchableOpacity
} from 'react-native';

interface Alert {
  id: string;
  title: string;
  message: string;
  type: 'info' | 'warning' | 'success' | 'error';
  timestamp: string;
  priority: number;
}

interface AlertsComponentProps {
  alerts: Alert[];
  hasNotificationPermission: boolean;
}

const AlertsComponent: React.FC<AlertsComponentProps> = ({ 
  alerts, 
  hasNotificationPermission 
}) => {
  const getAlertColor = (type: string) => {
    switch (type) {
      case 'success': return '#4CAF50';
      case 'warning': return '#FF9800';
      case 'error': return '#F44336';
      default: return '#2196F3';
    }
  };

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'success': return '✅';
      case 'warning': return '⚠️';
      case 'error': return '❌';
      default: return 'ℹ️';
    }
  };

  const renderAlert = ({ item }: { item: Alert }) => {
    return (
      <TouchableOpacity style={styles.alertItem}>
        <View style={[styles.alertIndicator, { backgroundColor: getAlertColor(item.type) }]} />
        
        <View style={styles.alertContent}>
          <View style={styles.alertHeader}>
            <Text style={styles.alertIcon}>{getAlertIcon(item.type)}</Text>
            <Text style={styles.alertTitle}>{item.title}</Text>
            <Text style={styles.priority}>P{item.priority}</Text>
          </View>
          
          <Text style={styles.alertMessage}>{item.message}</Text>
          
          <Text style={styles.alertTime}>
            {new Date(item.timestamp).toLocaleTimeString()}
          </Text>
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Alerts</Text>
        {!hasNotificationPermission && (
          <TouchableOpacity style={styles.permissionButton}>
            <Text style={styles.permissionText}>Enable Notifications</Text>
          </TouchableOpacity>
        )}
      </View>
      
      {alerts.length > 0 ? (
        <FlatList
          data={alerts.slice(0, 5)} // Show last 5 alerts
          renderItem={renderAlert}
          keyExtractor={(item) => item.id}
          showsVerticalScrollIndicator={false}
        />
      ) : (
        <Text style={styles.emptyText}>No recent alerts</Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#fff',
    margin: 10,
    borderRadius: 8,
    elevation: 2,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  permissionButton: {
    backgroundColor: '#FF9800',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4,
  },
  permissionText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  alertItem: {
    flexDirection: 'row',
    padding: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#f8f9fa',
  },
  alertIndicator: {
    width: 4,
    borderRadius: 2,
    marginRight: 12,
  },
  alertContent: {
    flex: 1,
  },
  alertHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  alertIcon: {
    fontSize: 16,
    marginRight: 8,
  },
  alertTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    flex: 1,
  },
  priority: {
    fontSize: 12,
    color: '#666',
    backgroundColor: '#f0f0f0',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 3,
  },
  alertMessage: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
    marginBottom: 8,
  },
  alertTime: {
    fontSize: 12,
    color: '#999',
  },
  emptyText: {
    textAlign: 'center',
    color: '#666',
    padding: 20,
    fontStyle: 'italic',
  },
});

export default AlertsComponent;