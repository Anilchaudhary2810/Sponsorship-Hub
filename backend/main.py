import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

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
    auth_router,
    stats_router,
    ops_router,
    billing_router,
)

# ✅ Import limiter ONLY from core
from backend.core.limiter import limiter
from backend.core.realtime import realtime_bus
from backend.core.metrics import record_request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded


# -------------------------------------------------
# Create FastAPI app
# -------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc"
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
    """Small startup migrations for backward-compatible schema updates."""
    try:
        from sqlalchemy import text, inspect
        # Use inspector to be database-agnostic
        inspector = inspect(engine)
        if "users" in inspector.get_table_names():
            user_columns = {c["name"] for c in inspector.get_columns("users")}
            with engine.begin() as conn:
                if "plan_tier" not in user_columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN plan_tier VARCHAR(30)"))
                    conn.execute(text("UPDATE users SET plan_tier = 'free' WHERE plan_tier IS NULL"))
                if "plan_status" not in user_columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN plan_status VARCHAR(20)"))
                    conn.execute(text("UPDATE users SET plan_status = 'active' WHERE plan_status IS NULL"))
                if "plan_renewal_at" not in user_columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN plan_renewal_at TIMESTAMP"))
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
app.include_router(stats_router)
app.include_router(ops_router)
app.include_router(billing_router)


@app.on_event("startup")
async def startup_realtime_bus():
    await realtime_bus.start()


@app.on_event("shutdown")
async def shutdown_realtime_bus():
    await realtime_bus.stop()


# -------------------------------------------------
# Health Check
# -------------------------------------------------

@app.get("/health")
@limiter.limit("10/minute")
def health_check(request: Request):
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/health/ready")
@limiter.limit("30/minute")
async def readiness_check(request: Request):
    db_ok = False
    redis_ok = False

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False

    if not realtime_bus.enabled:
        redis_ok = True
    else:
        try:
            if realtime_bus.redis is not None:
                redis_ok = bool(await realtime_bus.redis.ping())
            else:
                redis_ok = False
        except Exception:
            redis_ok = False

    if not db_ok or not redis_ok:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": db_ok, "redis": redis_ok},
        )

    return {"status": "ready", "db": db_ok, "redis": redis_ok}


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
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > settings.MAX_REQUEST_BODY_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"error": "PayloadTooLarge", "message": "Request body is too large"},
                )
        except ValueError:
            pass

    response = await call_next(request)

    process_time = time.time() - start_time
    process_ms = process_time * 1000.0

    record_request(request.url.path, response.status_code, process_ms)

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
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self' https: data: blob: 'unsafe-inline' 'unsafe-eval'; frame-ancestors 'none'; base-uri 'self'"
    return response


# CORS is added LAST → runs OUTERMOST → headers applied to every request/response.
# NOTE: allow_credentials=True is incompatible with allow_origins=["*"].
# We list the dev frontend origin explicitly; the settings list is used in production.
# ALLOWED_ORIGINS is also used by the exception handlers above to manually inject
# CORS headers on error responses (which bypass the middleware stack).
ALLOWED_ORIGINS = list(settings.CORS_ORIGINS)

if "*" in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://sponsorship-hub.vercel.app"
    ]

for _origin in [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://sponsorship-hub.vercel.app"
]:
    if _origin not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append(_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
