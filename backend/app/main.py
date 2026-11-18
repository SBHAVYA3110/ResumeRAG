"""
Main Application Entry Point.
Initializes FastAPI, configures CORS middleware, registers routers, and sets up OpenAPI docs.
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes import router as api_router
from backend.app.core.config import get_settings
from backend.app.core.database import init_db

settings = get_settings()

# Initialize relational database tables on startup
init_db()

# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Production-grade AI Resume & Job Match Assistant powered by "
        "Retrieval-Augmented Generation (RAG), ChromaDB, and Google Gemini."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure Cross-Origin Resource Sharing (CORS)
# Allows the React frontend to communicate with the FastAPI backend across different ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(api_router)


# Serve React production build if available
frontend_dist = Path("frontend/dist")
if frontend_dist.exists():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/app", tags=["Frontend"])
    async def serve_frontend_app():
        """Serves the compiled React frontend dashboard."""
        return FileResponse(str(frontend_dist / "index.html"))


@app.get("/", tags=["Root"])
async def root():
    """Welcome endpoint providing links to documentation and health status."""
    return {
        "app": settings.APP_NAME,
        "status": "online",
        "interactive_docs": "/docs",
        "health_check": "/api/health",
        "frontend_dashboard": "/app" if frontend_dist.exists() else "Run 'npm run build' in frontend/ to enable",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
