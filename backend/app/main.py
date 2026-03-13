from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import close_pool, init_pool
from app.routers import auth, health, readings, sensors, sessions, users, waitlist


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://smo-peak.github.io",
        "https://app.climbetter.com",
        "https://climbetter.com",
        "https://www.climbetter.com",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(sensors.router)
app.include_router(sessions.router)
app.include_router(readings.router)
app.include_router(waitlist.router)
