import logging
import sys

def setup_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("connectifyvpn")
    if logger.handlers:
        return logger
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    h = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
    h.setFormatter(fmt)
    logger.addHandler(h)
    return logger
