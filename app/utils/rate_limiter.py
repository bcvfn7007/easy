import time
from typing import Dict

# Simple memory dictionary to track user message timestamps
_USER_COOLDOWNS: Dict[int, float] = {}

def is_rate_limited(user_id: int, cooldown_seconds: float = 2.0) -> bool:
    """
    Checks if a user has sent a message within the cooldown period.
    Returns True if rate limited, False otherwise.
    """
    now = time.time()
    last_time = _USER_COOLDOWNS.get(user_id, 0.0)
    
    if now - last_time < cooldown_seconds:
        return True
        
    _USER_COOLDOWNS[user_id] = now
    return False
