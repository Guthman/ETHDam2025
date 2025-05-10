"""
Logging configuration module for the self-promise platform.
Provides consistent logging setup across all application modules.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any

# Default log levels for different environments
DEFAULT_LOG_LEVELS = {
    "production": logging.INFO,
    "development": logging.DEBUG,
    "testing": logging.DEBUG
}

# Default log format
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def setup_logging(
    module_name: str,
    log_level: Optional[str] = None,
    log_to_console: bool = True,
    log_to_file: bool = True,
    log_dir: str = "logs",
    log_file_max_size: int = 10 * 1024 * 1024,  # 10 MB
    log_file_backup_count: int = 5,
    log_format: str = DEFAULT_LOG_FORMAT
) -> logging.Logger:
    """
    Set up logging for a module.
    
    Args:
        module_name: Name of the module
        log_level: Log level as string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_console: Whether to log to console
        log_to_file: Whether to log to file
        log_dir: Directory to store log files
        log_file_max_size: Maximum size of log file before rotation
        log_file_backup_count: Number of backup files to keep
        log_format: Format string for log messages
        
    Returns:
        Configured logger instance
    """
    # Get environment
    env = os.environ.get("ENVIRONMENT", "development").lower()
    
    # Determine log level
    if log_level:
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {log_level}")
    else:
        numeric_level = DEFAULT_LOG_LEVELS.get(env, logging.INFO)
    
    # Create logger
    logger = logging.getLogger(module_name)
    logger.setLevel(numeric_level)
    
    # Clear existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_to_file:
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Create file handler
        log_file_path = os.path.join(log_dir, f"{module_name}.log")
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=log_file_max_size,
            backupCount=log_file_backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_module_logger(module_name: str, **kwargs: Any) -> logging.Logger:
    """
    Get a logger for a module with default configuration.
    
    Args:
        module_name: Name of the module
        **kwargs: Additional configuration options for setup_logging
        
    Returns:
        Configured logger instance
    """
    return setup_logging(module_name, **kwargs) 