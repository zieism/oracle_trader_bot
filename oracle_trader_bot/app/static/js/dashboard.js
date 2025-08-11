// Dashboard core functionality
let performanceChart = null;
let chartUpdatesPaused = false;

// Initialize dashboard
function initializeDashboard() {
    console.log('Initializing dashboard...');
    
    // Show loading state
    showLoadingState();
    
    // Load initial data
    refreshDashboard();
    
    // Setup periodic updates
    setInterval(updateSystemMetrics, 5000); // Every 5 seconds
    setInterval(refreshWebSocketStats, 10000); // Every 10 seconds
}

// Show loading state
function showLoadingState() {
    updateElement('bot-status-display', 'Loading...');
    updateElement('daily-pnl-display', 'Loading...');
    updateElement('active-positions-display', 'Loading...');
    updateElement('total-trades-display', 'Loading...');
}

// Initialize charts
function initializeCharts() {
    initializePerformanceChart();
}

// Initialize performance chart
function initializePerformanceChart() {
    const ctx = document.getElementById('performance-chart');
    if (!ctx) return;
    
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded. Cannot initialize performance chart.');
        // Show error message in the chart container
        ctx.innerHTML = '<div class="alert alert-danger">Chart.js library failed to load. Please refresh the page.</div>';
        return;
    }
    
    performanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Portfolio Value',
                data: [],
                borderColor: 'rgb(13, 110, 253)',
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                tension: 0.1
            }, {
                label: 'P&L',
                data: [],
                borderColor: 'rgb(25, 135, 84)',
                backgroundColor: 'rgba(25, 135, 84, 0.1)',
                tension: 0.1,
                yAxisID: 'y1'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: 'white'
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: 'white'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    ticks: {
                        color: 'white'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    ticks: {
                        color: 'white'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                }
            }
        }
    });
    
    // Add some sample data
    addChartData(performanceChart, new Date().toLocaleTimeString(), 10000, 0);
}

// Add data to chart
function addChartData(chart, label, portfolioValue, pnl) {
    if (!chart || chartUpdatesPaused) return;
    
    chart.data.labels.push(label);
    chart.data.datasets[0].data.push(portfolioValue);
    chart.data.datasets[1].data.push(pnl);
    
    // Keep only last 20 data points
    if (chart.data.labels.length > 20) {
        chart.data.labels.shift();
        chart.data.datasets.forEach(dataset => dataset.data.shift());
    }
    
    chart.update('none');
}

// Refresh dashboard data
async function refreshDashboard() {
    try {
        console.log('Refreshing dashboard data...');
        
        // Try to get dashboard data
        let response = await fetch('/dashboard/api/dashboard-data');
        let data;
        
        if (!response.ok) {
            console.warn('Main dashboard API failed, trying test endpoint...');
            // Fallback to test endpoint
            response = await fetch('/dashboard/api/test-data');
            if (response.ok) {
                const testData = await response.json();
                // Convert test data to dashboard format
                data = {
                    bot_status: testData.test_data?.bot_status || 'unknown',
                    daily_pnl: testData.test_data?.daily_pnl || 0,
                    active_positions: 0,
                    total_trades: testData.test_data?.total_trades || 0,
                    total_balance: 1000.0,
                    market_data: testData.test_data?.market_prices || {},
                    recent_trades: [],
                    system_health: {
                        cpu_usage: 25.0,
                        memory_usage: 60.0,
                        websocket_connections: 0
                    },
                    account_overview: []
                };
                console.log('Using test data as fallback');
            } else {
                throw new Error(`Both main API and test API failed! status: ${response.status}`);
            }
        } else {
            data = await response.json();
        }
        
        updateDashboardDisplay(data);
        
        // Get trading metrics (optional)
        try {
            const metricsResponse = await fetch('/dashboard/api/trading-metrics');
            if (metricsResponse.ok) {
                const metrics = await metricsResponse.json();
                updateTradingMetrics(metrics);
            }
        } catch (e) {
            console.warn('Trading metrics unavailable:', e);
        }
        
        // Get system status (optional)
        try {
            const statusResponse = await fetch('/dashboard/api/system-status');
            if (statusResponse.ok) {
                const status = await statusResponse.json();
                updateSystemStatus(status);
            }
        } catch (e) {
            console.warn('System status unavailable:', e);
        }
        
    } catch (error) {
        console.error('Error refreshing dashboard:', error);
        showNotification(`Error refreshing dashboard data: ${error.message}`, 'error');
        // Show mock data when everything fails
        displayMockData();
    }
}

