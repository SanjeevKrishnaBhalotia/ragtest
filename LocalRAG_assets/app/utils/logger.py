"""
Logger utility for LocalRAG application
Provides structured logging with file rotation
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime

def setup_logger(log_level=logging.INFO):
    """Set up the main application logger"""

    # Create logs directory
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger("LocalRAG")
    logger.setLevel(log_level)

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler with rotation
    log_file = log_dir / f"localrag_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

def get_logger(name):
    """Get a logger for a specific module"""
    return logging.getLogger(f"LocalRAG.{name}")
