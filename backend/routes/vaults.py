"""
Vaults Router
"""

from typing import List
from fastapi import APIRouter, HTTPException
from models import Vault
from core.aws import init_client
from core.utils import get_current_config
from core.db import get_collection

router = APIRouter()

@router.get('/', response_model=List[Vault])
def get_valts():
    """
    Returns Vaults
    """
    vaults = []

    try:
        config = get_current_config()
        glacier = init_client()
        response = glacier.list_vaults(accountId=config.account)
        collection = get_collection('vaults')
        for v in response['VaultList']:
            db_vault = collection.find_one({"name": v['VaultName']})

            if db_vault is not None:
                vaults.append(Vault.model_validate(db_vault))
                continue
            else:
                vault = Vault(
                    name = v['VaultName'],
                    arn= v['VaultARN'],
                    size_in_bytes = v['SizeInBytes'],
                    creation_date = v['CreationDate'],
                    number_of_achives = v['NumberOfArchives']
                )

                collection.insert_one(vault.model_dump())
                vaults.append(vault)
        return vaults
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to list vaults.") from e
