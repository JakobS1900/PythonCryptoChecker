/**
 * GEM P2P Trading Manager
 *
 * Handles all trading operations including order book display, order placement,
 * order cancellation, and trade history.
 */

class TradingManagerClass {
    constructor() {
        this.orderBook = { buy_orders: [], sell_orders: [] };
        this.myOrders = [];
        this.recentTrades = [];
        this.currentOrderType = 'buy'; // 'buy' or 'sell'
        this.currentFilter = 'active';
        this.userBalance = 0;
        this.refreshInterval = null;
    }

    async init() {
        console.log('[Trading] Initializing...');

        // Load initial data
        await this.loadBalance();
        await this.loadOrderBook();
        await this.loadMarketStats();
        await this.loadMyOrders();
        await this.loadRecentTrades();

        // Setup real-time updates every 10 seconds
        this.refreshInterval = setInterval(() => {
            this.loadOrderBook();
            this.loadMarketStats();
            this.loadMyOrders();
            this.loadRecentTrades();
        }, 10000);

        console.log('[Trading] Initialized successfully');
    }

    async loadBalance() {
        try {
            const token = localStorage.getItem('auth_token');
            if (!token) return;

            const response = await fetch('/api/auth/status', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                this.userBalance = data.gem_balance || 0;
                document.getElementById('user-balance').textContent = this.formatNumber(this.userBalance);
            }
        } catch (error) {
            console.error('[Trading] Error loading balance:', error);
        }
    }

    async loadOrderBook() {
        try {
            const response = await fetch('/api/trading/order-book');
            const data = await response.json();

            this.orderBook = data;
            this.renderOrderBook();
            this.updateBestPrices();
        } catch (error) {
            console.error('[Trading] Error loading order book:', error);
        }
    }

    renderOrderBook() {
        // Render sell orders (asks) - sorted lowest to highest
        const sellContainer = document.getElementById('sell-orders');
        if (this.orderBook.sell_orders.length === 0) {
            sellContainer.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="bi bi-inbox"></i>
                    <p class="mt-2 mb-0">No sell orders</p>
                </div>
            `;
        } else {
            let html = '';
            this.orderBook.sell_orders.forEach(order => {
                const remaining = order.amount - order.filled_amount;
                html += `
                    <div class="order-row sell-order mb-2" onclick="TradingManager.fillPriceFromOrder(${order.price})">
                        <div>
                            <div class="order-price price-sell">${this.formatNumber(order.price)}</div>
                            <small class="text-muted">${this.formatNumber(remaining)} GEM</small>
                        </div>
                        <div class="text-end">
                            <small class="text-muted">Total: ${this.formatNumber(order.price * remaining)}</small>
                        </div>
                    </div>
                `;
            });
            sellContainer.innerHTML = html;
        }

        // Render buy orders (bids) - sorted highest to lowest
        const buyContainer = document.getElementById('buy-orders');
        if (this.orderBook.buy_orders.length === 0) {
            buyContainer.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="bi bi-inbox"></i>
                    <p class="mt-2 mb-0">No buy orders</p>
                </div>
            `;
        } else {
            let html = '';
            this.orderBook.buy_orders.forEach(order => {
                const remaining = order.amount - order.filled_amount;
                html += `
                    <div class="order-row buy-order mb-2" onclick="TradingManager.fillPriceFromOrder(${order.price})">
                        <div>
                            <div class="order-price price-buy">${this.formatNumber(order.price)}</div>
                            <small class="text-muted">${this.formatNumber(remaining)} GEM</small>
                        </div>
                        <div class="text-end">
                            <small class="text-muted">Total: ${this.formatNumber(order.price * remaining)}</small>
                        </div>
                    </div>
                `;
            });
            buyContainer.innerHTML = html;
        }

        // Calculate and display spread
        this.updateSpread();
    }

    updateBestPrices() {
        const bestBuy = this.orderBook.buy_orders[0]?.price;
        const bestSell = this.orderBook.sell_orders[0]?.price;

        if (this.currentOrderType === 'buy') {
            document.getElementById('best-price').textContent = bestSell ? this.formatNumber(bestSell) : '-';
        } else {
            document.getElementById('best-price').textContent = bestBuy ? this.formatNumber(bestBuy) : '-';
        }
    }

    updateSpread() {
        const bestBuy = this.orderBook.buy_orders[0]?.price;
        const bestSell = this.orderBook.sell_orders[0]?.price;

        if (bestBuy && bestSell) {
            const spread = bestSell - bestBuy;
            const spreadPercent = ((spread / bestBuy) * 100).toFixed(2);
            document.getElementById('spread-display').textContent = `${this.formatNumber(spread)} (${spreadPercent}%)`;
            document.getElementById('stat-spread').textContent = `${this.formatNumber(spread)} GEM`;
        } else {
            document.getElementById('spread-display').textContent = '-';
            document.getElementById('stat-spread').textContent = '-';
        }
    }

