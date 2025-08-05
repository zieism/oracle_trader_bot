// WebSocket connection management
class DashboardWebSocket {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.isConnecting = false;
        this.messageHandlers = new Map();
        
        this.setupEventHandlers();
    }
    
    connect() {
        if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
            return;
        }
        
        this.isConnecting = true;
        this.updateConnectionStatus('connecting');
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/dashboard/ws/dashboard`;
        
        try {
            this.ws = new WebSocket(wsUrl);
            this.setupWebSocketHandlers();
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.handleConnectionError();
        }
    }
    
    setupWebSocketHandlers() {
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.isConnecting = false;
            this.reconnectAttempts = 0;
            this.updateConnectionStatus('connected');
            this.sendMessage('get_status', {});
        };
        
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };
        
        this.ws.onclose = (event) => {
            console.log('WebSocket disconnected:', event.code, event.reason);
            this.isConnecting = false;
            this.updateConnectionStatus('disconnected');
            
            if (event.code !== 1000) { // Not a normal closure
                this.attemptReconnect();
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.handleConnectionError();
        };
    }
    
    setupEventHandlers() {
        // Register message handlers for different event types
        this.messageHandlers.set('connection_established', this.handleConnectionEstablished.bind(this));
        this.messageHandlers.set('bot_status_update', this.handleBotStatusUpdate.bind(this));
        this.messageHandlers.set('trade_executed', this.handleTradeExecuted.bind(this));
        this.messageHandlers.set('price_update', this.handlePriceUpdate.bind(this));
        this.messageHandlers.set('notification', this.handleNotification.bind(this));
        this.messageHandlers.set('system_update', this.handleSystemUpdate.bind(this));
        this.messageHandlers.set('portfolio_update', this.handlePortfolioUpdate.bind(this));
        this.messageHandlers.set('ping', this.handlePing.bind(this));
        this.messageHandlers.set('error', this.handleError.bind(this));
    }
    
    handleMessage(data) {
        const messageType = data.type;
        const handler = this.messageHandlers.get(messageType);
        
        if (handler) {
            handler(data);
        } else {
            console.log('Unhandled message type:', messageType, data);
        }
        
        // Add event to live events display
        if (messageType !== 'ping' && messageType !== 'system_update') {
            this.addLiveEvent(data);
        }
    }
    
    handleConnectionEstablished(data) {
        console.log('Dashboard connection established:', data);
        showNotification('Dashboard connected successfully', 'success');
    }
    
    handleBotStatusUpdate(data) {
        const status = data.data.status;
        updateBotStatus(status);
        showNotification(`Bot status: ${status}`, 'info');
    }
    
    handleTradeExecuted(data) {
        console.log('Trade executed:', data.data);
        refreshRecentTrades();
        showNotification('New trade executed', 'success');
    }
    
    handlePriceUpdate(data) {
        const { symbol, price } = data.data;
        updateMarketPrice(symbol, price);
    }
    
    handleNotification(data) {
        const { message, level } = data.data;
        showNotification(message, level);
    }
    
    handleSystemUpdate(data) {
        updateSystemMetrics(data);
    }
    
    handlePortfolioUpdate(data) {
        updatePortfolioMetrics(data.data);
    }
    
    handlePing(data) {
        // Respond to ping with pong
        this.sendMessage('pong', { timestamp: data.timestamp });
    }
    
    handleError(data) {
        console.error('WebSocket error message:', data.message);
        showNotification(data.message, 'error');
    }
    
    sendMessage(type, data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const message = JSON.stringify({ type, ...data });
            this.ws.send(message);
        } else {
            console.warn('WebSocket not connected, cannot send message:', type);
        }
    }
    
    subscribe(topic) {
        this.sendMessage('subscribe', { topic });
    }
    
    unsubscribe(topic) {
        this.sendMessage('unsubscribe', { topic });
    }
    
    updateConnectionStatus(status) {
        const statusIcon = document.getElementById('ws-status-icon');
        const statusText = document.getElementById('ws-status-text');
        
        if (!statusIcon || !statusText) return;
        
        statusIcon.className = 'bi bi-circle-fill me-1';
        
        switch (status) {
            case 'connected':
                statusIcon.classList.add('text-success');
                statusText.textContent = 'Connected';
                break;
            case 'connecting':
                statusIcon.classList.add('text-warning');
                statusText.textContent = 'Connecting...';
                break;
            case 'disconnected':
                statusIcon.classList.add('text-danger');
                statusText.textContent = 'Disconnected';
                break;
        }
    }
    
    handleConnectionError() {
        this.isConnecting = false;
        this.updateConnectionStatus('disconnected');
        this.attemptReconnect();
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            showNotification('Connection lost. Please refresh the page.', 'error');
            return;
        }
        
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
        
        setTimeout(() => {
            this.connect();
        }, delay);
    }
    
    addLiveEvent(data) {
        const container = document.getElementById('live-events-container');
        if (!container) return;
        
        // Clear "waiting" message if it exists
        const waitingMsg = container.querySelector('.text-muted');
        if (waitingMsg) {
            waitingMsg.remove();
        }
        
        const eventElement = document.createElement('div');
        eventElement.className = `event-item event-${data.type || 'info'}`;
        
        const timestamp = new Date(data.timestamp * 1000).toLocaleTimeString();
        const eventType = data.type || 'unknown';
        const message = data.data?.message || JSON.stringify(data.data || {});
        
        eventElement.innerHTML = `
            <div class="d-flex justify-content-between">
                <small class="text-muted">${timestamp}</small>
                <small class="text-muted">${eventType}</small>
            </div>
            <div class="mt-1">${message}</div>
        `;
        
        // Add to top of container
        container.insertBefore(eventElement, container.firstChild);
        
        // Limit to 50 events
        const events = container.querySelectorAll('.event-item');
        if (events.length > 50) {
            events[events.length - 1].remove();
        }
        
        // Highlight new event
        eventElement.classList.add('live-update');
        setTimeout(() => {
            eventElement.classList.remove('live-update');
        }, 1000);
    }
    
    disconnect() {
        if (this.ws) {
            this.ws.close(1000, 'User disconnect');
            this.ws = null;
        }
    }
}

// Global WebSocket instance
let dashboardWS = null;

// Initialize WebSocket connection
function initializeWebSocket() {
    dashboardWS = new DashboardWebSocket();
    dashboardWS.connect();
}

// Utility function to show notifications
function showNotification(message, type = 'info') {
    const toast = document.getElementById('notification-toast');
    const toastBody = document.getElementById('toast-message');
    const toastTime = document.getElementById('toast-time');
    
    if (!toast || !toastBody || !toastTime) return;
    
    // Set message and time
    toastBody.textContent = message;
    toastTime.textContent = new Date().toLocaleTimeString();
    
    // Set toast type styling
    toast.className = 'toast';
    switch (type) {
        case 'success':
            toast.classList.add('bg-success', 'text-white');
            break;
        case 'error':
        case 'danger':
            toast.classList.add('bg-danger', 'text-white');
            break;
        case 'warning':
            toast.classList.add('bg-warning', 'text-dark');
            break;
        default:
            toast.classList.add('bg-info', 'text-white');
    }
    
    // Show toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeWebSocket();
});

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    if (dashboardWS) {
        dashboardWS.disconnect();
    }
});