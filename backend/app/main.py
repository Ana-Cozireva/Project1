import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401  (регистрация моделей в metadata)
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine, wait_for_db
from app.routers import (
    analytics,
    artworks,
    auth,
    conversations,
    favorites,
    lookups,
    reservations,
    users,
)
from app.seed import ensure_admin, seed_demo_data

settings = get_settings()
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        ensure_admin(db)
        if settings.seed_demo_data:
            seed_demo_data(db)
    yield


app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    description=(
        "REST API платформы ArtGallery — покупка и продажа предметов искусства.\n\n"
        "Аутентификация: JWT (Bearer). Получите токен через `POST /api/auth/login` "
        "или кнопку **Authorize** (демо: admin@artgallery.md / admin12345)."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth, users, lookups, artworks, favorites, conversations, reservations, analytics):
    app.include_router(module.router)

upload_root = Path(settings.upload_dir)
upload_root.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_root), name="uploads")


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok"}
