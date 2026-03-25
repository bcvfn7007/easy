import logging
import sys

def setup_logger(name: str) -> logging.Logger:
    """
    Set up a standard logger for the application modules.
    Ensures that output is cleanly formatted and async-safe print levels are respected.
    """
    logger = logging.getLogger(name)
    
    # Only configure if hasn't been configured before
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Format: [2026-03-25 10:15:30] [INFO] [app.services.ai] Message
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # Stream to stdout for cloud logging (like Railway)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger
