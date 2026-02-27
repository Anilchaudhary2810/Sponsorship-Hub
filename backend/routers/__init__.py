from .users import router as users_router
from .events import router as events_router
from .deals import router as deals_router
from .reviews import router as reviews_router
from .campaigns import router as campaigns_router
from .notifications import router as notifications_router, ws_router as notifications_ws_router
from .auth_router import router as auth_router
from .payments import router as payments_router
from .chat import router as chat_router

__all__ = [
    "users_router", 
    "events_router", 
    "deals_router", 
    "reviews_router", 
    "campaigns_router", 
    "notifications_router", 
    "notifications_ws_router",
    "auth_router",
    "payments_router",
    "chat_router"
]