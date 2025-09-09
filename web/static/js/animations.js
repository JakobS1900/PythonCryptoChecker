/**
 * Advanced Animations and Micro-interactions for Crypto Gaming Platform
 * Provides smooth, engaging visual feedback for user interactions
 */

class AnimationManager {
    constructor() {
        this.observers = new Map();
        this.particles = [];
        this.init();
    }

    init() {
        this.setupIntersectionObserver();
        this.setupParticleSystem();
        this.setupHoverEffects();
        this.setupClickEffects();
    }

    // ===== INTERSECTION OBSERVER FOR SCROLL ANIMATIONS =====
    setupIntersectionObserver() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.animateElement(entry.target);
                }
            });
        }, observerOptions);

        // Observe elements with animation classes
        document.querySelectorAll('.animate-on-scroll').forEach(el => {
            observer.observe(el);
        });

        this.observers.set('scroll', observer);
    }

    animateElement(element) {
        const animationType = element.dataset.animation || 'fadeInUp';
        const delay = element.dataset.delay || 0;

        setTimeout(() => {
            element.classList.add('animated', animationType);
        }, delay);
    }

    // ===== PARTICLE SYSTEM =====
    setupParticleSystem() {
        this.createParticleContainer();
        this.startParticleAnimation();
    }

    createParticleContainer() {
        if (document.querySelector('.particles-container')) return;

        const container = document.createElement('div');
        container.className = 'particles-container';
        document.body.appendChild(container);

        // Create initial particles
        for (let i = 0; i < 50; i++) {
            this.createParticle(container);
        }
    }

    createParticle(container) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        
        // Random positioning and properties
        particle.style.left = Math.random() * 100 + '%';
        particle.style.top = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 6 + 's';
        particle.style.animationDuration = (Math.random() * 3 + 3) + 's';
        
        // Random colors
        const colors = ['#00ffff', '#ff00ff', '#39ff14', '#ff6600'];
        particle.style.background = colors[Math.floor(Math.random() * colors.length)];
        
        container.appendChild(particle);
        this.particles.push(particle);
    }

    startParticleAnimation() {
        setInterval(() => {
            this.particles.forEach(particle => {
                if (Math.random() < 0.01) { // 1% chance per frame
                    this.animateParticle(particle);
                }
            });
        }, 100);
    }

    animateParticle(particle) {
        particle.style.transform = `translateY(${Math.random() * 20 - 10}px) scale(${Math.random() * 0.5 + 0.5})`;
        setTimeout(() => {
            particle.style.transform = '';
        }, 1000);
    }

    // ===== HOVER EFFECTS =====
    setupHoverEffects() {
        // Card hover effects
        document.addEventListener('mouseover', (e) => {
            if (e.target.closest('.card, .bet-option, .achievement-card')) {
                this.addHoverEffect(e.target.closest('.card, .bet-option, .achievement-card'));
            }
        });

        document.addEventListener('mouseout', (e) => {
            if (e.target.closest('.card, .bet-option, .achievement-card')) {
                this.removeHoverEffect(e.target.closest('.card, .bet-option, .achievement-card'));
            }
        });

        // Button hover effects
        document.addEventListener('mouseover', (e) => {
            if (e.target.matches('.btn')) {
                this.addButtonHoverEffect(e.target);
            }
        });
    }

    addHoverEffect(element) {
        element.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        element.style.transform = 'translateY(-8px) scale(1.02)';
        element.style.boxShadow = '0 20px 40px rgba(0, 0, 0, 0.15)';
    }

    removeHoverEffect(element) {
        element.style.transform = '';
        element.style.boxShadow = '';
    }

    addButtonHoverEffect(button) {
        if (!button.querySelector('.hover-ripple')) {
            const ripple = document.createElement('span');
            ripple.className = 'hover-ripple';
            button.appendChild(ripple);
        }
    }

    // ===== CLICK EFFECTS =====
    setupClickEffects() {
        document.addEventListener('click', (e) => {
            if (e.target.matches('.btn, .bet-option, .crypto-icon')) {
                this.createRippleEffect(e);
            }
        });
    }

    createRippleEffect(event) {
        const button = event.target;
        const rect = button.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;

        const ripple = document.createElement('span');
        ripple.className = 'click-ripple';
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';

        button.style.position = 'relative';
        button.style.overflow = 'hidden';
        button.appendChild(ripple);

        setTimeout(() => {
            ripple.remove();
        }, 600);
    }

    // ===== ROULETTE WHEEL ANIMATIONS =====
    animateRouletteWheel(targetNumber, duration = 3000) {
        const wheel = document.querySelector('.roulette-wheel');
        if (!wheel) return;

        const positions = 37; // 0-36
        const degreesPerPosition = 360 / positions;
        const targetAngle = 360 - (degreesPerPosition * targetNumber);
        const totalRotation = 1440 + targetAngle; // 4 full spins + target

        wheel.style.transition = `transform ${duration}ms cubic-bezier(0.23, 1, 0.320, 1)`;
        wheel.style.transform = `rotate(${totalRotation}deg)`;

        // Add spinning effects
        this.addSpinningEffects(wheel, duration);

        return new Promise(resolve => {
            setTimeout(() => {
                this.removeSpinningEffects(wheel);
                resolve();
            }, duration);
        });
    }

    addSpinningEffects(wheel, duration) {
        wheel.classList.add('spinning');
        
        // Add blur effect during spin
        wheel.style.filter = 'blur(2px)';
        
        // Add glow effect
        wheel.style.boxShadow = '0 0 50px rgba(247, 147, 26, 0.8)';
        
        // Gradually reduce blur
        setTimeout(() => {
            wheel.style.filter = 'blur(1px)';
        }, duration * 0.7);
        
        setTimeout(() => {
            wheel.style.filter = '';
        }, duration * 0.9);
    }

    removeSpinningEffects(wheel) {
        wheel.classList.remove('spinning');
        wheel.style.filter = '';
        wheel.style.boxShadow = '';
    }

    // ===== ACHIEVEMENT UNLOCK ANIMATION =====
    animateAchievementUnlock(achievementData) {
        const modal = this.createAchievementModal(achievementData);
        document.body.appendChild(modal);

        // Animate modal entrance
        setTimeout(() => {
            modal.classList.add('show');
        }, 100);

        // Auto-hide after 5 seconds
        setTimeout(() => {
            this.hideAchievementModal(modal);
        }, 5000);

        // Add confetti effect
        this.createConfettiEffect();
    }

    createAchievementModal(data) {
        const modal = document.createElement('div');
        modal.className = 'achievement-unlock-modal';
        modal.innerHTML = `
            <div class="achievement-unlock-content">
                <div class="achievement-unlock-icon">🏆</div>
                <h3>Achievement Unlocked!</h3>
                <h4>${data.name}</h4>
                <p>${data.description}</p>
                <div class="achievement-unlock-reward">
                    +${data.xp_reward} XP • +${data.gem_reward} GEM
                </div>
            </div>
        `;

        return modal;
    }

    hideAchievementModal(modal) {
        modal.classList.add('hide');
        setTimeout(() => {
            modal.remove();
        }, 500);
    }

    createConfettiEffect() {
        const colors = ['#f43f5e', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b'];
        const confettiCount = 50;

        for (let i = 0; i < confettiCount; i++) {
            setTimeout(() => {
                this.createConfettiPiece(colors[Math.floor(Math.random() * colors.length)]);
            }, i * 50);
        }
    }

    createConfettiPiece(color) {
        const confetti = document.createElement('div');
        confetti.className = 'confetti-piece';
        confetti.style.background = color;
        confetti.style.left = Math.random() * 100 + '%';
        confetti.style.animationDelay = Math.random() * 2 + 's';
        
        document.body.appendChild(confetti);

        setTimeout(() => {
            confetti.remove();
        }, 3000);
    }

    // ===== LOADING ANIMATIONS =====
    showLoadingAnimation(container, type = 'spinner') {
        const loader = document.createElement('div');
        loader.className = `loading-animation loading-${type}`;
        
        switch (type) {
            case 'spinner':
                loader.innerHTML = '<div class="spinner"></div>';
                break;
            case 'dots':
                loader.innerHTML = '<div class="dots"><span></span><span></span><span></span></div>';
                break;
            case 'pulse':
                loader.innerHTML = '<div class="pulse"></div>';
                break;
        }

        container.appendChild(loader);
        return loader;
    }

    hideLoadingAnimation(loader) {
        if (loader && loader.parentNode) {
            loader.classList.add('fade-out');
            setTimeout(() => {
                loader.remove();
            }, 300);
        }
    }

    // ===== NOTIFICATION ANIMATIONS =====
    animateNotification(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="notification-icon fas fa-${this.getNotificationIcon(type)}"></i>
                <span class="notification-message">${message}</span>
                <button class="notification-close">&times;</button>
            </div>
        `;

        const container = document.querySelector('.notification-container') || this.createNotificationContainer();
        container.appendChild(notification);

        // Animate entrance
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);

        // Auto-hide
        setTimeout(() => {
            this.hideNotification(notification);
        }, duration);

        // Close button
        notification.querySelector('.notification-close').addEventListener('click', () => {
            this.hideNotification(notification);
        });
    }

    createNotificationContainer() {
        const container = document.createElement('div');
        container.className = 'notification-container';
        document.body.appendChild(container);
        return container;
    }

    hideNotification(notification) {
        notification.classList.add('hide');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }

    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-triangle',
            warning: 'exclamation-circle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    // ===== UTILITY METHODS =====
    fadeIn(element, duration = 300) {
        element.style.opacity = '0';
        element.style.transition = `opacity ${duration}ms ease`;
        
        setTimeout(() => {
            element.style.opacity = '1';
        }, 10);
    }

    fadeOut(element, duration = 300) {
        element.style.transition = `opacity ${duration}ms ease`;
        element.style.opacity = '0';
        
        return new Promise(resolve => {
            setTimeout(() => {
                resolve();
            }, duration);
        });
    }

    slideIn(element, direction = 'up', duration = 300) {
        const transforms = {
            up: 'translateY(20px)',
            down: 'translateY(-20px)',
            left: 'translateX(20px)',
            right: 'translateX(-20px)'
        };

        element.style.transform = transforms[direction];
        element.style.opacity = '0';
        element.style.transition = `all ${duration}ms cubic-bezier(0.4, 0, 0.2, 1)`;

        setTimeout(() => {
            element.style.transform = '';
            element.style.opacity = '1';
        }, 10);
    }

    // ===== CLEANUP =====
    destroy() {
        this.observers.forEach(observer => observer.disconnect());
        this.particles.forEach(particle => particle.remove());
        
        const particleContainer = document.querySelector('.particles-container');
        if (particleContainer) {
            particleContainer.remove();
        }
    }
}

// ===== CSS FOR ANIMATIONS =====
const animationStyles = `
<style>
/* Click Ripple Effect */
.click-ripple {
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.3);
    transform: scale(0);
    animation: ripple 0.6s linear;
    pointer-events: none;
}

@keyframes ripple {
    to {
        transform: scale(4);
        opacity: 0;
    }
}

/* Achievement Unlock Modal */
.achievement-unlock-modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    opacity: 0;
    transform: scale(0.8);
    transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.achievement-unlock-modal.show {
    opacity: 1;
    transform: scale(1);
}

.achievement-unlock-modal.hide {
    opacity: 0;
    transform: scale(0.8);
}

.achievement-unlock-content {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 3rem;
    border-radius: 20px;
    text-align: center;
    color: white;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
    max-width: 400px;
}

.achievement-unlock-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
    animation: bounce 1s ease-in-out infinite alternate;
}

