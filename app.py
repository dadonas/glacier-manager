from http import HTTPStatus
from typing import Optional, List
import json
from pymongo import MongoClient
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException
from bson import ObjectId
import boto3
import consts
from models import AccountConfig, VaultArchive, Vault

app = FastAPI()

@app.post('/configs', status_code=HTTPStatus.CREATED, response_model=AccountConfig)
def post_configs(config: AccountConfig,  replace: Optional[str] = None):
    collection = app.database['config']
    saved_config = collection.find_one()

    if saved_config is None:
        try:
            test_client_config(config)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid configuration. Could not list vaults.") from e

        collection.insert_one(config.dict())
        return config
    elif replace == 'true':
        collection.update_one(
            {"_id": ObjectId(saved_config['_id'])},
            {"$set": config.dict()}
        )
        return config
    
    app.config = config

    raise HTTPException(status_code=400, detail="Account already set. Use query param replace=true to override account configuration.")

@app.get('/configs', response_model=AccountConfig)
def get_configs():
    saved_config = get_current_config()

    if saved_config is None:
        raise HTTPException(status_code=400, detail="No configuration found.")

    return saved_config

@app.get('/vaults', response_model=List[Vault])
def get_valts():
    vaults = []

    try:
        glacier = init_client()
        response = glacier.list_vaults(accountId=app.config.account)
        collection = app.database['vaults']
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

@app.get('/vaults/{vault_name}/inventory/status')
def get_inventory(vault_name: str):
    glacier = init_client()
    collection = app.database['vaults']
    db_vault = collection.find_one({"name": vault_name})
    status = consts.JOB_STATUS_REQUESTED

    if db_vault is None:
        raise HTTPException(status_code=400, detail=f"Vault {vault_name} not found in database. Please, call GET /vaults first.")

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

def initiate_job(glacier, vault_name, job_type, tier: str = ''):
    config = get_current_config()

    params={
        'Type': job_type,
    }

    if config.sns_topic_arn is not None:
        params['SNSTopic'] = config.sns_topic_arn

    if tier is not '':
        params['Tier'] = tier

    response = glacier.initiate_job(
                    vaultName=vault_name,
                    jobParameters=params
                )
    
    return response['jobId']

def check_job_status(vault_name, job_id):
    glacier = init_client()

    try:
        response = glacier.describe_job(
            vaultName=vault_name,
            jobId=job_id
        )

        if response['Completed']:
            return consts.JOB_STATUS_AVAILABLE    

        return consts.JOB_STATUS_REQUESTED
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            return consts.JOB_STATUS_NOT_FOUND
        else:
            print(f"ClientError: {e.response['Error']['Message']}")

@app.get('/vaults/{vault_name}/inventory', status_code=HTTPStatus.OK)
def download_inventory(vault_name: str):
    glacier = init_client()
    collection = app.database['vaults']
    db_vault = collection.find_one({"name": vault_name})
    
    if db_vault is None:
        raise HTTPException(status_code=400, detail=f"Vault {vault_name} not found in database. Please, call GET /vaults first.")
    
    if db_vault['inventory_status'] != consts.JOB_STATUS_AVAILABLE:
        raise HTTPException(status_code=400, detail=f"Vault {vault_name} is not available yet. Please, call GET /vaults/{vault_name}/inventory/status to check vault status.")
    
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

def test_client_config(config):
    glacier = boto3.client(
        'glacier',
        aws_access_key_id=config.key,
        aws_secret_access_key=config.secret,
        region_name=config.region        
    )

    glacier.list_vaults(accountId=config.account)
    
def init_client():
    saved_config = get_current_config()

    if saved_config == None:
        raise HTTPException(status_code=400, detail="No configuration found.")

    glacier = boto3.client(
        'glacier',
        aws_access_key_id=saved_config.key,
        aws_secret_access_key=saved_config.secret,
        region_name=saved_config.region        
    )
    
    return glacier

@app.on_event("startup")
def startup_db_client():
    app.mongodb_client = MongoClient("mongodb://user:pass@localhost:27017/")
    app.database = app.mongodb_client["glacier_manager"]

@app.on_event("shutdown")
def shutdown_db_client():
    app.mongodb_client.close()

def get_current_config():
    if not hasattr(app, 'config'):
        collection = app.database['config']
        saved_config = collection.find_one()
        app.config = AccountConfig.parse_obj(saved_config)
    
    return app.config