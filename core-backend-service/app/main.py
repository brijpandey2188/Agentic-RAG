from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core import settings

app = FastAPI(
    title="Core Backend Service",
    description="Microservice responsible for Orders and Refunds data management.",
    version="1.0.0",
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Health Check"])
def read_root():
    return {
        "status": "online",
        "service": "Core Backend Service",
        "docs": "http://127.0.0.1:8000/docs",
    }


@app.get("/health", tags=["Health Check"])
def health_check():
    return {"status": "healthy"}