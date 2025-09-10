/**
 * Main JavaScript functionality for Crypto Gamification Platform
 * Handles global utilities, UI components, and common functionality
 */

// ===== GLOBAL UTILITIES =====
// Note: Utils are now loaded from utils.js - commenting out duplicate

/*window.utils = {
    // Format numbers with appropriate suffixes
    formatNumber: (num) => {
        if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B';
        if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M';
        if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K';
        return num.toString();
    },

    // Format currency with symbol
    formatCurrency: (amount, currency = 'GEM') => {
        const symbols = {
            'GEM': '💎',
            'BTC': '₿',
            'ETH': 'Ξ',
            'USD': '$'
        };
        return `${symbols[currency] || currency} ${window.utils.formatNumber(amount)}`;
    },

    // Format date/time
    formatDate: (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    },

    // Format relative time (e.g., "2 hours ago")
    formatRelativeTime: (dateString) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) return 'Just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
        if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)}d ago`;
        return date.toLocaleDateString();
    },

    // Debounce function for search inputs
    debounce: (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Copy text to clipboard
    copyToClipboard: async (text) => {
        try {
            await navigator.clipboard.writeText(text);
            window.showAlert('Copied to clipboard!', 'success');
        } catch (err) {
            console.error('Failed to copy:', err);
            window.showAlert('Failed to copy to clipboard', 'warning');
        }
    },

    // Generate random ID
    generateId: () => {
        return Math.random().toString(36).substr(2, 9);
    }
};*/

// ===== ALERT SYSTEM =====

window.showAlert = (message, type = 'info', duration = 5000) => {
    const alertContainer = document.getElementById('alertContainer');
    if (!alertContainer) return;

    const alertId = 'alert-' + Date.now();
    const alertHTML = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            <div class="d-flex align-items-center">
                <i class="fas fa-${getAlertIcon(type)} me-2"></i>
                <div class="flex-grow-1">${message}</div>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        </div>
    `;

    alertContainer.insertAdjacentHTML('beforeend', alertHTML);

    // Auto-dismiss after duration
    if (duration > 0) {
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, duration);
    }

    function getAlertIcon(type) {
        const icons = {
            'success': 'check-circle',
            'danger': 'exclamation-triangle',
            'warning': 'exclamation-circle',
            'info': 'info-circle',
            'primary': 'bell'
        };
        return icons[type] || 'info-circle';
    }
};

// ===== LOADING STATES =====

window.showLoading = (target, text = 'Loading...') => {
    const element = typeof target === 'string' ? document.getElementById(target) : target;
    if (!element) return;

    const loadingHTML = `
        <div class="loading-overlay d-flex align-items-center justify-content-center">
            <div class="text-center">
                <div class="spinner-border text-primary mb-3" role="status"></div>
                <div class="fw-semibold">${text}</div>
            </div>
        </div>
    `;

    element.style.position = 'relative';
    element.insertAdjacentHTML('beforeend', loadingHTML);
};

window.hideLoading = (target) => {
    const element = typeof target === 'string' ? document.getElementById(target) : target;
    if (!element) return;

    const overlay = element.querySelector('.loading-overlay');
    if (overlay) {
        overlay.remove();
    }
};

// ===== MODAL UTILITIES =====

window.showModal = (title, content, actions = []) => {
    const modalId = 'modal-' + Date.now();
    const actionsHTML = actions.map(action => 
        `<button type="button" class="btn btn-${action.type || 'secondary'}" 
                 onclick="${action.onclick || ''}" 
                 ${action.dismiss ? 'data-bs-dismiss="modal"' : ''}>
            ${action.text}
         </button>`
    ).join('');

    const modalHTML = `
        <div class="modal fade" id="${modalId}" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${title}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">${content}</div>
                    <div class="modal-footer">
                        ${actionsHTML}
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    const modal = new bootstrap.Modal(document.getElementById(modalId));
    modal.show();

    // Clean up modal after it's hidden
    document.getElementById(modalId).addEventListener('hidden.bs.modal', () => {
        document.getElementById(modalId).remove();
    });

    return modal;
};

// ===== FORM VALIDATION =====