.achievement-unlock-reward {
    margin-top: 1rem;
    padding: 0.5rem 1rem;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 10px;
    font-weight: bold;
}

/* Confetti Animation */
.confetti-piece {
    position: fixed;
    width: 10px;
    height: 10px;
    top: -10px;
    z-index: 9999;
    animation: confetti-fall 3s linear forwards;
}

@keyframes confetti-fall {
    0% {
        transform: translateY(-100vh) rotate(0deg);
        opacity: 1;
    }
    100% {
        transform: translateY(100vh) rotate(720deg);
        opacity: 0;
    }
}

/* Loading Animations */
.loading-animation {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
}

.loading-spinner .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid rgba(79, 70, 229, 0.2);
    border-top: 4px solid #4f46e5;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

.loading-dots .dots {
    display: flex;
    gap: 0.5rem;
}

.loading-dots .dots span {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #4f46e5;
    animation: dot-bounce 1.4s ease-in-out infinite both;
}

.loading-dots .dots span:nth-child(1) { animation-delay: -0.32s; }
.loading-dots .dots span:nth-child(2) { animation-delay: -0.16s; }

@keyframes dot-bounce {
    0%, 80%, 100% {
        transform: scale(0);
    }
    40% {
        transform: scale(1);
    }
}

.loading-pulse .pulse {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: #4f46e5;
    animation: pulse-scale 1.5s ease-in-out infinite;
}

