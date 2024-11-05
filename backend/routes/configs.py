"""
Configs Router
"""

from http import HTTPStatus
import boto3
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from models import AccountConfig
from core.db import get_collection
from core.utils import get_current_config

router = APIRouter()

@router.post('/', status_code=HTTPStatus.CREATED, response_model=AccountConfig)
def post_configs(config: AccountConfig):
    """
    Create Config
    """
    collection = get_collection('config')
    saved_config = collection.find_one()

    if saved_config is None:
        try:
            test_client_config(config)
            collection.insert_one(config.model_dump())
            return config
        except Exception as e:
            raise HTTPException(status_code=400, detail="Could not list vaults.") from e

    raise HTTPException(
        status_code=400,
        detail="Account already set."
    )

@router.put('/', status_code=HTTPStatus.OK, response_model=AccountConfig)
def put_configs(config: AccountConfig):
    """
    Replace Config
    """
    collection = get_collection('config')
    saved_config = collection.find_one()

    if saved_config is None:
        raise HTTPException(status_code=400, detail="There's no config set yet.")
    try:
        test_client_config(config)
        collection.update_one(
            {"_id": ObjectId(saved_config['_id'])},
            {"$set": config.model_dump()}
        )
        return config
    except Exception as e:
        raise HTTPException(status_code=400, detail="Could not list vaults.") from e

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
