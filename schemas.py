from pydantic import BaseModel
from typing import List

class AccountConfig(BaseModel):
    account: str
    key: str
    secret: str

class Archive(BaseModel):
    ArchiveId: str
    ArchiveDescription: str
    CreationDate: str
    Size: int
    SHA256TreeHash: str

class GlacierVault(BaseModel):
    VaultARN: str
    InventoryDate: str
    ArchiveList: List[Archive]