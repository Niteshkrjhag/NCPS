"""
NCPS Backend — FastAPI Entry Point.

Source: docs/context/ncps_architecture.md §2
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.connection import init_db, close_db
from app.database.cache import cache
from app.event_pipeline import producer, consumer
from app.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown."""
    # ── Startup ──
    logger.info("NCPS Backend starting up...")

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database connection failed (non-fatal): {e}")
        logger.warning("Running without database — API routes that need DB will fail")

    # Connect Redis
    try:
        await cache.connect()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis connection failed (non-fatal): {e}")

    # Start Kafka producer
    try:
        await producer.start()
        logger.info("Kafka producer started")
    except Exception as e:
        logger.warning(f"Kafka producer failed to start (non-fatal): {e}")

    yield

    # ── Shutdown ──
    logger.info("NCPS Backend shutting down...")

    try:
        await producer.stop()
    except Exception:
        pass

    try:
        await cache.disconnect()
    except Exception:
        pass

    await close_db()
    logger.info("NCPS Backend stopped")


app = FastAPI(
    title="NCPS — News Credibility & Propagation System",
    description=(
        "Event-driven credibility scoring and trust propagation. "
        "Credibility-driven information, NOT engagement-driven."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(router, tags=["NCPS API"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "ncps-backend", "version": "0.1.0"}