    fillPriceFromOrder(price) {
        document.getElementById('order-price').value = price;
        this.updateTotalCost();
    }

    async loadMarketStats() {
        try {
            const response = await fetch('/api/trading/stats');
            const stats = await response.json();

            document.getElementById('stat-volume').textContent = this.formatNumber(stats.total_volume_24h);
            document.getElementById('stat-trades').textContent = this.formatNumber(stats.total_trades_24h);
            document.getElementById('stat-orders').textContent = this.formatNumber(stats.active_orders_count);
        } catch (error) {
            console.error('[Trading] Error loading market stats:', error);
        }
    }

    async loadMyOrders(status = null) {
        try {
            const token = localStorage.getItem('auth_token');
            if (!token) {
                document.getElementById('my-orders-list').innerHTML = `
                    <div class="alert-modern alert-modern-warning">
                        <div class="alert-modern-content">
                            <div class="alert-modern-message">Please login to view your orders</div>
                        </div>
                    </div>
                `;
                return;
            }

            const url = status ? `/api/trading/my-orders?status=${status}` : '/api/trading/my-orders';
            const response = await fetch(url, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const orders = await response.json();
                this.myOrders = orders;
                this.renderMyOrders(orders);
            }
        } catch (error) {
            console.error('[Trading] Error loading my orders:', error);
        }
    }

