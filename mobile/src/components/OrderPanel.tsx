import React, { useState } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity,
  TextInput,
  Alert
} from 'react-native';

interface OrderPanelProps {
  symbol: string;
  currentPrice: number;
  onPlaceOrder: (orderData: any) => void;
}

const OrderPanel: React.FC<OrderPanelProps> = ({ 
  symbol, 
  currentPrice, 
  onPlaceOrder 
}) => {
  const [orderType, setOrderType] = useState<'buy' | 'sell'>('buy');
  const [amount, setAmount] = useState('');
  const [price, setPrice] = useState(currentPrice.toString());
  const [orderMode, setOrderMode] = useState<'market' | 'limit'>('market');

  const handlePlaceOrder = () => {
    if (!amount || parseFloat(amount) <= 0) {
      Alert.alert('Error', 'Please enter a valid amount');
      return;
    }

    const orderData = {
      symbol,
      type: orderType,
      amount: parseFloat(amount),
      price: orderMode === 'market' ? currentPrice : parseFloat(price),
      orderMode,
      timestamp: new Date().toISOString()
    };

    Alert.alert(
      'Confirm Order',
      `${orderType.toUpperCase()} ${amount} ${symbol} at ${orderMode === 'market' ? 'market price' : `$${price}`}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Confirm', 
          onPress: () => onPlaceOrder(orderData)
        }
      ]
    );
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Place Order - {symbol}</Text>
      
      {/* Order Type Toggle */}
      <View style={styles.toggleContainer}>
        <TouchableOpacity
          style={[styles.toggleButton, orderType === 'buy' && styles.buyActive]}
          onPress={() => setOrderType('buy')}
        >
          <Text style={[styles.toggleText, orderType === 'buy' && styles.buyText]}>
            BUY
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.toggleButton, orderType === 'sell' && styles.sellActive]}
          onPress={() => setOrderType('sell')}
        >
          <Text style={[styles.toggleText, orderType === 'sell' && styles.sellText]}>
            SELL
          </Text>
        </TouchableOpacity>
      </View>

      {/* Order Mode Toggle */}
      <View style={styles.modeContainer}>
        <TouchableOpacity
          style={[styles.modeButton, orderMode === 'market' && styles.modeActive]}
          onPress={() => setOrderMode('market')}
        >
          <Text style={[styles.modeText, orderMode === 'market' && styles.modeActiveText]}>
            Market
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.modeButton, orderMode === 'limit' && styles.modeActive]}
          onPress={() => setOrderMode('limit')}
        >
          <Text style={[styles.modeText, orderMode === 'limit' && styles.modeActiveText]}>
            Limit
          </Text>
        </TouchableOpacity>
      </View>

      {/* Amount Input */}
      <View style={styles.inputContainer}>
        <Text style={styles.inputLabel}>Amount</Text>
        <TextInput
          style={styles.input}
          value={amount}
          onChangeText={setAmount}
          placeholder="0.00"
          keyboardType="numeric"
        />
      </View>

      {/* Price Input (for limit orders) */}
      {orderMode === 'limit' && (
        <View style={styles.inputContainer}>
          <Text style={styles.inputLabel}>Price</Text>
          <TextInput
            style={styles.input}
            value={price}
            onChangeText={setPrice}
            placeholder={currentPrice.toString()}
            keyboardType="numeric"
          />
        </View>
      )}

      {/* Current Price Display */}
      <View style={styles.priceDisplay}>
        <Text style={styles.priceLabel}>Current Price</Text>
        <Text style={styles.priceValue}>${currentPrice.toLocaleString()}</Text>
      </View>

      {/* Place Order Button */}
      <TouchableOpacity
        style={[
          styles.orderButton,
          { backgroundColor: orderType === 'buy' ? '#4CAF50' : '#F44336' }
        ]}
        onPress={handlePlaceOrder}
      >
        <Text style={styles.orderButtonText}>
          {orderType.toUpperCase()} {symbol}
        </Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    padding: 20,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 20,
    textAlign: 'center',
  },
  toggleContainer: {
    flexDirection: 'row',
    backgroundColor: '#f0f0f0',
    borderRadius: 8,
    marginBottom: 20,
  },
  toggleButton: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
    borderRadius: 8,
  },
  buyActive: {
    backgroundColor: '#4CAF50',
  },
  sellActive: {
    backgroundColor: '#F44336',
  },
  toggleText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#666',
  },
  buyText: {
    color: '#fff',
  },
  sellText: {
    color: '#fff',
  },
  modeContainer: {
    flexDirection: 'row',
    marginBottom: 20,
  },
  modeButton: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#ddd',
    marginHorizontal: 2,
  },
  modeActive: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  modeText: {
    fontSize: 14,
    color: '#666',
  },
  modeActiveText: {
    color: '#fff',
  },
  inputContainer: {
    marginBottom: 15,
  },
  inputLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    paddingHorizontal: 15,
    paddingVertical: 12,
    fontSize: 16,
    color: '#333',
  },
  priceDisplay: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 15,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
    marginBottom: 20,
  },
  priceLabel: {
    fontSize: 14,
    color: '#666',
  },
  priceValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  orderButton: {
    paddingVertical: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  orderButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
});

export default OrderPanel;