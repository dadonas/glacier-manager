"""
Main App File
"""

from fastapi import FastAPI
from routes import configs, vaults

app = FastAPI()

app.include_router(configs.router, prefix="/configs", tags=["configs"])
app.include_router(vaults.router, prefix="/vaults", tags=["vaults"])
