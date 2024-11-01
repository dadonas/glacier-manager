"""
Commom Operations
"""
from models import AccountConfig
from core.db import get_collection

def get_current_config() -> AccountConfig:
    """
    Returns current config if set.
    """
    collection = get_collection('config')
    saved_config = collection.find_one()
    return AccountConfig.model_validate(saved_config)
