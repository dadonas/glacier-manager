"""
Main App File
"""

from fastapi import FastAPI
import routes

app = FastAPI()

app.include_router(routes.configs.router, tags=["configs"])
app.include_router(routes.vaults.router, tags=["vaults"])
