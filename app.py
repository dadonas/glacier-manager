from fastapi import FastAPI, Header
from schemas import AccountConfig, GlacierVault
from http import HTTPStatus
import uuid
import boto3
import time
import asyncio
from typing import Optional

app = FastAPI()
current_account_config = {}

@app.post('/configs', status_code=HTTPStatus.CREATED)
def post_configs(config: AccountConfig):
    token = uuid.uuid4()
    current_account_config[str(token)] = config

    return {'token': str(token)}

@app.get('/configs', response_model=AccountConfig)
def get_configs(authorization: str = Header(...)):
    print(f'authorization {authorization} dict {current_account_config}')
    return current_account_config[authorization]

@app.get('/vaults')
def get_valts(authorization: str = Header(...)):
    glacier, credentials = init_client(authorization)
    response = glacier.list_vaults(accountId=credentials.account)
    return response['VaultList']

@app.post('/vaults/{vault_name}/list', status_code=HTTPStatus.OK)
def get_inventory(vault_name: str, authorization: str = Header(...)):
    glacier, _ = init_client(authorization)
    
    response = glacier.initiate_job(
        vaultName=vault_name,
        jobParameters={
            'Type': 'inventory-retrieval',
            'SNSTopic': 'arn:aws:sns:us-east-1:560159337065:glacier-inventory-retrieval'
        }
    )
    
    return {'job_id': response['jobId']}

def initiate_inventory_retrieval(token, vault_name):
    glacier, _ = init_client(token)
    
    response = glacier.initiate_job(
        vaultName=vault_name,
        jobParameters={
            'Type': 'inventory-retrieval',
            'SNSTopic': 'arn:aws:sns:us-east-1:560159337065:glacier-inventory-retrieval'
        }
    )
    job_id = response['jobId']
    print(f"Job de inventário iniciado com ID: {job_id}")
    return job_id

def check_job_status(token, vault_name, job_id):
    glacier, _ = init_client(token)

    response = glacier.describe_job(
        vaultName=vault_name,
        jobId=job_id
    )
    return response['Completed']

@app.get('/vaults/{vault_name}/inventory', status_code=HTTPStatus.OK)
def download_inventory(vault_name: str, job_id: Optional[str] = None, authorization: str = Header(...)):
    glacier, _ = init_client(authorization)

    response = glacier.get_job_output(
        vaultName=vault_name,
        jobId=job_id
    )
    inventory_data = response['body'].read()
    return GlacierVault.model_validate_json(inventory_data)

def init_client(token):
    credentials = current_account_config[token]

    return boto3.client(
        'glacier',
        aws_access_key_id=credentials.key,
        aws_secret_access_key=credentials.secret
    ), credentials
