from fastapi import APIRouter

from app.api.routes import feedback, fetch, health, papers, settings

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(fetch.router, prefix="/fetch", tags=["fetch"])
api_router.include_router(papers.router, prefix="/papers", tags=["papers"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
