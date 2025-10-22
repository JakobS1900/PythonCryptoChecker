/**
 * GEM Store - Frontend JavaScript
 * Handles package display, purchase flow, and history
 */

class GemStoreManager {
    constructor() {
        this.packages = [];
        this.selectedPackage = null;
        this.purchaseModal = null;
        this.successModal = null;

        this.init();
    }

    async init() {
        console.log('🏪 Initializing GEM Store...');

        // Initialize modals
        this.purchaseModal = new bootstrap.Modal(document.getElementById('purchaseModal'));
        this.successModal = new bootstrap.Modal(document.getElementById('successModal'));

        // Load data
        await this.loadBalance();
        await this.loadPackages();
        await this.loadPurchaseHistory();

        // Setup event listeners
        this.setupEventListeners();

        console.log('✅ GEM Store initialized');
    }

    setupEventListeners() {
        // Confirm purchase button
        const confirmBtn = document.getElementById('confirm-purchase-btn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.completePurchase());
        }
    }

    async loadBalance() {
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                document.getElementById('current-balance').innerHTML = '<span>Login Required</span>';
                return;
            }

            const response = await fetch('/api/auth/me', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            const result = await response.json();
            if (result.success && result.data.wallet) {
                const balance = result.data.wallet.gem_balance;
                document.getElementById('current-balance').innerHTML =
                    `<i class="bi bi-gem"></i> <span>${this.formatNumber(balance)}</span> GEM`;
            }
        } catch (error) {
            console.error('Error loading balance:', error);
        }
    }

    async loadPackages() {
        try {
            const response = await fetch('/api/gem-store/packages');
            const packages = await response.json();

            this.packages = packages;
            this.renderPackages(packages);
        } catch (error) {
            console.error('Error loading packages:', error);
            document.getElementById('packages-grid').innerHTML = `
                <div class="col-12 text-center py-5">
                    <p style="color: var(--error);">Failed to load packages. Please try again.</p>
                </div>
            `;
        }
    }

    renderPackages(packages) {
        const grid = document.getElementById('packages-grid');

        let html = '';
        packages.forEach(pkg => {
            const badgeHtml = pkg.badge ?
                `<div class="badge-modern badge-modern-${pkg.color}" style="position: absolute; top: var(--space-3); right: var(--space-3); font-size: var(--text-xs);">
                    ${pkg.badge}
                </div>` : '';

            const popularBadge = pkg.popular ?
                `<div class="badge-modern badge-modern-warning" style="position: absolute; top: var(--space-3); left: var(--space-3); font-size: var(--text-xs);">
                    ⭐ Most Popular
                </div>` : '';

            const bestValueBadge = pkg.best_value ?
                `<div class="badge-modern badge-modern-gem" style="position: absolute; top: var(--space-3); left: var(--space-3); font-size: var(--text-xs);">
                    💎 Best Value
                </div>` : '';

            const borderColor = pkg.popular || pkg.best_value ? 'var(--gem)' : 'var(--border-subtle)';

            html += `
                <div class="col-lg-4 col-md-6 mb-4">
                    <div class="card-modern" style="position: relative; border: 2px solid ${borderColor}; height: 100%; display: flex; flex-direction: column;">
                        ${popularBadge}
                        ${bestValueBadge}
                        ${badgeHtml}

                        <div style="padding: var(--space-6); flex: 1; display: flex; flex-direction: column;">
                            <!-- Icon -->
                            <div style="text-align: center; margin-bottom: var(--space-4);">
                                <i class="${pkg.icon}" style="font-size: 3rem; color: var(--${pkg.color});"></i>
                            </div>

                            <!-- Package Name -->
                            <h4 style="text-align: center; color: var(--text-primary); margin-bottom: var(--space-2); font-weight: var(--font-bold);">
                                ${pkg.name}
                            </h4>

                            <!-- Description -->
                            <p style="text-align: center; color: var(--text-secondary); font-size: var(--text-sm); margin-bottom: var(--space-4);">
                                ${pkg.description}
                            </p>

                            <!-- GEM Amount -->
                            <div style="text-align: center; margin-bottom: var(--space-4); flex: 1;">
                                <div style="font-size: var(--text-3xl); font-weight: var(--font-bold); color: var(--gem); margin-bottom: var(--space-2);">
                                    ${this.formatNumber(pkg.total_gems)}
                                    <small style="font-size: var(--text-base); color: var(--text-muted);">GEM</small>
                                </div>
                                ${pkg.bonus_gems > 0 ? `
                                    <div style="color: var(--success); font-size: var(--text-sm);">
                                        <i class="bi bi-plus-circle"></i> ${this.formatNumber(pkg.bonus_gems)} Bonus GEM
                                    </div>
                                ` : ''}
                            </div>

                            <!-- Price -->
                            <div style="text-align: center; margin-bottom: var(--space-4);">
                                <div style="font-size: var(--text-2xl); font-weight: var(--font-bold); color: var(--text-primary);">
                                    $${pkg.price_usd.toFixed(2)}
                                    <small style="font-size: var(--text-sm); color: var(--text-muted);">USD</small>
                                </div>
                            </div>

                            <!-- Purchase Button -->
                            <button class="btn-modern btn-modern-${pkg.color} w-100" onclick="GemStore.showPurchaseModal('${pkg.id}')">
                                <i class="bi bi-cart-plus"></i> Purchase
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });

        grid.innerHTML = html;
    }

    showPurchaseModal(packageId) {
        const pkg = this.packages.find(p => p.id === packageId);
        if (!pkg) return;

        this.selectedPackage = pkg;

        // Fill modal with package details
        document.getElementById('modal-package-name').textContent = pkg.name;
        document.getElementById('modal-package-description').textContent = pkg.description;
        document.getElementById('modal-base-gems').textContent = this.formatNumber(pkg.gems) + ' GEM';
        document.getElementById('modal-bonus-gems').textContent = pkg.bonus_gems > 0 ?
            this.formatNumber(pkg.bonus_gems) + ' GEM' : 'None';
        document.getElementById('modal-total-gems').textContent = this.formatNumber(pkg.total_gems) + ' GEM';
        document.getElementById('modal-price').textContent = '$' + pkg.price_usd.toFixed(2) + ' USD';

        this.purchaseModal.show();
    }

    async completePurchase() {
        if (!this.selectedPackage) return;

        const confirmBtn = document.getElementById('confirm-purchase-btn');
        const originalText = confirmBtn.innerHTML;

        try {
            // Disable button
            confirmBtn.disabled = true;
            confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';

            const token = localStorage.getItem('token');
            if (!token) {
                throw new Error('Please log in to make a purchase');
            }

            const paymentMethod = document.getElementById('payment-method').value;

            const response = await fetch('/api/gem-store/purchase', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    package_id: this.selectedPackage.id,
                    payment_method: paymentMethod
                })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Purchase failed');
            }

            // Hide purchase modal
            this.purchaseModal.hide();

            // Show success modal
            document.getElementById('success-gems').textContent = this.formatNumber(result.total_gems);
            document.getElementById('success-transaction-id').textContent = result.transaction_id;
            document.getElementById('success-new-balance').textContent = this.formatNumber(result.new_balance) + ' GEM';

            this.successModal.show();

            // Refresh data
            await this.loadBalance();
            await this.loadPurchaseHistory();

        } catch (error) {
            console.error('Purchase error:', error);
            alert('Purchase failed: ' + error.message);
        } finally {
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = originalText;
        }
    }

    async loadPurchaseHistory() {
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                document.getElementById('purchase-history').innerHTML = `
                    <p style="color: var(--text-muted); text-align: center;">Login to view purchase history</p>
                `;
                return;
            }

            const response = await fetch('/api/gem-store/purchase-history', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            const result = await response.json();
            this.renderPurchaseHistory(result);
        } catch (error) {
            console.error('Error loading purchase history:', error);
            document.getElementById('purchase-history').innerHTML = `
                <p style="color: var(--error); text-align: center;">Failed to load purchase history</p>
            `;
        }
    }

    renderPurchaseHistory(data) {
        const container = document.getElementById('purchase-history');

        if (data.purchases.length === 0) {
            container.innerHTML = `
                <p style="color: var(--text-muted); text-align: center;">No purchases yet. Buy your first GEM package above!</p>
            `;
            return;
        }

        let html = `
            <div style="margin-bottom: var(--space-4);">
                <div class="row">
                    <div class="col-md-4">
                        <div class="stat-card-modern">
                            <div class="stat-label">Total Purchases</div>
                            <div class="stat-value">${data.total_purchased}</div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="stat-card-modern">
                            <div class="stat-label">Total Spent</div>
                            <div class="stat-value">$${data.total_spent.toFixed(2)}</div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="stat-card-modern">
                            <div class="stat-label">Average Purchase</div>
                            <div class="stat-value">$${(data.total_spent / data.total_purchased).toFixed(2)}</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="table-responsive">
                <table class="table-modern">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Package</th>
                            <th>GEM Received</th>
                            <th>Price</th>
                            <th>Payment Method</th>
                            <th>Transaction ID</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        data.purchases.forEach(purchase => {
            const date = new Date(purchase.created_at);
            html += `
                <tr>
                    <td>${date.toLocaleDateString()} ${date.toLocaleTimeString()}</td>
                    <td><strong>${purchase.package_name}</strong></td>
                    <td>
                        <span style="color: var(--gem);">
                            <i class="bi bi-gem"></i> ${this.formatNumber(purchase.total_gems)}
                        </span>
                        ${purchase.bonus_gems > 0 ? `<small style="color: var(--success);"> (+${this.formatNumber(purchase.bonus_gems)})</small>` : ''}
                    </td>
                    <td><strong>$${purchase.price_usd.toFixed(2)}</strong></td>
                    <td>${this.formatPaymentMethod(purchase.payment_method)}</td>
                    <td><code style="font-size: var(--text-xs);">${purchase.transaction_id}</code></td>
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

    formatPaymentMethod(method) {
        const methods = {
            'demo_card': '💳 Demo Card',
            'demo_crypto': '₿ Demo Crypto',
            'demo_paypal': '💰 Demo PayPal'
        };
        return methods[method] || method;
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(2) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(2) + 'K';
        }
        return num.toLocaleString();
    }

    async refreshHistory() {
        await this.loadPurchaseHistory();
    }
}

// Initialize when DOM is ready
let GemStore;
document.addEventListener('DOMContentLoaded', () => {
    GemStore = new GemStoreManager();
});
