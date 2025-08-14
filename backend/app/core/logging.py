# backend/app/core/logging.py
"""
Centralized logging configuration for the FastAPI application.

This module provides consistent logging setup across the application,
including both console and file output with proper formatting and rotation.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

def setup_logging(
    log_dir: str,
    api_server_log_file: str,
    max_log_file_size_mb: int = 5,
    log_file_backup_count: int = 5,
    log_level: int = logging.INFO,
    clear_existing_handlers: bool = True
) -> logging.Logger:
    """
    Configure logging for FastAPI server to file and console.
    
    Args:
        log_dir: Directory where log files will be stored
        api_server_log_file: Name of the API server log file
        max_log_file_size_mb: Maximum size of log files in MB before rotation
        log_file_backup_count: Number of backup log files to keep
        log_level: Logging level (e.g., logging.INFO, logging.DEBUG)
        clear_existing_handlers: Whether to clear existing handlers
    
    Returns:
        Configured logger instance
    """
    
    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)
    api_server_log_path = os.path.join(log_dir, api_server_log_file)

    # Get the root logger for general application logging
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to prevent duplicate output if reloaded (e.g., by uvicorn reload)
    if clear_existing_handlers and root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File Handler for API server logs
    file_handler = RotatingFileHandler(
        api_server_log_path,
        maxBytes=max_log_file_size_mb * 1024 * 1024, 
        backupCount=log_file_backup_count
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Additionally, configure uvicorn loggers to use our file handler
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.addHandler(file_handler)
    uvicorn_access_logger.propagate = False 

    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.addHandler(file_handler)
    uvicorn_error_logger.propagate = False

    return root_logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
