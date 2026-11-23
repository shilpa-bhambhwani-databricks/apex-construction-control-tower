"""Control Tower — FastAPI backend + static React frontend for Databricks Apps."""
import os

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from server.auth import current_user
from server.genie import GENIE_SPACE_ID, router as genie_router
from server.risk import router as risk_router
from server.followups import router as followups_router
from server.resolve import router as resolve_router
from server.jobsite import router as jobsite_router

BRAND = os.environ.get("BRAND", "apex")
app = FastAPI(title="Control Tower")
app.include_router(genie_router)
app.include_router(risk_router)
app.include_router(followups_router)
app.include_router(resolve_router)
app.include_router(jobsite_router)


@app.get("/api/health")
def health():
    return {"ok": True, "brand": BRAND, "genie": bool(GENIE_SPACE_ID)}


@app.get("/api/me")
def me(request: Request):
    return current_user(request)


DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = os.path.join(DIST, path)
        return FileResponse(f if path and os.path.isfile(f) else os.path.join(DIST, "index.html"))
