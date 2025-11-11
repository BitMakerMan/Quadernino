"""
Sistema di logging professionale per Quadernino V2
Utilizza solo la libreria standard di Python
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

class QuaderninoLogger:
    """Gestore di logging centralizzato per Quadernino"""

    def __init__(self, name: str = "Quadernino", log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.logger = None
        self._setup_logger()

    def _setup_logger(self):
        """Configura il logger con file e console"""
        # Crea directory log se non esiste
        self.log_dir.mkdir(exist_ok=True)

        # Nome file con data
        log_filename = f"quadernino_{datetime.now().strftime('%Y%m%d')}.log"
        log_filepath = self.log_dir / log_filename

        # Configura logger
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)

        # Rimuovi handler esistenti per evitare duplicati
        if self.logger.handlers:
            self.logger.handlers.clear()

        # Formato dettagliato
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # File handler per tutti i log
        file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        # Console handler solo per WARNING e ERROR
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)

        # Aggiungi handler
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def debug(self, message: str, **kwargs):
        """Log di debug (solo su file)"""
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log informativo (solo su file)"""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log di avviso (file + console)"""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log di errore (file + console)"""
        self.logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critico (file + console)"""
        self.logger.critical(message, **kwargs)

    def log_user_action(self, action: str, details: Optional[str] = None, user: Optional[str] = None):
        """Registra azioni utente per audit"""
        message = f"USER_ACTION: {action}"
        if user:
            message += f" | User: {user}"
        if details:
            message += f" | Details: {details}"
        self.info(message)

    def log_api_call(self, api_name: str, status: str, duration: Optional[float] = None):
        """Registra chiamate API con performance"""
        message = f"API_CALL: {api_name} | Status: {status}"
        if duration:
            message += f" | Duration: {duration:.2f}s"
        self.info(message)

    def log_error_with_context(self, error: Exception, context: str, user_data: Optional[dict] = None):
        """Log errori con contesto completo"""
        message = f"ERROR in {context}: {type(error).__name__}: {str(error)}"
        if user_data:
            message += f" | Context: {user_data}"
        self.error(message, exc_info=True)

# Istanza globale dell'applicazione
quadernino_logger = QuaderninoLogger()

# Funzioni di comodo per quick access
def log_debug(message: str):
    quadernino_logger.debug(message)

def log_info(message: str):
    quadernino_logger.info(message)

def log_warning(message: str):
    quadernino_logger.warning(message)

def log_error(message: str):
    quadernino_logger.error(message)

def log_critical(message: str):
    quadernino_logger.critical(message)

def log_user_action(action: str, details: Optional[str] = None):
    quadernino_logger.log_user_action(action, details)

def log_api_call(api_name: str, status: str, duration: Optional[float] = None):
    quadernino_logger.log_api_call(api_name, status, duration)

def log_error_with_context(error: Exception, context: str, user_data: Optional[dict] = None):
    quadernino_logger.log_error_with_context(error, context, user_data)