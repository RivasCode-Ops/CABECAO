from contextlib import asynccontextmanager
from pathlib import Path

import app.models  # noqa: F401 — registra tabelas no metadata
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import settings
from app.database import Base, SessionLocal, engine

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="cabecao", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "cabecao"}


@app.get("/health/db")
async def health_db():
    async with SessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.get("/")
async def site_home():
    """Painel web (teste por URL no navegador)."""
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=503, detail="static/index.html não encontrado")
    return FileResponse(index, media_type="text/html; charset=utf-8")


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def run() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
