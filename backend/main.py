"""
Main App File
"""

from fastapi import FastAPI
from routes import configs, vaults, inventories

app = FastAPI()

app.include_router(configs.router, prefix="/configs", tags=["configs"])
app.include_router(vaults.router, prefix="/vaults", tags=["vaults"])
app.include_router(inventories.router, prefix="/inventories", tags=["inventories"])
