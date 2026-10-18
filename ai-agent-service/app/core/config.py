from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise Agentic E-Commerce Platform - AI Agent Service"

    OPENAI_API_KEY: str
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str = "ecommerce-policies"
    TAVILY_API_KEY: str = ""
    STRIPE_TEST_SECRET_KEY: str = ""
    CORE_BACKEND_URL: str = "http://127.0.0.1:8000/api/v1"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()