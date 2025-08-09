// Dashboard core functionality
let performanceChart = null;
let chartUpdatesPaused = false;

// Initialize dashboard
function initializeDashboard() {
    console.log('Initializing dashboard...');
    
    // Load initial data
    refreshDashboard();
    
    // Setup periodic updates
    setInterval(updateSystemMetrics, 5000); // Every 5 seconds
    setInterval(refreshWebSocketStats, 10000); // Every 10 seconds
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
        
        // Get dashboard data
        const response = await fetch('/dashboard/api/dashboard-data');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        updateDashboardDisplay(data);
        
        // Get trading metrics
        const metricsResponse = await fetch('/dashboard/api/trading-metrics');
        if (metricsResponse.ok) {
            const metrics = await metricsResponse.json();
            updateTradingMetrics(metrics);
        }
        
        // Get system status
        const statusResponse = await fetch('/dashboard/api/system-status');
        if (statusResponse.ok) {
            const status = await statusResponse.json();
            updateSystemStatus(status);
        }
        
    } catch (error) {
        console.error('Error refreshing dashboard:', error);
        showNotification('Error refreshing dashboard data', 'error');
    }
}

// Update dashboard display
function updateDashboardDisplay(data) {
    // Update quick stats
    updateElement('bot-status-display', data.bot_status);
    updateElement('daily-pnl-display', formatCurrency(data.daily_pnl));
    updateElement('active-positions-display', data.active_positions);
    updateElement('total-trades-display', data.total_trades);
    
    // Update bot status styling
    updateBotStatus(data.bot_status);
    
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
        const changeClass = data.change >= 0 ? 'text-success' : 'text-danger';
        const changeIcon = data.change >= 0 ? 'bi-arrow-up' : 'bi-arrow-down';
        
        row.innerHTML = `
            <td>${symbol}</td>
            <td>$${data.price.toFixed(2)}</td>
            <td class="${changeClass}">
                <i class="bi ${changeIcon} me-1"></i>
                ${Math.abs(data.change).toFixed(2)}%
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