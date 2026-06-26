"""
FlashiFi — Modern music downloader API.

Application entry point. Creates and configures the FastAPI application
with CORS, custom middleware, error handlers, and API routers. Can be
run directly with ``python main.py`` or via uvicorn for production
deployment.

Usage::

    # Development (auto-reload)
    python main.py

    # Production
    uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import Settings
from app.core.lifespan import lifespan
from app.core.version import APP_VERSION
from app.middleware.error_handler import register_error_handlers
from app.middleware.logging_mw import LoggingMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.routers import download_router, health_router, metadata_router, progress_router


def create_app() -> FastAPI:
    """Create and configure the FlashiFi FastAPI application.

    Configures the following in order:
    1. **FastAPI instance** with OpenAPI metadata and lifespan handler.
    2. **CORS middleware** with origins from settings.
    3. **Custom middleware** stack (RequestID → Logging, outermost first).
    4. **Error handlers** for structured error responses.
    5. **API routers** for health, metadata, download, and progress endpoints.

    Returns:
        A fully-configured ``FastAPI`` application instance.
    """
    settings = Settings()

    app = FastAPI(
        title="FlashiFi",
        description=(
            "Modern music downloader API. Download music in multiple formats "
            "from YouTube, YouTube Music, Spotify URLs, or plain search queries."
        ),
        version=APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Custom middleware (first added = outermost in the stack) ──────────
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # ── Error handlers ───────────────────────────────────────────────────
    register_error_handlers(app)

    # ── Routers ──────────────────────────────────────────────────────────
    app.include_router(health_router)
    app.include_router(metadata_router)
    app.include_router(download_router)
    app.include_router(progress_router)

    # ── Static Files & Frontend serving ──────────────────────────────────
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, FileResponse
    import os

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    frontend_dir = os.path.join(base_dir, "frontend")

    # Dynamic fallback to backend/frontend if running in environments where frontend was copied into backend
    if not os.path.exists(os.path.join(frontend_dir, "index.html")):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        frontend_dir = os.path.join(current_dir, "frontend")
        if not os.path.exists(os.path.join(frontend_dir, "index.html")):
            # Legacy fallback
            frontend_dir = base_dir

    assets_dir = os.path.join(frontend_dir, "assets")

    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", response_class=HTMLResponse)
    async def get_index():
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                return f.read()
        return "FlashiFi Frontend is not deployed yet."

    @app.get("/manifest.json")
    async def get_manifest():
        path = os.path.join(frontend_dir, "manifest.json")
        if os.path.exists(path):
            return FileResponse(path)
        return {"detail": "manifest.json not found"}

    @app.get("/sw.js")
    async def get_sw():
        path = os.path.join(frontend_dir, "sw.js")
        if os.path.exists(path):
            return FileResponse(path, media_type="application/javascript")
        return {"detail": "sw.js not found"}

    @app.get("/favicon.ico")
    async def get_favicon():
        path = os.path.join(frontend_dir, "favicon.ico")
        if os.path.exists(path):
            return FileResponse(path)
        return {"detail": "favicon.ico not found"}

    @app.get("/robots.txt")
    async def get_robots():
        path = os.path.join(frontend_dir, "robots.txt")
        if os.path.exists(path):
            return FileResponse(path, media_type="text/plain")
        return {"detail": "robots.txt not found"}

    @app.get("/sitemap.xml")
    async def get_sitemap():
        path = os.path.join(frontend_dir, "sitemap.xml")
        if os.path.exists(path):
            return FileResponse(path, media_type="application/xml")
        return {"detail": "sitemap.xml not found"}

    return app


app = create_app()


if __name__ == "__main__":
    settings = Settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=settings.debug,
    )
