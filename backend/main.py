import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import engine
from . import models, exceptions
from .config import settings
from .logger import logger
from .routers import (
    users_router,
    events_router,
    deals_router,
    reviews_router,
    campaigns_router,
    payments_router,
    chat_router,
    notifications_router,
    notifications_ws_router,
    auth_router
)

# ✅ Import limiter ONLY from core
from backend.core.limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded


# -------------------------------------------------
# Create FastAPI app
# -------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.ENV == "development" else None,
    redoc_url="/redoc" if settings.ENV == "development" else None
)

# -------------------------------------------------
# Attach limiter
# -------------------------------------------------

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# -------------------------------------------------
# Initialize database
# -------------------------------------------------

def run_startup_migrations():
    """Manual migration for vendor change if DB already exists"""
    try:
        from sqlalchemy import text, inspect
        # Use inspector to be database-agnostic
        inspector = inspect(engine)
        if 'deals' in inspector.get_table_names():
            columns = [c['name'] for c in inspector.get_columns('deals')]
            if 'stripe_payment_intent_id' in columns and 'razorpay_payment_id' not in columns:
                with engine.begin() as conn:
                    if engine.url.drivername.startswith("postgresql"):
                        conn.execute(text("ALTER TABLE deals RENAME COLUMN stripe_payment_intent_id TO razorpay_payment_id"))
                    else:
                        # SQLite doesn't support RENAME COLUMN in older versions easily, 
                        # but SQLAlchemy/FastAPI devs usually use latest. 
                        # Simple RENAME for SQLite:
                        conn.execute(text("ALTER TABLE deals RENAME COLUMN stripe_payment_intent_id TO razorpay_payment_id"))
                    logger.info("Migrated 'stripe_payment_intent_id' to 'razorpay_payment_id'")
    except Exception as e:
        logger.warning(f"Startup migration skipped/failed: {e}")

models.Base.metadata.create_all(bind=engine)
run_startup_migrations()


# -------------------------------------------------
# Global Exception Handlers
# -------------------------------------------------

def _cors_headers(request: Request) -> dict:
    """
    FastAPI exception handlers run OUTSIDE the CORS middleware stack,
    so error responses never receive Access-Control-Allow-Origin headers
    unless we add them manually here.
    """
    origin = request.headers.get("origin", "")
    allowed = ALLOWED_ORIGINS  # defined below, before add_middleware
    if origin in allowed:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return {}


@app.exception_handler(exceptions.AppError)
async def app_error_handler(request: Request, exc: exceptions.AppError):
    logger.error(
        f"AppError: {exc.error_type} - {exc.message}",
        extra={"request_id": getattr(request.state, "request_id", "unknown")}
    )
    return JSONResponse(
        status_code=exc.code,
        content={
            "error": exc.error_type,
            "message": exc.message,
            "code": exc.code
        },
        headers=_cors_headers(request),
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        f"Unhandled Exception: {str(exc)}",
        exc_info=True,
        extra={"request_id": req_id}
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred.",
            "request_id": req_id
        },
        headers=_cors_headers(request),
    )


# -------------------------------------------------
# Routes
# -------------------------------------------------

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(events_router)
app.include_router(campaigns_router)
app.include_router(deals_router)
app.include_router(payments_router)
app.include_router(chat_router)
app.include_router(notifications_router)
app.include_router(notifications_ws_router)
app.include_router(reviews_router)


# -------------------------------------------------
# Health Check
# -------------------------------------------------

@app.get("/health")
@limiter.limit("10/minute")
def health_check(request: Request):
    return {"status": "healthy", "timestamp": time.time()}


# -------------------------------------------------
# Middleware — registered in reverse-priority order.
# In Starlette, add_middleware() calls are applied as
# a stack: the LAST call added becomes the OUTERMOST
# layer (runs first on every request).
# CORS must be outermost → it is added LAST.
# -------------------------------------------------

@app.middleware("http")
async def add_process_time_and_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def set_secure_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# CORS is added LAST → runs OUTERMOST → headers applied to every request/response.
# NOTE: allow_credentials=True is incompatible with allow_origins=["*"].
# We list the dev frontend origin explicitly; the settings list is used in production.
# ALLOWED_ORIGINS is also used by the exception handlers above to manually inject
# CORS headers on error responses (which bypass the middleware stack).
ALLOWED_ORIGINS = list(settings.CORS_ORIGINS)
if "*" in ALLOWED_ORIGINS:
    # Wildcard is not allowed with credentials; replace with the known dev origins
    ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

# Always ensure the standard Vite dev server origin is included
for _origin in ["http://localhost:5173", "http://127.0.0.1:5173"]:
    if _origin not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append(_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)