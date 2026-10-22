from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "materials"
    cookie_secure: bool = False

    class Config:
        env_file = ".env"

settings = Settings()