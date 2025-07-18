"""Logging framework for OVERKILL"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from rich.logging import RichHandler
from rich.console import Console


class OverkillLogger:
    """Custom logger with file and console output"""
    
    def __init__(self, name: str = "overkill", log_dir: Optional[Path] = None):
        self.name = name
        self.log_dir = log_dir or Path("/var/log/overkill")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # Console handler with Rich formatting
        console_handler = RichHandler(
            console=Console(stderr=True),
            show_time=False,
            show_path=False
        )
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_format)
        
        # File handler for detailed logs
        log_file = self.log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_format)
        
        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance"""
        return self.logger
    
    def set_console_level(self, level: int) -> None:
        """Set console logging level"""
        for handler in self.logger.handlers:
            if isinstance(handler, RichHandler):
                handler.setLevel(level)
    
    def enable_debug(self) -> None:
        """Enable debug output to console"""
        self.set_console_level(logging.DEBUG)
    
    def disable_debug(self) -> None:
        """Disable debug output to console"""
        self.set_console_level(logging.INFO)


# Global logger instance
_logger_instance = None


def get_logger(name: str = "overkill") -> logging.Logger:
    """Get or create the global logger instance"""
    global _logger_instance
    
    if _logger_instance is None:
        _logger_instance = OverkillLogger(name)
    
    return _logger_instance.get_logger()


# Convenience shortcuts
logger = get_logger()
debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
critical = logger.critical


def log_exception(exc: Exception, message: str = "An error occurred") -> None:
    """Log an exception with full traceback"""
    logger.exception(f"{message}: {str(exc)}")


def log_system_info() -> None:
    """Log basic system information"""
    import platform
    import psutil
    
    info("=== OVERKILL System Information ===")
    info(f"Platform: {platform.system()} {platform.release()}")
    info(f"Machine: {platform.machine()}")
    info(f"Python: {platform.python_version()}")
    info(f"CPU Count: {psutil.cpu_count()}")
    info(f"Memory: {psutil.virtual_memory().total / (1024**3):.1f} GB")
    
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read().strip()
            info(f"Device: {model}")
    except:
        pass
    
    info("===================================")


def setup_logging(debug_mode: bool = False) -> None:
    """Setup logging configuration"""
    if debug_mode:
        get_logger().parent.handlers[0].setLevel(logging.DEBUG)
        debug("Debug mode enabled")