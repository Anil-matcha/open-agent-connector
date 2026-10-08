from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.session import init_db

# V1 Routers
from app.api.v1.providers import router as v1_providers_router
from app.api.v1.actions import router as v1_actions_router
from app.api.v1.proxy import router as v1_proxy_router
from app.api.v1.mcp import router as mcp_router

# Admin Routers
from app.api.admin.connections import router as admin_connections_router
from app.api.admin.tokens import router as admin_tokens_router
from app.api.admin.runs import router as admin_runs_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema
    await init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Minimal AI Agent Connector Gateway & Hub",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(v1_providers_router, prefix="/v1")
app.include_router(v1_actions_router, prefix="/v1")
app.include_router(v1_proxy_router, prefix="/v1")
app.include_router(mcp_router) # Mounts /mcp and /mcp/tools directly

app.include_router(admin_connections_router, prefix="/api")
app.include_router(admin_tokens_router, prefix="/api")
app.include_router(admin_runs_router, prefix="/api")

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
