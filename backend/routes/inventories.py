"""
Inventories Router
"""

import json
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from models import InventoryRetrievalRequest, VaultArchive
from core.aws import init_client, initiate_job, check_job_status
from core.db import get_collection
import backend.consts as consts

router = APIRouter()

@router.post('/requests')
def post_inventories_request(body: InventoryRetrievalRequest):
    """
    Initializes a inventory-retrieval job.
    """
    glacier = init_client()
    collection = get_collection('vaults')
    db_vault = collection.find_one({"name": body.vault_name})
    if db_vault is None:
        raise HTTPException(
            status_code=400,
            detail=f"Vault {body.vault_name} not found in database."
        )

    if  db_vault['inventory_status'] != consts.JOB_STATUS_NOT_REQUESTED:
        return HTTPException(
            status_code=400,
            detail=f"Vault inventory status must be {consts.JOB_STATUS_NOT_REQUESTED}"
            )

    job_id = initiate_job(glacier, body.vault_name, consts.INVENTORY_RETRIEVAL)
    db_vault['inventory_status'] = consts.JOB_STATUS_REQUESTED
    db_vault['inventory_job_id'] = job_id
    collection.update_one(
        {"_id": ObjectId(db_vault['_id'])},
        {"$set": db_vault}
    )

@router.get('/requests/status')
def get_inventories_status(vault_name: str):
    """
    Returns inventory-retrieval job status.
    """
    collection = get_collection('vaults')
    db_vault = collection.find_one({"name": vault_name})

    if db_vault is None:
        raise HTTPException(
            status_code=400,
            detail=f"Vault {vault_name} not found in database. Please, call GET /vaults first."
        )
    if db_vault['inventory_status'] == consts.JOB_STATUS_REQUESTED:
        db_vault = update_job_status(db_vault)

    return {'status': db_vault['inventory_status']}

@router.get('/')
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
            detail=f"Vault {vault_name} not found in database."
        )

    if db_vault['archives'] is not None:
        return db_vault['archives']

    db_vault = update_job_status(db_vault)

    if db_vault['inventory_status'] != consts.JOB_STATUS_AVAILABLE:
        raise HTTPException(
            status_code=400,
            detail="Inventory is not available."
        )

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
            size = arch['Size']
        )

        archives.append(va.model_dump())

    db_vault['archives'] = archives
    collection.update_one(
        {"_id": ObjectId(db_vault['_id'])},
        {"$set": db_vault}
    )

    return archives

def update_job_status(db_vault):
    """
    Update Job Status
    """
    if db_vault['inventory_job_id'] == '':
        return db_vault

    collection = get_collection('vaults')
    aws_job_status = check_job_status(db_vault['name'], db_vault['inventory_job_id'])
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
    return db_vault