window.formValidator = {
    validate: (form) => {
        const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
        let isValid = true;

        inputs.forEach(input => {
            if (!window.formValidator.validateField(input)) {
                isValid = false;
            }
        });

        return isValid;
    },

    validateField: (field) => {
        const value = field.value.trim();
        let isValid = true;
        let message = '';

        // Clear previous validation
        field.classList.remove('is-invalid');
        const feedback = field.parentNode.querySelector('.invalid-feedback');
        if (feedback) feedback.textContent = '';

        // Required validation
        if (field.hasAttribute('required') && !value) {
            message = `${field.name || 'This field'} is required`;
            isValid = false;
        }

        // Type-specific validation
        if (isValid && value) {
            switch (field.type) {
                case 'email':
                    if (!window.formValidator.isValidEmail(value)) {
                        message = 'Please enter a valid email address';
                        isValid = false;
                    }
                    break;
                
                case 'password':
                    const minLength = parseInt(field.getAttribute('minlength')) || 8;
                    if (value.length < minLength) {
                        message = `Password must be at least ${minLength} characters`;
                        isValid = false;
                    }
                    break;
                
                case 'number':
                    const min = parseFloat(field.getAttribute('min'));
                    const max = parseFloat(field.getAttribute('max'));
                    const numValue = parseFloat(value);
                    
                    if (isNaN(numValue)) {
                        message = 'Please enter a valid number';
                        isValid = false;
                    } else if (!isNaN(min) && numValue < min) {
                        message = `Value must be at least ${min}`;
                        isValid = false;
                    } else if (!isNaN(max) && numValue > max) {
                        message = `Value must be at most ${max}`;
                        isValid = false;
                    }
                    break;
            }
        }

        // Show validation result
        if (!isValid) {
            field.classList.add('is-invalid');
            if (feedback) feedback.textContent = message;
        }

        return isValid;
    },

    isValidEmail: (email) => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
};

// ===== WEBSOCKET CONNECTION (for real-time features) =====

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.listeners = new Map();
    }

    connect() {
        if (!window.auth.isAuthenticated()) return;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                
                // Send auth token
                this.send('authenticate', {
                    token: localStorage.getItem('access_token')
                });
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.attemptReconnect();
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    send(type, data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type, data }));
        }
    }

    handleMessage(message) {
        const { type, data } = message;
        const listeners = this.listeners.get(type) || [];
        
        listeners.forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error('WebSocket listener error:', error);
            }
        });
    }

    on(type, callback) {
        if (!this.listeners.has(type)) {
            this.listeners.set(type, []);
        }
        this.listeners.get(type).push(callback);
    }

    off(type, callback) {
        const listeners = this.listeners.get(type);
        if (listeners) {
            const index = listeners.indexOf(callback);
            if (index !== -1) {
                listeners.splice(index, 1);
            }
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            setTimeout(() => {
                this.connect();
            }, this.reconnectDelay * this.reconnectAttempts);
        }
    }
}

// ===== INITIALIZATION =====

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl));

    // Initialize WebSocket for authenticated users (disabled for demo)
    setTimeout(() => {
        if (window.auth && window.auth.isAuthenticated()) {
            console.log('WebSocket disabled for demo mode');
            // window.wsManager = new WebSocketManager();
            // window.wsManager.connect();

            // Listen for real-time updates (only if wsManager exists)
            if (window.wsManager) {
                window.wsManager.on('notification', (data) => {
                    window.showAlert(data.message, data.type || 'info');
                });

                window.wsManager.on('friend_request', (data) => {
                    window.showAlert(`Friend request from ${data.username}`, 'info');
                    // Update friend requests UI if visible
                    if (typeof updateFriendRequests === 'function') {
                        updateFriendRequests();
                    }
                });

                window.wsManager.on('achievement_unlocked', (data) => {
                    window.showAlert(`🏆 Achievement unlocked: ${data.name}!`, 'success', 10000);
                });
            } else {
                console.log('WebSocket manager not initialized - real-time features disabled');
            }
        }
    }, 1000);

    // Global error handler
    window.addEventListener('error', (event) => {
        console.error('Global error:', event.error);
        // Don't show alerts for network errors or script errors
        if (!event.error?.message?.includes('NetworkError') && 
            !event.error?.message?.includes('Script error')) {
            window.showAlert('An unexpected error occurred', 'danger');
        }
    });

    // Handle offline/online status
    window.addEventListener('online', () => {
        window.showAlert('Connection restored', 'success');
        if (window.wsManager) {
            window.wsManager.connect();
        }
    });

    window.addEventListener('offline', () => {
        window.showAlert('Connection lost. Some features may not work.', 'warning');
    });
});

// ===== PERFORMANCE OPTIMIZATION =====

// Lazy loading for images
const lazyImageObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
        if (entry.isIntersecting) {
            const img = entry.target;
            img.src = img.dataset.src;
            img.classList.remove('lazy');
            lazyImageObserver.unobserve(img);
        }
    });
});

// Apply lazy loading to images with data-src
document.addEventListener('DOMContentLoaded', () => {
    const lazyImages = document.querySelectorAll('img[data-src]');
    lazyImages.forEach((img) => {
        lazyImageObserver.observe(img);
    });
});

// ===== EXPORT FOR MODULES =====

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        utils: window.utils,
        showAlert: window.showAlert,
        showModal: window.showModal,
        formValidator: window.formValidator,
        WebSocketManager
    };
}