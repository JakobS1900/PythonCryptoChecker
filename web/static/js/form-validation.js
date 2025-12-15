/**
 * Real-Time Form Validation Module
 * Provides inline validation with immediate feedback
 */

class FormValidator {
    constructor(formElement, options = {}) {
        this.form = formElement;
        this.options = {
            validateOnBlur: true,
            validateOnInput: true,
            showSuccessIcons: true,
            ...options
        };
        this.init();
    }

    init() {
        if (!this.form) return;

        // Add validation to all inputs
        const inputs = this.form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            if (this.options.validateOnBlur) {
                input.addEventListener('blur', () => this.validateField(input));
            }
            if (this.options.validateOnInput) {
                input.addEventListener('input', () => {
                    // Only validate on input if field was already validated
                    if (input.classList.contains('is-valid') || input.classList.contains('is-invalid')) {
                        this.validateField(input);
                    }
                });
            }
        });

        // Validate on form submit
        this.form.addEventListener('submit', (e) => {
            if (!this.validateForm()) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    }

    validateField(input) {
        // Clear previous validation
        input.classList.remove('is-valid', 'is-invalid');
        this.clearFieldError(input);

        // Check if field is required and empty
        if (input.hasAttribute('required') && !input.value.trim()) {
            this.setFieldError(input, 'This field is required');
            return false;
        }

        // Skip validation if field is empty and not required
        if (!input.value.trim() && !input.hasAttribute('required')) {
            return true;
        }

        // Email validation
        if (input.type === 'email') {
            if (!this.validateEmail(input.value)) {
                this.setFieldError(input, 'Please enter a valid email address');
                return false;
            }
        }

        // URL validation
        if (input.type === 'url') {
            if (!this.validateURL(input.value)) {
                this.setFieldError(input, 'Please enter a valid URL');
                return false;
            }
        }

        // Min length validation
        if (input.hasAttribute('minlength')) {
            const minLength = parseInt(input.getAttribute('minlength'));
            if (input.value.length < minLength) {
                this.setFieldError(input, `Must be at least ${minLength} characters`);
                return false;
            }
        }

        // Max length validation
        if (input.hasAttribute('maxlength')) {
            const maxLength = parseInt(input.getAttribute('maxlength'));
            if (input.value.length > maxLength) {
                this.setFieldError(input, `Must be no more than ${maxLength} characters`);
                return false;
            }
        }

        // Pattern validation
        if (input.hasAttribute('pattern')) {
            const pattern = new RegExp(input.getAttribute('pattern'));
            if (!pattern.test(input.value)) {
                const patternMsg = input.getAttribute('data-pattern-message') || 'Invalid format';
                this.setFieldError(input, patternMsg);
                return false;
            }
        }

        // Password confirmation
        if (input.name === 'confirmPassword' || input.id.includes('Confirm')) {
            const passwordField = this.form.querySelector('[name="password"], [id*="Password"]:not([id*="Confirm"])');
            if (passwordField && input.value !== passwordField.value) {
                this.setFieldError(input, 'Passwords do not match');
                return false;
            }
        }

        // Field is valid
        this.setFieldSuccess(input);
        return true;
    }

    validateForm() {
        let isValid = true;
        const inputs = this.form.querySelectorAll('input, textarea, select');

        inputs.forEach(input => {
            if (!this.validateField(input)) {
                isValid = false;
            }
        });

        // Focus first invalid field
        if (!isValid) {
            const firstInvalid = this.form.querySelector('.is-invalid');
            if (firstInvalid) {
                firstInvalid.focus();
            }
        }

        return isValid;
    }

    setFieldError(input, message) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');

        // Create or update error message
        let feedback = input.parentElement.querySelector('.invalid-feedback');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            input.parentElement.appendChild(feedback);
        }
        feedback.textContent = message;
        feedback.style.display = 'block';
    }

    setFieldSuccess(input) {
        input.classList.add('is-valid');
        input.classList.remove('is-invalid');
        this.clearFieldError(input);

        // Add success message if configured
        if (this.options.showSuccessIcons) {
            let feedback = input.parentElement.querySelector('.valid-feedback');
            if (!feedback) {
                feedback = document.createElement('div');
                feedback.className = 'valid-feedback';
                input.parentElement.appendChild(feedback);
            }
            feedback.textContent = '✓';
            feedback.style.display = 'block';
        }
    }

    clearFieldError(input) {
        const invalidFeedback = input.parentElement.querySelector('.invalid-feedback');
        if (invalidFeedback) {
            invalidFeedback.style.display = 'none';
        }
        const validFeedback = input.parentElement.querySelector('.valid-feedback');
        if (validFeedback) {
            validFeedback.style.display = 'none';
        }
    }

    validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }

    validateURL(url) {
        try {
            new URL(url);
            return true;
        } catch {
            return false;
        }
    }

    reset() {
        const inputs = this.form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.classList.remove('is-valid', 'is-invalid');
            this.clearFieldError(input);
        });
    }
}

// Auto-initialize forms with data-validate attribute
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
        new FormValidator(form);
    });
});

// Make available globally
window.FormValidator = FormValidator;
