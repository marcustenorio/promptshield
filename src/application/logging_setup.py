# Comentário: configuração de logging JSON (arquivo + console).
import logging
import os
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(name: str, file_name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Handler arquivo (rotativo)
    fh = RotatingFileHandler(os.path.join(LOG_DIR, file_name), maxBytes=2_000_000, backupCount=3)
    fh.setLevel(logging.INFO)
    fh.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

    # Handler console
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

    # Evita handlers duplicados ao recarregar
    if not logger.handlers:
        logger.addHandler(fh)
        logger.addHandler(ch)

    logger.propagate = False
    return logger

# Loggers específicos
app_logger     = setup_logger("app", "app.log")           # decisões de firewall
metrics_logger = setup_logger("metrics", "metrics.log")   # métricas de treino/val/calibração

