"""
Models
"""

from typing import List, Optional
from pydantic import BaseModel

class AccountConfig(BaseModel):
    account: str
    key: str
    secret: str
    region: str
    sns_topic_arn: Optional[str] = None

class VaultArchive(BaseModel):
    id: str
    description: str
    creation_date: str
    size: int

class Vault(BaseModel):
    name: str
    arn: str
    size_in_bytes: int
    creation_date: str
    number_of_achives: int
    inventory_status: str = "not_requested" # not_requested, requested, available
    inventory_job_id: Optional[str] = None
    archives: Optional[List[VaultArchive]] = None

class InventoryRetrievalRequest(BaseModel):
    vault_name: str

class ArchiveRetrievalRequest(BaseModel):
    archive_id: str
    tier: Optional[str] = None
