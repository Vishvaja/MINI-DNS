from fastapi import FastAPI
from app.core.logger import logger

#This is for loging the startup tasks
def setup_startup_tasks(app: FastAPI):
    @app.on_event("startup")
    async def startup_event():
        logger.info("🚀 Application startup complete.")

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("🛑 Application shutdown complete.")
