
"""
DB Operations
"""
from pymongo import MongoClient
from consts import MONGO_URL

client = MongoClient(MONGO_URL)
database = client["glacier_manager"]

def get_collection(name: str):
    """
    Returns collection from the specified name. 
    """
    return database[name]
