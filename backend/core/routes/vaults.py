"""
Vaults Router
"""

from http import HTTPStatus
from typing import List
import json
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from models import VaultArchive, Vault
from core.aws import init_client, initiate_job, check_job_status
from core.utils import get_current_config
from core.db import get_collection
import backend.consts as consts

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
                vaults.append(Vault.parse_obj(db_vault))
                continue
            else:
                vault = Vault(
                    name = v['VaultName'],
                    arn= v['VaultARN'],
                    size_in_bytes = v['SizeInBytes'],
                    creation_date = v['CreationDate'],
                    number_of_achives = v['NumberOfArchives']
                )

                collection.insert_one(vault.dict())
                vaults.append(vault)
        return vaults
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to list vaults.") from e

@router.get('/{vault_name}/inventory/status')
def get_inventory(vault_name: str):
    """
    Returns inventory if avaiable or initializes a inventory-retrieval job.
    """
    glacier = init_client()
    collection = get_collection('vaults')
    db_vault = collection.find_one({"name": vault_name})
    status = consts.JOB_STATUS_REQUESTED

    if db_vault is None:
        raise HTTPException(
            status_code=400,
            detail=f"Vault {vault_name} not found in database. Please, call GET /vaults first."
        )

    match db_vault['inventory_status']:
        case consts.JOB_STATUS_NOT_REQUESTED:
            job_id = initiate_job(glacier, vault_name, 'inventory-retrieval', )
            db_vault['inventory_status'] = status
            db_vault['inventory_job_id'] = job_id
            collection.update_one(
                {"_id": ObjectId(db_vault['_id'])},
                {"$set": db_vault}
            )
        case consts.JOB_STATUS_REQUESTED:
            aws_job_status = check_job_status(vault_name, db_vault['inventory_job_id'])
            match aws_job_status:
                case consts.JOB_STATUS_AVAILABLE:
                    status = consts.JOB_STATUS_AVAILABLE
                    db_vault['inventory_status'] = status
                    collection.update_one(
                        {"_id": ObjectId(db_vault['_id'])},
                        {"$set": db_vault}
                    )
                case consts.JOB_STATUS_NOT_FOUND:
                    status = consts.JOB_STATUS_NOT_REQUESTED
                    db_vault['inventory_status'] = status
                    db_vault['inventory_job_id'] = ''
                    collection.update_one(
                        {"_id": ObjectId(db_vault['_id'])},
                        {"$set": db_vault}
                    )
        case consts.JOB_STATUS_AVAILABLE:
            status = consts.JOB_STATUS_AVAILABLE

    return {'status': status}

@router.get('/{vault_name}/inventory', status_code=HTTPStatus.OK)
def download_inventory(vault_name: str):
    """
    Downloads inventory if ready.
    """
    glacier = init_client()
    collection = get_collection('vaults')
    db_vault = collection.find_one({"name": vault_name})
    if db_vault is None:
        raise HTTPException(
            status_code=400,
            detail=f"Vault {vault_name} not found in database.\nPlease, call GET /vaults first."
        )
    if db_vault['inventory_status'] != consts.JOB_STATUS_AVAILABLE:
        raise HTTPException(
            status_code=400,
            detail=f"""
            Vault {vault_name} is not available yet.\n
            Please, call GET /vaults/{vault_name}/inventory/status to check vault status.
            """
        )
    if db_vault['archives'] is not None:
        return db_vault['archives']

    response = glacier.get_job_output(
        vaultName=vault_name,
        jobId=db_vault['inventory_job_id']
    )

    glacier_vault = json.loads(response['body'].read())

    archives = []
    for arch in glacier_vault['ArchiveList']:
        va = VaultArchive(
            id = arch['ArchiveId'],
            description = arch['ArchiveDescription'],
            creation_date = arch['CreationDate'],
            size = arch['Size'],
        )

        archives.append(va.dict())
    db_vault['archives'] = archives
    collection.update_one(
        {"_id": ObjectId(db_vault['_id'])},
        {"$set": db_vault}
    )

    return archives