    renderMyOrders(orders) {
        const container = document.getElementById('my-orders-list');

        if (orders.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="bi bi-inbox" style="font-size: 3rem; color: var(--text-secondary);"></i>
                    <p class="mt-3">No ${this.currentFilter === 'active' ? 'active' : ''} orders found</p>
                </div>
            `;
            return;
        }

        let html = `
            <div class="table-responsive">
                <table class="table-modern">
                    <thead>
                        <tr>
                            <th>Type</th>
                            <th>Price</th>
                            <th>Amount</th>
                            <th>Filled</th>
                            <th>Status</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        orders.forEach(order => {
            const typeClass = order.order_type === 'buy' ? 'price-buy' : 'price-sell';
            const typeIcon = order.order_type === 'buy' ? 'arrow-up-circle' : 'arrow-down-circle';
            const fillPercent = Math.round((order.filled_amount / order.amount) * 100);
            const statusClass = `status-${order.status}`;

            html += `
                <tr>
                    <td>
                        <span class="${typeClass}">
                            <i class="bi bi-${typeIcon}"></i>
                            ${order.order_type.toUpperCase()}
                        </span>
                    </td>
                    <td><strong>${this.formatNumber(order.price)}</strong> GEM</td>
                    <td>${this.formatNumber(order.amount)} GEM</td>
                    <td>
                        ${this.formatNumber(order.filled_amount)}
                        <small class="text-muted">(${fillPercent}%)</small>
                    </td>
                    <td>
                        <span class="status-badge ${statusClass}">
                            ${order.status}
                        </span>
                    </td>
                    <td>
                        <small>${new Date(order.created_at).toLocaleString()}</small>
                    </td>
                    <td>
                        ${order.status === 'active' || order.status === 'partial' ? `
                            <button class="btn-modern btn-modern-sm btn-modern-danger"
                                    onclick="TradingManager.cancelOrder(${order.id})">
                                <i class="bi bi-x-circle"></i>
                                Cancel
                            </button>
                        ` : '-'}
                    </td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;

        container.innerHTML = html;
    }

    async loadRecentTrades() {
        try {
            const response = await fetch('/api/trading/trades/recent?limit=20');
            const trades = await response.json();

            this.recentTrades = trades;
            this.renderRecentTrades(trades);
        } catch (error) {
            console.error('[Trading] Error loading recent trades:', error);
        }
    }

    renderRecentTrades(trades) {
        const container = document.getElementById('recent-trades-list');

        if (trades.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="bi bi-inbox" style="font-size: 3rem; color: var(--text-secondary);"></i>
                    <p class="mt-3">No recent trades</p>
                </div>
            `;
            return;
        }

        let html = `
            <div class="table-responsive">
                <table class="table-modern">
                    <thead>
                        <tr>
                            <th>Price</th>
                            <th>Amount</th>
                            <th>Total</th>
                            <th>Fee</th>
                            <th>Time</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        trades.forEach(trade => {
            html += `
                <tr>
                    <td><strong class="price-buy">${this.formatNumber(trade.price)}</strong> GEM</td>
                    <td>${this.formatNumber(trade.amount)} GEM</td>
                    <td>${this.formatNumber(trade.total_value)} GEM</td>
                    <td class="text-muted">${this.formatNumber(trade.fee)} GEM</td>
                    <td>
                        <small>${this.formatTimeAgo(new Date(trade.created_at))}</small>
                    </td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;

        container.innerHTML = html;
    }

    switchOrderType(type) {
        this.currentOrderType = type;

        // Update tab states
        document.querySelectorAll('.trade-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`.trade-tab.${type}`).classList.add('active');

        // Update form button
        const submitBtn = document.getElementById('submit-btn-text');
        const submitBtnIcon = document.getElementById('submit-order-btn').querySelector('i');

        if (type === 'buy') {
            submitBtn.textContent = 'Place Buy Order';
            submitBtnIcon.className = 'bi bi-arrow-up-circle';
            document.getElementById('price-type-label').textContent = 'sell';
            document.getElementById('total-label').textContent = 'Cost';
        } else {
            submitBtn.textContent = 'Place Sell Order';
            submitBtnIcon.className = 'bi bi-arrow-down-circle';
            document.getElementById('price-type-label').textContent = 'buy';
            document.getElementById('total-label').textContent = 'Revenue';
        }

        // Update best price display
        this.updateBestPrices();

        // Recalculate total cost
        this.updateTotalCost();
    }

    updateTotalCost() {
        const price = parseInt(document.getElementById('order-price').value) || 0;
        const amount = parseInt(document.getElementById('order-amount').value) || 0;

        const orderValue = price * amount;
        const fee = Math.floor(orderValue * 0.02); // 2% fee
        const total = orderValue + fee;

        document.getElementById('order-value').textContent = this.formatNumber(orderValue);
        document.getElementById('order-fee').textContent = this.formatNumber(fee);
        document.getElementById('order-total').textContent = this.formatNumber(total);
    }

    async placeOrder(event) {
        event.preventDefault();

        const token = localStorage.getItem('auth_token');
        if (!token) {
            window.location.href = '/login?redirect=/trading';
            return;
        }

        const price = parseInt(document.getElementById('order-price').value);
        const amount = parseInt(document.getElementById('order-amount').value);

        if (!price || !amount) {
            this.showError('Please enter both price and amount');
            return;
        }

        if (price <= 0 || amount <= 0) {
            this.showError('Price and amount must be greater than 0');
            return;
        }

        try {
            const response = await fetch('/api/trading/order', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    order_type: this.currentOrderType,
                    price: price,
                    amount: amount
                })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Failed to place order');
            }

            this.showSuccess(result.message);

            // Clear form
            document.getElementById('trade-form').reset();
            this.updateTotalCost();

            // Refresh data
            await this.loadBalance();
            await this.loadOrderBook();
            await this.loadMarketStats();
            await this.loadMyOrders();
            await this.loadRecentTrades();

        } catch (error) {
            console.error('[Trading] Error placing order:', error);
            this.showError(error.message);
        }
    }

    async cancelOrder(orderId) {
        if (!confirm('Cancel this order?')) return;

        try {
            const token = localStorage.getItem('auth_token');
            const response = await fetch(`/api/trading/cancel-order/${orderId}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Failed to cancel order');
            }

            this.showSuccess(result.message);

            // Refresh data
            await this.loadBalance();
            await this.loadOrderBook();
            await this.loadMarketStats();
            await this.loadMyOrders();

        } catch (error) {
            console.error('[Trading] Error cancelling order:', error);
            this.showError(error.message);
        }
    }

    filterOrders(filter) {
        this.currentFilter = filter;

        // Update button states
        document.querySelectorAll('#my-orders-list').parent().querySelectorAll('.btn-group button').forEach(btn => {
            btn.classList.remove('active', 'btn-modern-primary');
            btn.classList.add('btn-modern-secondary');
        });
        event.target.classList.remove('btn-modern-secondary');
        event.target.classList.add('active', 'btn-modern-primary');

        // Load orders with filter
        const status = filter === 'active' ? 'active' : null;
        this.loadMyOrders(status);
    }

    formatNumber(num) {
        return new Intl.NumberFormat('en-US').format(num);
    }

    formatTimeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);

        if (seconds < 60) return `${seconds}s ago`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        return `${Math.floor(seconds / 86400)}d ago`;
    }

    showSuccess(message) {
        if (window.Toast) {
            Toast.success(message);
        } else if (window.showAlert) {
            window.showAlert(message, 'success');
        } else {
            console.log('[SUCCESS]', message);
        }
    }

    showError(message) {
        if (window.Toast) {
            Toast.error(message);
        } else if (window.showAlert) {
            window.showAlert(message, 'danger');
        } else {
            console.error('[ERROR]', message);
        }
    }

    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }
}

// Create global instance
const TradingManager = new TradingManagerClass();

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    TradingManager.destroy();
});