// Display mock data when all APIs fail
function displayMockData() {
    const mockData = {
        bot_status: 'stopped',
        daily_pnl: 0,
        active_positions: 0,
        total_trades: 0,
        total_balance: 1000.0,
        market_data: {
            'BTC/USDT': { price: '45000.00', change: '0.5' },
            'ETH/USDT': { price: '3200.00', change: '-1.2' }
        },
        recent_trades: [],
        system_health: {
            cpu_usage: 15.5,
            memory_usage: 45.2,
            websocket_connections: 0
        },
        account_overview: [
            {
                currency: "USDT",
                total: 1000.0,
                free: 950.0,
                used: 50.0
            }
        ]
    };
    
    updateDashboardDisplay(mockData);
    console.log('Displaying mock data due to API failures');
}

// Update dashboard display
function updateDashboardDisplay(data) {
    // Update quick stats
    updateElement('bot-status-display', data.bot_status);
    updateElement('daily-pnl-display', formatCurrency(data.daily_pnl));
    updateElement('active-positions-display', data.active_positions);
    updateElement('total-trades-display', data.total_trades);
    
    // Update total balance
    updateElement('total-balance-display', formatCurrency(data.total_balance));
    
    // Update bot status styling
    updateBotStatus(data.bot_status);
    
    // Update account overview
    updateAccountOverview(data.account_overview);
    
    // Update market data table
    updateMarketDataTable(data.market_data);
    
    // Update recent trades
    updateRecentTradesList(data.recent_trades);
    
    // Update system health
    updateSystemHealth(data.system_health);
    
    // Update chart with new data
    if (performanceChart && !chartUpdatesPaused) {
        const timestamp = new Date().toLocaleTimeString();
        addChartData(performanceChart, timestamp, data.total_balance, data.daily_pnl);
    }
}

// Update account overview
function updateAccountOverview(accountData) {
    const container = document.getElementById('account-overview');
    if (!container || !accountData) return;
    
    container.innerHTML = '';
    
    accountData.forEach(account => {
        const total = parseFloat(account.total) || 0;
        const free = parseFloat(account.free) || 0;
        const used = parseFloat(account.used) || 0;
        
        const accountDiv = document.createElement('div');
        accountDiv.className = 'mb-3 p-3 border rounded bg-dark';
        accountDiv.innerHTML = `
            <div class="d-flex justify-content-between mb-2">
                <strong>${account.currency}</strong>
                <span class="text-success">${total.toFixed(4)}</span>
            </div>
            <div class="small text-muted">
                <div class="d-flex justify-content-between">
                    <span>Free:</span>
                    <span>${free.toFixed(4)}</span>
                </div>
                <div class="d-flex justify-content-between">
                    <span>Used:</span>
                    <span>${used.toFixed(4)}</span>
                </div>
            </div>
        `;
        container.appendChild(accountDiv);
    });
}

// Update bot status
function updateBotStatus(status) {
    const statusDisplay = document.getElementById('bot-status-display');
    const statusAlert = document.getElementById('bot-status-alert');
    const statusMessage = document.getElementById('bot-status-message');
    
    if (statusDisplay) {
        statusDisplay.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        
        // Update parent card styling
        const card = statusDisplay.closest('.card');
        if (card) {
            card.className = 'card text-white h-100';
            switch (status) {
                case 'running':
                    card.classList.add('bg-success');
                    break;
                case 'stopped':
                    card.classList.add('bg-danger');
                    break;
                default:
                    card.classList.add('bg-warning');
            }
        }
    }
    
    // Show status alert if needed
    if (statusAlert && statusMessage) {
        if (status === 'error' || status === 'stopped') {
            statusMessage.textContent = `Bot is currently ${status}`;
            statusAlert.classList.remove('d-none');
        } else {
            statusAlert.classList.add('d-none');
        }
    }
}