@keyframes pulse-scale {
    0%, 100% {
        transform: scale(1);
        opacity: 1;
    }
    50% {
        transform: scale(1.2);
        opacity: 0.7;
    }
}

/* Notification Styles */
.notification-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 9999;
    max-width: 400px;
}

.notification {
    background: white;
    border-radius: 10px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    margin-bottom: 1rem;
    transform: translateX(100%);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    opacity: 0;
}

.notification.show {
    transform: translateX(0);
    opacity: 1;
}

.notification.hide {
    transform: translateX(100%);
    opacity: 0;
}

.notification-content {
    display: flex;
    align-items: center;
    padding: 1rem;
}

.notification-icon {
    margin-right: 1rem;
    font-size: 1.2rem;
}

.notification-success { border-left: 4px solid #22c55e; }
.notification-success .notification-icon { color: #22c55e; }

.notification-error { border-left: 4px solid #ef4444; }
.notification-error .notification-icon { color: #ef4444; }

.notification-warning { border-left: 4px solid #f59e0b; }
.notification-warning .notification-icon { color: #f59e0b; }

.notification-info { border-left: 4px solid #3b82f6; }
.notification-info .notification-icon { color: #3b82f6; }

.notification-message {
    flex: 1;
    font-weight: 500;
}

.notification-close {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: #6b7280;
    padding: 0;
    margin-left: 1rem;
}

.notification-close:hover {
    color: #374151;
}

/* Scroll Animations */
.animate-on-scroll {
    opacity: 0;
    transform: translateY(30px);
    transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.animate-on-scroll.animated {
    opacity: 1;
    transform: translateY(0);
}

.fade-out {
    opacity: 0 !important;
    transition: opacity 0.3s ease;
}
</style>
`;

// Inject styles
document.head.insertAdjacentHTML('beforeend', animationStyles);

// Initialize animation manager
window.animationManager = new AnimationManager();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AnimationManager;
}