from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import close_pool, init_pool
from app.routers import auth, health, readings, sensors, sessions, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(
    title="ClimBetter API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(sensors.router)
app.include_router(sessions.router)
app.include_router(readings.router)
