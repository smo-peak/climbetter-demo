from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import close_pool, init_pool
from app.models import create_tables
from app.routers import health, measurements, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await init_pool()
    await create_tables(pool)
    yield
    await close_pool()


app = FastAPI(
    title="ClimBetter API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(measurements.router)
