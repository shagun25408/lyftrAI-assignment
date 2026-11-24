from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .database import Base, engine
from . import models
from .routers.api import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

settings = get_settings()
app = FastAPI(title="Lyftr AI", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",")], allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-Simulate-Failure"])
app.include_router(router)
