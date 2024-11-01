"""
Configs Router
"""

from http import HTTPStatus
from typing import Optional
import boto3
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from models import AccountConfig
from core.db import get_collection
from core.utils import get_current_config

router = APIRouter()

@router.post('/', status_code=HTTPStatus.CREATED, response_model=AccountConfig)
def post_configs(config: AccountConfig,  replace: Optional[str] = None):
    """
    Create or Replace Config
    """
    collection = get_collection('config')
    saved_config = collection.find_one()

    if saved_config is None:
        try:
            test_client_config(config)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Could not list vaults.") from e

        collection.insert_one(config.dict())
        return config
    elif replace == 'true':
        collection.update_one(
            {"_id": ObjectId(saved_config['_id'])},
            {"$set": config.dict()}
        )
        return config
    raise HTTPException(
        status_code=400,
        detail="Account already set. Use query param replace=true to override this one."
    )

@router.get('/', response_model=AccountConfig)
def get_configs():
    """
    Returns AWS Account configuration if set
    """
    saved_config = get_current_config()

    if saved_config is None:
        raise HTTPException(status_code=204, detail="No configuration found.")

    return saved_config

def test_client_config(config):
    """
    Tests AWS credentials
    """
    glacier = boto3.client(
        'glacier',
        aws_access_key_id=config.key,
        aws_secret_access_key=config.secret,
        region_name=config.region
    )

    glacier.list_vaults(accountId=config.account)
