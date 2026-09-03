from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from src.api.procedure_routes import router as procedure_router
from src.api.routes import router
from src.common.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_db()
    yield


app = FastAPI(title="Claim Processing Service", lifespan=lifespan)
app.include_router(router)
app.include_router(procedure_router)
