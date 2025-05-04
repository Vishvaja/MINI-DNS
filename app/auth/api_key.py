from fastapi import Header, HTTPException, Depends
from app.core.config import settings

API_KEY_NAME = "Enter API-Key"

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
