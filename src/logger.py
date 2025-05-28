"""
Enhanced Logging System for Supplier Price List Consolidation Tool
Provides comprehensive logging with file rotation and multiple output formats.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json


class ConsolidatorLogger:
    """Enhanced logging system with file rotation and structured output."""
    
    def __init__(self, log_dir: str = "logs", log_level: str = "INFO"):
        """
        Initialize the logging system.
        
        Args:
            log_dir: Directory for log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.log_level = getattr(logging, log_level.upper())
        self.logger = logging.getLogger("consolidator")
        self.logger.setLevel(self.log_level)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Session tracking - MUST be set before handlers
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_stats = {
            "start_time": datetime.now().isoformat(),
            "files_processed": 0,
            "errors": 0,
            "warnings": 0,
            "session_id": self.session_id
        }
        
        # Setup handlers (after session_id is set)
        self._setup_file_handler()
        self._setup_console_handler()
        self._setup_error_handler()
    
    def _setup_file_handler(self):
        """Setup rotating file handler for general logs."""
        log_file = self.log_dir / "consolidator.log"
        
        # Rotating file handler (10MB max, keep 5 backups)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        
        self.logger.addHandler(file_handler)
    
    def _setup_console_handler(self):
        """Setup console handler for user feedback."""
        console_handler = logging.StreamHandler(sys.stdout)
        
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(self.log_level)
        
        self.logger.addHandler(console_handler)
    
    def _setup_error_handler(self):
        """Setup separate handler for errors only."""
        error_file = self.log_dir / f"errors_{self.session_id}.log"
        
        error_handler = logging.FileHandler(error_file, encoding='utf-8')
        error_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s\n'
            'Session: %(session_id)s\n'
            '%(pathname)s\n'
            '---\n',
            defaults={'session_id': self.session_id}
        )
        error_handler.setFormatter(error_formatter)
        error_handler.setLevel(logging.ERROR)
        
        self.logger.addHandler(error_handler)
    
    def log_session_start(self, config: Dict[str, Any]):
        """Log session start with configuration."""
        self.logger.info(f"=== SESSION START: {self.session_id} ===")
        self.logger.info(f"Log Level: {logging.getLevelName(self.log_level)}")
        self.logger.info(f"Configuration: {json.dumps(config.get('logging', {}), indent=2)}")
    
    def log_session_end(self):
        """Log session end with statistics."""
        self.session_stats["end_time"] = datetime.now().isoformat()
        duration = datetime.fromisoformat(self.session_stats["end_time"]) - \
                  datetime.fromisoformat(self.session_stats["start_time"])
        
        self.logger.info(f"=== SESSION END: {self.session_id} ===")
        self.logger.info(f"Duration: {duration}")
        self.logger.info(f"Files Processed: {self.session_stats['files_processed']}")
        self.logger.info(f"Total Errors: {self.session_stats['errors']}")
        self.logger.info(f"Total Warnings: {self.session_stats['warnings']}")
        
        # Write session summary
        self._write_session_summary()
    
    def log_file_processing_start(self, file_path: str, file_size: int):
        """Log start of file processing."""
        self.logger.info(f"Processing file: {file_path} ({file_size:,} bytes)")
    
    def log_file_processing_end(self, file_path: str, records_processed: int, 
                               errors: int = 0, warnings: int = 0):
        """Log end of file processing."""
        self.session_stats["files_processed"] += 1
        self.session_stats["errors"] += errors
        self.session_stats["warnings"] += warnings
        
        status = "SUCCESS"
        if errors > 0:
            status = "ERRORS"
        elif warnings > 0:
            status = "WARNINGS"
        
        self.logger.info(f"Completed {file_path}: {records_processed} records, "
                        f"{errors} errors, {warnings} warnings - {status}")
    
    def log_validation_summary(self, supplier_name: str, validation_result):
        """Log validation summary for a supplier."""
        summary = validation_result.get_summary()
        
        if summary['error_count'] > 0:
            self.logger.error(f"{supplier_name}: {summary['error_count']} validation errors")
        
        if summary['warning_count'] > 0:
            self.logger.warning(f"{supplier_name}: {summary['warning_count']} validation warnings")
        
        if summary['error_count'] == 0 and summary['warning_count'] == 0:
            self.logger.info(f"{supplier_name}: Validation passed")
    
    def log_column_mapping(self, supplier_name: str, mappings: Dict[str, str], 
                          unmapped_columns: list):
        """Log column mapping results."""
        self.logger.debug(f"{supplier_name} - Column mappings: {mappings}")
        
        if unmapped_columns:
            self.logger.warning(f"{supplier_name} - Unmapped columns: {unmapped_columns}")
    
    def log_performance_metrics(self, operation: str, duration: float, 
                               records_processed: int = 0):
        """Log performance metrics."""
        rate = records_processed / duration if duration > 0 and records_processed > 0 else 0
        
        self.logger.info(f"Performance - {operation}: {duration:.2f}s")
        if rate > 0:
            self.logger.info(f"Processing rate: {rate:.1f} records/second")
    
    def log_memory_usage(self, operation: str):
        """Log current memory usage."""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.logger.debug(f"Memory usage after {operation}: {memory_mb:.1f} MB")
        except ImportError:
            self.logger.debug("psutil not available for memory monitoring")
    
    def _write_session_summary(self):
        """Write detailed session summary to JSON file."""
        summary_file = self.log_dir / f"session_summary_{self.session_id}.json"
        
        try:
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(self.session_stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to write session summary: {e}")
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance."""
        return self.logger


class ContextualLogger:
    """Context manager for logging operations with automatic timing."""
    
    def __init__(self, logger: logging.Logger, operation: str, level: int = logging.INFO):
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.log(self.level, f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            self.logger.log(self.level, f"Completed {self.operation} in {duration:.2f}s")
        else:
            self.logger.error(f"Failed {self.operation} after {duration:.2f}s: {exc_val}")
        
        return False  # Don't suppress exceptions


def setup_logging(config: Dict[str, Any]) -> ConsolidatorLogger:
    """
    Setup logging system based on configuration.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        Configured ConsolidatorLogger instance
    """
    logging_config = config.get('logging', {})
    
    log_dir = logging_config.get('log_directory', 'logs')
    log_level = logging_config.get('level', 'INFO')
    
    return ConsolidatorLogger(log_dir, log_level)


def get_logger(name: str = "consolidator") -> logging.Logger:
    """Get logger instance by name."""
    return logging.getLogger(name)
