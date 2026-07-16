"""
TechMart AI Customer Support — FastAPI Application Entry Point

Run with:
    cd backend
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Or from project root:
    uvicorn backend.main:app --reload
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .api.routes import router
from .config import settings
from .database.db import create_tables

# ------------------------------------------------------------------
# Logging setup — prints timestamped log lines to stdout
# ------------------------------------------------------------------
logging.basicConfig(level = logging.INFO, format = "%(asctime)s [%(levelname)s] %(name)s — %(message)s", handlers = [logging.StreamHandler(sys.stdout)])

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Lifespan hook — code here runs once when the server starts up,
# and anything after `yield` would run on shutdown
# ------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    
    """
    Startup tasks:
    1. Create DB tables
    2. Build / reload FAISS index
    """

    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Create any database tables that don't exist yet
    create_tables()

    logger.info("Database tables ready.")

    # Build or reload the FAISS knowledge base index
    # (imported here, not at the top, to avoid slowing down every import of this module)
    from .rag.retriever import get_retriever

    retriever = get_retriever()

    # force_rebuild=False means: reuse the existing index on disk if one is found
    result = retriever.build_index(force_rebuild = False)

    logger.info(f"RAG index: {result}")

    # Pre-load embedding model AND warm it up with a test query
    from .rag.embeddings import get_embedding_manager

    from .rag.retriever import get_retriever

    embedder = get_embedding_manager(settings.EMBEDDING_MODEL)

    # Warm up with a dummy encode to fully initialize the model.
    # The first real embedding call is often slow (model loads weights
    # into memory), so we absorb that cost here instead of on a user's request.
    try:

        embedder.embed_query("warm up query")

        logger.info("Embedding model pre-loaded and warmed up successfully.")

    except Exception as e:

        # Don't crash startup just because the warm-up failed —
        # the app can still work, just slower on the first real request
        logger.warning(f"Embedding warm-up failed: {e}")

    yield  # --- server is running here; requests get handled between yield and shutdown ---


# ------------------------------------------------------------------
# FastAPI application instance
# ------------------------------------------------------------------
app = FastAPI(

    title = settings.APP_NAME,

    description = (
        
        """"
        Multi-Agent AI Customer Support System for TechMart Electronics.
        Powered by Retrieval-Augmented Generation (RAG) and specialized AI agents.
        """
        
    ),

    version = settings.APP_VERSION,

    lifespan = lifespan,

    docs_url = "/docs",

    redoc_url = "/redoc"

)

# ------------------------------------------------------------------
# CORS — allow the frontend (running on a different port/domain) to call this API
# ------------------------------------------------------------------
app.add_middleware(
    
    CORSMiddleware,
    
    allow_origins = [
        
        "http://localhost:3000",  # Next.js dev server
        
        "http://localhost:5173",  # Vite dev server
        
        "http://127.0.0.1:3000",
        
        "http://127.0.0.1:5173",
        
        "https://your-vercel-app.vercel.app"  # replace with actual deployment URL
        
    ],
    
    allow_credentials = True,
    
    allow_methods = ["*"],
    
    allow_headers = ["*"]
    
)

# ------------------------------------------------------------------
# Mount all API routes under the /api prefix
# ------------------------------------------------------------------
app.include_router(router, prefix="/api")


# ------------------------------------------------------------------
# Optionally serve the built frontend as static files, if present
# (useful for a single-server deployment instead of separate hosting)
# ------------------------------------------------------------------
frontend_dist = Path(__file__).parent.parent / "frontend" / "out"

if frontend_dist.exists():

    app.mount("/", StaticFiles(directory = str(frontend_dist), html = True), name = "frontend")

    logger.info(f"Serving frontend from {frontend_dist}")


# ------------------------------------------------------------------
# Allows running this file directly with `python main.py` during development
# ------------------------------------------------------------------
if __name__ == "__main__":

    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port = 8000, reload = True)
