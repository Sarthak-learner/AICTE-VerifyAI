"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.v1.router import api_router

settings = get_settings()

logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(__name__)

DISCLAIMER = (
    "AICTE VerifyAI produces advisory findings only. "
    "No AI model makes a final regulatory decision. "
    "All validation results must be reviewed by an authorised AICTE officer."
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AICTE VerifyAI starting — environment: %s", settings.app_env)

    # Security check: Production requires explicit, cryptographically secure SECRET_KEY
    if settings.app_env.lower() == "production":
        insecure_keys = {
            "CHANGE_ME_IN_PRODUCTION",
            "verifyai-demo-secret-key-2026-development-only",
            "replace-with-a-random-32-char-secret",
        }
        if settings.secret_key in insecure_keys or len(settings.secret_key) < 32:
            raise RuntimeError(
                "Production security violation: SECRET_KEY must be an explicitly configured, "
                "cryptographically secure string with at least 32 characters."
            )

    # Seed demo accounts only in development mode
    if settings.is_development:
        try:
            from app.db.session import SessionLocal
            from app.services.user_service import seed_default_users
            with SessionLocal() as db:
                seed_default_users(db)
        except Exception as exc:
            logger.warning("Could not auto-seed default users on startup: %s", exc)
    yield
    logger.info("AICTE VerifyAI shutting down.")


app = FastAPI(
    title="AICTE VerifyAI",
    description=(
        "Preliminary document validation assistant for AICTE institutional approval applications.\n\n"
        f"**Advisory Disclaimer:** {DISCLAIMER}"
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def root():
    return {
        "service": "AICTE VerifyAI",
        "version": "0.1.0",
        "docs": "/api/docs",
        "disclaimer": DISCLAIMER,
    }
