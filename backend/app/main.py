import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import account, admin, auth, chat, conversations, memory, meta
from app.api import usage as usage_api
from app.config import settings
from app.db.database import db_session, init_db
from app.db.repositories import users
from app.graph.checkpointer import set_saver
from app.graph.main_graph import init_user_graph
from app.retrieval import embeddings, reranker
from app.retrieval.wikipedia_client import wiki
from app.services.usage import budget
from app.services.cache_maintenance import maintenance_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await budget.load_today()
    async with db_session() as db:
        await users.ensure_admin(db)
    await asyncio.to_thread(embeddings.warmup)
    await asyncio.to_thread(reranker.warmup)
    async with AsyncSqliteSaver.from_conn_string(str(settings.checkpoint_path)) as saver:
        set_saver(saver)
        init_user_graph(saver)
        cleaner = asyncio.create_task(maintenance_loop())
        try:
            yield
        finally:
            cleaner.cancel()
    await wiki.aclose()


class SecurityHeaders(BaseHTTPMiddleware):
    DOC_PATHS = ("/docs", "/openapi.json", "/redoc")

    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        if settings.cookie_secure:
            resp.headers["Strict-Transport-Security"] = "max-age=31536000"
        if not request.url.path.startswith(self.DOC_PATHS):
            resp.headers["Content-Security-Policy"] = (
                "default-src 'self'; img-src 'self' https://upload.wikimedia.org data:; "
                "font-src 'self' data:; "
                "style-src 'self' 'unsafe-inline'; frame-ancestors 'none'"
            )
        return resp


class StripApiPrefix:
    """The browser always calls /api/...; the routes live at the root. In dev the Vite proxy
    strips the prefix, in production this middleware does (so one container serves both)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket") and scope["path"].startswith("/api/"):
            scope = dict(scope)
            scope["path"] = scope["path"][4:]
            if scope.get("raw_path"):
                scope["raw_path"] = scope["raw_path"][4:]
            scope["is_api"] = True
        await self.app(scope, receive, send)


app = FastAPI(
    title="Wiki RAG Chatbot",
    lifespan=lifespan,
    docs_url=None if settings.is_prod else "/docs",
    redoc_url=None,
    openapi_url=None if settings.is_prod else "/openapi.json",
)

app.add_middleware(SecurityHeaders)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)
app.add_middleware(StripApiPrefix)  

app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(usage_api.router)
app.include_router(admin.router)
app.include_router(account.router)
app.include_router(meta.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


def _mount_frontend() -> None:
    """Serves the built React app (single-page app) when frontend/dist exists."""
    dist = settings.frontend_dist
    index = dist / "index.html"
    if not index.is_file():
        return
    root = dist.resolve()
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str, request: Request):
        if request.scope.get("is_api"): 
            raise HTTPException(404, "Not found")
        target = (dist / full_path).resolve()
        if full_path and target.is_file() and root in target.parents:  
            return FileResponse(target)
        return FileResponse(index)  


_mount_frontend()  