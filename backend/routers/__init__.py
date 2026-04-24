from .users import router as users_router
from .events import router as events_router
from .deals import router as deals_router
from .reviews import router as reviews_router
from .campaigns import router as campaigns_router
from .notifications import router as notifications_router, ws_router as notifications_ws_router
from .auth_router import router as auth_router
from .payments import router as payments_router
from .chat import router as chat_router
from .stats import router as stats_router
from .ops import router as ops_router
from .billing import router as billing_router
from .trust import router as trust_router
from .proposal_tools import router as proposal_tools_router
from .revenue import router as revenue_router
from .collaboration import router as collaboration_router
from .retention import router as retention_router
from .reporting import router as reporting_router
from .integrations import router as integrations_router
from .ai_assistant import router as ai_assistant_router

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
    "chat_router",
    "stats_router",
    "ops_router",
    "billing_router",
    "trust_router",
    "proposal_tools_router",
    "revenue_router",
    "collaboration_router",
    "retention_router",
    "reporting_router",
    "integrations_router",
    "ai_assistant_router",
]
