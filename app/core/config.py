from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    API_KEY: str = "supersecret"
    MAX_CNAME_DEPTH: int = 10
    TTL_CLEANUP_INTERVAL: int = 60
    REDIS_URL: str = "redis://localhost:6379"
    TESTING: bool = False 

    class Config:
        env_file = ".env"

settings = Settings()
