# app/utils/logging.py
import logging
import sys
import os
from datetime import datetime
from app.config.settings import AppConfig

def setup_logging(log_level=None, log_to_file=True):
    """
    Set up application logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to a file in addition to console
    
    Returns:
        Logger instance for the application
    """
    # Get log level from config if not provided
    if log_level is None:
        log_level_str = AppConfig.LOG_LEVEL
        log_level = getattr(logging, log_level_str, logging.INFO)
    
    # Create logger
    logger = logging.getLogger('hospital_chatbot')
    logger.setLevel(log_level)
    
    # Clear existing handlers to avoid duplication
    if logger.handlers:
        logger.handlers = []
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if requested
    if log_to_file:
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Create log file name with timestamp and environment
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        env_name = AppConfig.ENV
        log_file = os.path.join(logs_dir, f'hospital_chatbot_{env_name}_{timestamp}.log')
        
        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Log startup message
    logger.info(f"Logging initialized for {AppConfig.get_environment_name()} environment at level {log_level_str}")
    
    return logger

def get_logger(name=None):
    """
    Get a logger instance.
    
    Args:
        name: Logger name (optional)
    
    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f'hospital_chatbot.{name}')
    else:
        return logging.getLogger('hospital_chatbot')

# Initialize default logger
default_logger = setup_logging()