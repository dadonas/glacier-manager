"""
AWS Client Operations
"""
import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException
from core.utils import get_current_config
from backend.consts import JOB_STATUS_REQUESTED, JOB_STATUS_NOT_FOUND, JOB_STATUS_AVAILABLE

def init_client():
    """
    Initializes Glacier Client
    """
    saved_config = get_current_config()

    if saved_config is None:
        raise HTTPException(status_code=400, detail="No configuration found.")

    glacier = boto3.client(
        'glacier',
        aws_access_key_id=saved_config.key,
        aws_secret_access_key=saved_config.secret,
        region_name=saved_config.region
    )
    return glacier

def initiate_job(glacier, vault_name, job_type, tier: str = ''):
    """
    Initializes a Glacier Job
    """
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
    """
    Checks a Glacier Job Status
    """
    glacier = init_client()

    try:
        response = glacier.describe_job(
            vaultName=vault_name,
            jobId=job_id
        )

        if response['Completed']:
            return JOB_STATUS_AVAILABLE

        return JOB_STATUS_REQUESTED
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            return JOB_STATUS_NOT_FOUND
        else:
            print(f"ClientError: {e.response['Error']['Message']}")