// Update market data table
function updateMarketDataTable(marketData) {
    const tableBody = document.getElementById('market-data-table');
    if (!tableBody || !marketData) return;
    
    tableBody.innerHTML = '';
    
    Object.entries(marketData).forEach(([symbol, data]) => {
        const row = document.createElement('tr');
        const price = parseFloat(data.price) || 0;
        const change = parseFloat(data.change) || 0;
        const changeClass = change >= 0 ? 'text-success' : 'text-danger';
        const changeIcon = change >= 0 ? 'bi-arrow-up' : 'bi-arrow-down';
        
        row.innerHTML = `
            <td>${symbol}</td>
            <td>$${price.toFixed(2)}</td>
            <td class="${changeClass}">
                <i class="bi ${changeIcon} me-1"></i>
                ${Math.abs(change).toFixed(2)}%
            </td>
            <td>
                <span class="badge bg-success">Active</span>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
}

// Update recent trades list
function updateRecentTradesList(trades) {
    const tradesList = document.getElementById('recent-trades-list');
    if (!tradesList || !trades) return;
    
    tradesList.innerHTML = '';
    
    if (trades.length === 0) {
        tradesList.innerHTML = '<div class="list-group-item text-center">No recent trades</div>';
        return;
    }
    
    trades.forEach(trade => {
        const tradeElement = document.createElement('div');
        tradeElement.className = 'list-group-item trade-item';
        
        const pnlClass = trade.pnl >= 0 ? 'trade-profit' : 'trade-loss';
        const sideClass = trade.side === 'buy' ? 'text-success' : 'text-danger';
        
        tradeElement.innerHTML = `
            <div class="d-flex justify-content-between">
                <div>
                    <strong>${trade.symbol}</strong>
                    <span class="badge ${sideClass === 'text-success' ? 'bg-success' : 'bg-danger'} ms-2">
                        ${trade.side.toUpperCase()}
                    </span>
                </div>
                <div class="${pnlClass}">
                    ${formatCurrency(trade.pnl)}
                </div>
            </div>
            <div class="d-flex justify-content-between text-muted small">
                <span>Qty: ${trade.quantity}</span>
                <span>Price: $${trade.price}</span>
            </div>
        `;
        
        tradesList.appendChild(tradeElement);
    });
}

// Update system health
function updateSystemHealth(healthData) {
    if (!healthData) return;
    
    updateProgressBar('cpu-progress', 'cpu-usage', healthData.cpu_usage, '%');
    updateProgressBar('memory-progress', 'memory-usage', healthData.memory_usage, '%');
    updateProgressBar('ws-progress', 'ws-connection-count', healthData.websocket_connections, '');
    
    // Update WebSocket connections display
    updateElement('ws-connections', `${healthData.websocket_connections} connections`);
}

// Update system metrics from WebSocket
function updateSystemMetrics(data) {
    if (data && data.type === 'system_update') {
        updateProgressBar('cpu-progress', 'cpu-usage', data.cpu_usage, '%');
        updateProgressBar('memory-progress', 'memory-usage', data.memory_usage, '%');
        updateElement('ws-connection-count', data.websocket_connections);
    }
}

// Update progress bar
function updateProgressBar(progressId, textId, value, suffix) {
    const progressBar = document.getElementById(progressId);
    const textElement = document.getElementById(textId);
    
    if (progressBar) {
        progressBar.style.width = `${Math.min(value, 100)}%`;
        
        // Update color based on value
        progressBar.className = 'progress-bar';
        if (value < 50) {
            progressBar.classList.add('bg-success');
        } else if (value < 80) {
            progressBar.classList.add('bg-warning');
        } else {
            progressBar.classList.add('bg-danger');
        }
    }
    
    if (textElement) {
        textElement.textContent = `${value.toFixed(1)}${suffix}`;
    }
}

// Bot control functions
async function controlBot(action) {
    try {
        const button = document.getElementById(`${action}-bot-btn`);
        if (button) {
            button.disabled = true;
            button.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${action.charAt(0).toUpperCase() + action.slice(1)}ing...`;
        }
        
        const response = await fetch(`/dashboard/api/bot-control/${action}`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        showNotification(result.message, 'success');
        
        // Refresh dashboard after action
        setTimeout(refreshDashboard, 2000);
        
    } catch (error) {
        console.error(`Error ${action} bot:`, error);
        showNotification(`Error ${action}ing bot: ${error.message}`, 'error');
    } finally {
        // Reset button
        const button = document.getElementById(`${action}-bot-btn`);
        if (button) {
            button.disabled = false;
            const icon = action === 'start' ? 'play-fill' : action === 'stop' ? 'stop-fill' : 'arrow-clockwise';
            button.innerHTML = `<i class="bi bi-${icon} me-2"></i>${action.charAt(0).toUpperCase() + action.slice(1)} Bot`;
        }
    }
}

// Test WebSocket function
async function emitTestEvent() {
    try {
        const response = await fetch('/dashboard/api/emit-test-event', {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        showNotification('Test event emitted successfully', 'info');
        
    } catch (error) {
        console.error('Error emitting test event:', error);
        showNotification('Error emitting test event', 'error');
    }
}

// Toggle chart updates
function toggleChartUpdates() {
    chartUpdatesPaused = !chartUpdatesPaused;
    const toggleButton = document.querySelector('[onclick="toggleChartUpdates()"]');
    const toggleText = document.getElementById('chart-toggle-text');
    
    if (toggleText) {
        toggleText.textContent = chartUpdatesPaused ? 'Resume Updates' : 'Pause Updates';
    }
    
    if (toggleButton) {
        const icon = toggleButton.querySelector('i');
        if (icon) {
            icon.className = chartUpdatesPaused ? 'bi bi-play-fill me-2' : 'bi bi-pause-fill me-2';
        }
    }
    
    showNotification(`Chart updates ${chartUpdatesPaused ? 'paused' : 'resumed'}`, 'info');
}

// Clear event log
function clearEventLog() {
    const container = document.getElementById('live-events-container');
    if (container) {
        container.innerHTML = '<div class="p-3 text-center text-muted">Event log cleared</div>';
    }
}

// Refresh WebSocket stats
async function refreshWebSocketStats() {
    try {
        const response = await fetch('/dashboard/api/websocket-stats');
        if (response.ok) {
            const stats = await response.json();
            updateElement('ws-connections', `${stats.total_connections} connections`);
        }
    } catch (error) {
        console.error('Error refreshing WebSocket stats:', error);
    }
}

// Utility functions
function updateElement(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
        element.classList.add('live-update');
        setTimeout(() => element.classList.remove('live-update'), 1000);
    }
}

function formatCurrency(value) {
    if (typeof value !== 'number') return '$0.00';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(value);
}

function updateMarketPrice(symbol, price) {
    // This would update market prices in real-time
    console.log(`Price update: ${symbol} = $${price}`);
}

function updatePortfolioMetrics(data) {
    // Update portfolio-related displays
    if (data.total_balance) {
        updateElement('total-balance-display', formatCurrency(data.total_balance));
    }
    if (data.daily_pnl !== undefined) {
        updateElement('daily-pnl-display', formatCurrency(data.daily_pnl));
    }
}

function refreshRecentTrades() {
    // Refresh trades would trigger a partial dashboard refresh
    refreshDashboard();
}

function updateTradingMetrics(metrics) {
    // Update additional trading metrics if displayed
    console.log('Trading metrics:', metrics);
}

function updateSystemStatus(status) {
    // Update system status displays
    console.log('System status:', status);
}

// Settings Management Functions
let availableSymbols = [];
let selectedSymbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT'];

async function loadAvailableSymbols() {
    try {
        const response = await fetch('/api/trading-symbols');
        const data = await response.json();
        
        if (data.symbols) {
            availableSymbols = data.symbols;
            console.log('Loaded available symbols:', availableSymbols);
        }
    } catch (error) {
        console.error('Error loading symbols:', error);
        // Use fallback symbols
        availableSymbols = [
            {symbol: 'BTC/USDT:USDT', base: 'BTC', quote: 'USDT', active: true},
            {symbol: 'ETH/USDT:USDT', base: 'ETH', quote: 'USDT', active: true},
            {symbol: 'ADA/USDT:USDT', base: 'ADA', quote: 'USDT', active: true},
            {symbol: 'DOT/USDT:USDT', base: 'DOT', quote: 'USDT', active: true},
            {symbol: 'SOL/USDT:USDT', base: 'SOL', quote: 'USDT', active: true}
        ];
    }
}

function openSymbolSelector() {
    // Load symbols if not already loaded
    if (availableSymbols.length === 0) {
        loadAvailableSymbols();
    }
    
    // Populate modal with symbols
    const symbolList = document.getElementById('symbol-list');
    symbolList.innerHTML = '';
    
    availableSymbols.forEach(symbol => {
        const isSelected = selectedSymbols.includes(symbol.symbol);
        
        const col = document.createElement('div');
        col.className = 'col-12 mb-2';
        
        col.innerHTML = `
            <div class="form-check">
                <input class="form-check-input" type="checkbox" value="${symbol.symbol}" 
                       id="symbol-${symbol.base}" ${isSelected ? 'checked' : ''}>
                <label class="form-check-label" for="symbol-${symbol.base}">
                    ${symbol.symbol} <span class="text-muted">(${symbol.base}/${symbol.quote})</span>
                </label>
            </div>
        `;
        
        symbolList.appendChild(col);
    });
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('symbolModal'));
    modal.show();
}

function filterSymbols() {
    const searchTerm = document.getElementById('symbol-search').value.toLowerCase();
    const checkboxes = document.querySelectorAll('#symbol-list .form-check');
    
    checkboxes.forEach(checkbox => {
        const label = checkbox.querySelector('label').textContent.toLowerCase();
        const parent = checkbox.closest('.col-12');
        
        if (label.includes(searchTerm)) {
            parent.style.display = 'block';
        } else {
            parent.style.display = 'none';
        }
    });
}

async function saveSymbolSelection() {
    const checkboxes = document.querySelectorAll('#symbol-list input[type="checkbox"]:checked');
    const newSelectedSymbols = Array.from(checkboxes).map(cb => cb.value);
    
    try {
        const response = await fetch('/api/settings/symbols', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ symbols: newSelectedSymbols })
        });
        
        const result = await response.json();
        
        if (result.success) {
            selectedSymbols = newSelectedSymbols;
            updateSelectedSymbolsDisplay();
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('symbolModal'));
            modal.hide();
            
            showNotification('Symbols saved successfully!', 'success');
        } else {
            showNotification('Failed to save symbols', 'error');
        }
        
    } catch (error) {
        console.error('Error saving symbols:', error);
        showNotification('Error saving symbols', 'error');
    }
}

function updateSelectedSymbolsDisplay() {
    const container = document.getElementById('selected-symbols');
    container.innerHTML = '';
    
    selectedSymbols.forEach(symbol => {
        const badge = document.createElement('span');
        badge.className = 'badge bg-secondary me-1 mb-1';
        badge.textContent = symbol.replace(':USDT', '');
        container.appendChild(badge);
    });
}

async function saveSettings() {
    const leverage = document.getElementById('leverage-input').value;
    const riskPerTrade = document.getElementById('risk-input').value;
    
    const settings = {
        trading_symbols: selectedSymbols,
        leverage: parseInt(leverage),
        risk_per_trade: parseFloat(riskPerTrade),
        max_positions: 5,
        stop_loss_pct: 3.0,
        take_profit_pct: 6.0,
        auto_trading: false
    };
    
    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(settings)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Settings saved successfully!', 'success');
        } else {
            showNotification('Failed to save settings', 'error');
        }
        
    } catch (error) {
        console.error('Error saving settings:', error);
        showNotification('Error saving settings', 'error');
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 3000);
}

// Initialize settings on page load
document.addEventListener('DOMContentLoaded', function() {
    loadAvailableSymbols();
    updateSelectedSymbolsDisplay();
});