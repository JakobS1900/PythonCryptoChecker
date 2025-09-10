// Utility functions for the CryptoChecker platform

window.utils = {
    /**
     * Format a number with commas for thousands separator
     * @param {number} num - The number to format
     * @returns {string} - Formatted number string
     */
    formatNumber: function(num) {
        if (typeof num !== 'number') {
            num = parseFloat(num) || 0;
        }
        return num.toLocaleString();
    },

    /**
     * Format currency with symbol
     * @param {number} amount - The amount to format
     * @param {string} symbol - Currency symbol (default: 'GEM')
     * @returns {string} - Formatted currency string
     */
    formatCurrency: function(amount, symbol = 'GEM') {
        return `${this.formatNumber(amount)} ${symbol}`;
    },

    /**
     * Format relative time (e.g., "2 minutes ago")
     * @param {string|Date} timestamp - The timestamp to format
     * @returns {string} - Relative time string
     */
    formatRelativeTime: function(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diffMs = now - time;
        const diffSecs = Math.floor(diffMs / 1000);
        const diffMins = Math.floor(diffSecs / 60);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffSecs < 60) {
            return 'Just now';
        } else if (diffMins < 60) {
            return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
        } else if (diffHours < 24) {
            return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
        } else {
            return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
        }
    },

    /**
     * Debounce function to limit function calls
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in milliseconds
     * @returns {Function} - Debounced function
     */
    debounce: function(func, wait) {
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

    /**
     * Generate a random ID
     * @param {number} length - Length of the ID (default: 8)
     * @returns {string} - Random ID string
     */
    generateId: function(length = 8) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let result = '';
        for (let i = 0; i < length; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
    },

    /**
     * Validate email format
     * @param {string} email - Email to validate
     * @returns {boolean} - True if valid email
     */
    isValidEmail: function(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    /**
     * Copy text to clipboard
     * @param {string} text - Text to copy
     * @returns {Promise<boolean>} - True if successful
     */
    copyToClipboard: async function(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            return true;
        }
    },

    /**
     * Get query parameter from URL
     * @param {string} param - Parameter name
     * @returns {string|null} - Parameter value or null
     */
    getUrlParameter: function(param) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(param);
    },

    /**
     * Format file size
     * @param {number} bytes - File size in bytes
     * @returns {string} - Formatted file size
     */
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    /**
     * Check if device is mobile
     * @returns {boolean} - True if mobile device
     */
    isMobile: function() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    },

    /**
     * Smooth scroll to element
     * @param {string|Element} target - Element or selector to scroll to
     * @param {number} offset - Offset from top (default: 0)
     */
    scrollTo: function(target, offset = 0) {
        const element = typeof target === 'string' ? document.querySelector(target) : target;
        if (element) {
            const elementPosition = element.getBoundingClientRect().top;
            const offsetPosition = elementPosition + window.pageYOffset - offset;
            
            window.scrollTo({
                top: offsetPosition,
                behavior: 'smooth'
            });
        }
    },

    /**
     * Show alert notification
     * @param {string} message - Alert message
     * @param {string} type - Alert type (success, error, warning, info)
     * @param {number} duration - Duration in milliseconds
     */
    showAlert: function(message, type = 'info', duration = 5000) {
        console.log(`🚨 Alert (${type}): ${message} - BUNGA MUNGA!`);
        
        // Create alert element
        const alertContainer = document.getElementById('alertContainer') || document.body;
        const alertId = 'alert-' + Date.now();
        
        const alertClass = type === 'error' ? 'danger' : type;
        const iconMap = {
            'success': 'check-circle',
            'error': 'exclamation-triangle', 
            'warning': 'exclamation-circle',
            'info': 'info-circle'
        };
        
        const alertHtml = `
            <div id="${alertId}" class="alert alert-${alertClass} alert-dismissible fade show" role="alert">
                <i class="fas fa-${iconMap[type] || 'info-circle'} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        alertContainer.insertAdjacentHTML('afterbegin', alertHtml);
        
        // Auto-remove after duration
        setTimeout(() => {
            const alertElement = document.getElementById(alertId);
            if (alertElement) {
                alertElement.remove();
            }
        }, duration);
    },

    /**
     * Show loading spinner in element
     * @param {string} elementId - ID of element to show loading in
     */
    showLoading: function(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div class="text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <div class="mt-2 text-muted">Loading...</div>
                </div>
            `;
        }
    },

    /**
     * Hide loading spinner from element
     * @param {string} elementId - ID of element to hide loading from
     */
    hideLoading: function(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            const loadingElement = element.querySelector('.spinner-border');
            if (loadingElement) {
                loadingElement.closest('.text-center').remove();
            }
        }
    }
};

// Make showAlert available globally (expected by auth system)
window.showAlert = window.utils.showAlert;

// Initialize utils when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Utils initialized - BUNGA MUNGA MUNGA!');
});