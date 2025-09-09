"""
Logging and error handling module for Crypto Analytics Platform.
Provides comprehensive logging, error handling, and monitoring capabilities.
"""

import logging
import logging.handlers
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict
from functools import wraps
import json

from config import config


class CryptoAnalyticsLogger:
    """Enhanced logger with crypto-specific formatting and error handling."""
    
    def __init__(self, name: str = "CryptoAnalytics"):
        self.logger = logging.getLogger(name)
        self._setup_logger()
        self.error_count = 0
        self.warning_count = 0
    
    def _setup_logger(self) -> None:
        """Configure logger with appropriate handlers and formatting."""
        log_level = getattr(logging, config.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        if config.get('DEBUG_MODE', False):
            console_handler.setFormatter(detailed_formatter)
        else:
            console_handler.setFormatter(simple_formatter)
        
        self.logger.addHandler(console_handler)
        
        # File handler (if not in debug mode, create logs directory)
        if not config.get('DEBUG_MODE', False):
            self._setup_file_logging(detailed_formatter)
    
    def _setup_file_logging(self, formatter: logging.Formatter) -> None:
        """Setup file logging with rotation."""
        try:
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            
            # Main log file with rotation
            file_handler = logging.handlers.RotatingFileHandler(
                logs_dir / "crypto_analytics.log",
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            
            # Error-only log file
            error_handler = logging.handlers.RotatingFileHandler(
                logs_dir / "errors.log",
                maxBytes=1 * 1024 * 1024,  # 1MB
                backupCount=3,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            self.logger.addHandler(error_handler)
            
        except Exception as e:
            # If file logging fails, just log to console
            self.logger.warning(f"Could not setup file logging: {e}")
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with optional context."""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with optional context."""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with optional context."""
        self.warning_count += 1
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """Log error message with optional exception info and context."""
        self.error_count += 1
        self._log_with_context(logging.ERROR, message, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, exc_info: bool = True, **kwargs) -> None:
        """Log critical message with exception info and context."""
        self.error_count += 1
        self._log_with_context(logging.CRITICAL, message, exc_info=exc_info, **kwargs)
    
    def _log_with_context(self, level: int, message: str, exc_info: bool = False, **kwargs) -> None:
        """Log message with additional context information."""
        if kwargs:
            context = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
            message = f"{message} | {context}"
        
        self.logger.log(level, message, exc_info=exc_info)
    
    def log_api_request(self, provider: str, endpoint: str, status_code: Optional[int] = None, 
                       response_time: Optional[float] = None, error: Optional[str] = None) -> None:
        """Log API request details."""
        context = {
            'provider': provider,
            'endpoint': endpoint,
            'status': status_code,
            'response_time': f"{response_time:.2f}s" if response_time else None,
            'error': error
        }
        
        if error:
            self.error("API request failed", **{k: v for k, v in context.items() if v is not None})
        elif status_code and status_code >= 400:
            self.warning("API request returned error status", **{k: v for k, v in context.items() if v is not None})
        else:
            self.debug("API request completed", **{k: v for k, v in context.items() if v is not None})
    
    def log_user_action(self, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log user actions for analytics."""
        context = {'action': action}
        if details:
            context.update(details)
        
        self.info("User action", **context)
    
    def get_stats(self) -> Dict[str, int]:
        """Get logging statistics."""
        return {
            'errors': self.error_count,
            'warnings': self.warning_count
        }


class APIException(Exception):
    """Base exception for API-related errors."""
    
    def __init__(self, message: str, provider: str = None, status_code: int = None, response_data: Any = None):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.response_data = response_data
        self.timestamp = datetime.now()


class DataValidationException(Exception):
    """Exception for data validation errors."""
    
    def __init__(self, message: str, invalid_data: Any = None, expected_format: str = None):
        super().__init__(message)
        self.invalid_data = invalid_data
        self.expected_format = expected_format


class ConfigurationException(Exception):
    """Exception for configuration-related errors."""
    
    def __init__(self, message: str, config_key: str = None):
        super().__init__(message)
        self.config_key = config_key


def handle_exceptions(logger: CryptoAnalyticsLogger):
    """Decorator for handling exceptions in functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except APIException as e:
                logger.error(
                    f"API error in {func.__name__}: {str(e)}",
                    exc_info=True,
                    provider=e.provider,
                    status_code=e.status_code
                )
                raise
            except DataValidationException as e:
                logger.error(
                    f"Data validation error in {func.__name__}: {str(e)}",
                    exc_info=True,
                    expected_format=e.expected_format
                )
                raise
            except ConfigurationException as e:
                logger.error(
                    f"Configuration error in {func.__name__}: {str(e)}",
                    exc_info=True,
                    config_key=e.config_key
                )
                raise
            except Exception as e:
                logger.error(
                    f"Unexpected error in {func.__name__}: {str(e)}",
                    exc_info=True
                )
                raise
        return wrapper
    return decorator


def handle_exceptions_gracefully(logger: CryptoAnalyticsLogger, default_return=None):
    """Decorator for gracefully handling exceptions without re-raising."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    exc_info=True
                )
                return default_return
        return wrapper
    return decorator


class ErrorReporter:
    """Collects and reports application errors and metrics."""
    
    def __init__(self, logger: CryptoAnalyticsLogger):
        self.logger = logger
        self.error_history = []
        self.performance_metrics = {}
    
    def report_error(self, error: Exception, context: Dict[str, Any] = None) -> None:
        """Report an error with context information."""
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {}
        }
        
        self.error_history.append(error_info)
        
        # Keep only last 100 errors in memory
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-100:]
        
        self.logger.error(
            f"Error reported: {error_info['error_type']} - {error_info['message']}",
            exc_info=True,
            **error_info['context']
        )
    
    def record_performance_metric(self, metric_name: str, value: float) -> None:
        """Record a performance metric."""
        if metric_name not in self.performance_metrics:
            self.performance_metrics[metric_name] = []
        
        self.performance_metrics[metric_name].append({
            'timestamp': datetime.now().isoformat(),
            'value': value
        })
        
        # Keep only last 1000 metrics per type
        if len(self.performance_metrics[metric_name]) > 1000:
            self.performance_metrics[metric_name] = self.performance_metrics[metric_name][-1000:]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors."""
        if not self.error_history:
            return {'total_errors': 0, 'error_types': {}}
        
        error_types = {}
        for error in self.error_history:
            error_type = error['error_type']
            if error_type not in error_types:
                error_types[error_type] = 0
            error_types[error_type] += 1
        
        return {
            'total_errors': len(self.error_history),
            'error_types': error_types,
            'recent_errors': self.error_history[-5:] if self.error_history else []
        }


# Global logger instance
logger = CryptoAnalyticsLogger()
error_reporter = ErrorReporter(logger)

# Export commonly used functions
def log_info(message: str, **kwargs) -> None:
    """Convenience function for info logging."""
    logger.info(message, **kwargs)

def log_error(message: str, exc_info: bool = False, **kwargs) -> None:
    """Convenience function for error logging."""
    logger.error(message, exc_info=exc_info, **kwargs)

def log_warning(message: str, **kwargs) -> None:
    """Convenience function for warning logging."""
    logger.warning(message, **kwargs)

def log_debug(message: str, **kwargs) -> None:
    """Convenience function for debug logging."""
    logger.debug(message, **kwargs)