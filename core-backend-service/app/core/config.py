from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise Core Backend Service"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:admin1234@localhost:5432/ecommerce_db"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()