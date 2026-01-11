import os

from fastapi import FastAPI

from app.routes.tiktok import router as tiktok_router
from app.routes.youtube import router as youtube_router
from app.routes.downloads import router as downloads_router
from app.routes.pdf import router as pdf_router

ROOT_PATH = os.environ.get("ROOT_PATH", "")

app = FastAPI(
    root_path=ROOT_PATH,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(youtube_router)
app.include_router(tiktok_router)
app.include_router(downloads_router)
app.include_router(pdf_router)
