from routes.auth import router as auth_router
from routes.projects import router as projects_router
from routes.plans import router as plans_router

__all__ = ["auth_router", "projects_router", "plans_router"]
