# log_config.py

import logging
from colorlog import ColoredFormatter

def setup_logging(level=logging.DEBUG):
    """
    # Set up root logger with colored output.
    # - Uses colorlog.ColoredFormatter for automatic color mapping.
    # - Attaches one StreamHandler to the root logger.
    # - Subsequent calls are idempotent.
    """
    root = logging.getLogger()
    if root.handlers:
        return  # already configured

    # Create console handler with colored formatter
    handler = logging.StreamHandler()
    handler.setFormatter(ColoredFormatter(
        "%(log_color)s%(levelname)s - %(name)s - %(message)s",
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'red,bg_white',
            "EXCEPTION" : 'white, bg_red'
        }
    ))

    root.setLevel(level)
    root.addHandler(handler)
