from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.schemas import Health

app = FastAPI(title="CourseMind")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Workspace-Id"],
    expose_headers=["Retry-After"],
)


@app.get("/health", response_model=Health)
def health() -> Health:
    return Health(status="ok")
