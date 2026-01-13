# Configuração centralizada de logging

import logging
from pathlib import Path
from config import LOG_FORMAT, LOG_FILE

def setup_logger(name: str, log_file: Path = LOG_FILE) -> logging.Logger:
    """
    Configura um logger centralizado com output para arquivo e console.
    
    Args:
        name: Nome do logger (geralmente __name__)
        log_file: Caminho do arquivo de log
        
    Returns:
        logging.Logger: Logger configurado
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter(LOG_FORMAT)
    
    # File Handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
