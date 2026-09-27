import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import config, store
from app.schemas import ErrorBody, Health

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Missing settings are a deploy mistake: fail now. An unreachable Qdrant is an outage:
    # start anyway so /health can report 503 and the app recovers when Qdrant is back.
    if not (config.QDRANT_URL and config.QDRANT_API_KEY):
        raise RuntimeError("QDRANT_URL and QDRANT_API_KEY must be set")
    store.ping()
    yield


app = FastAPI(title="CourseMind", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Workspace-Id"],
    expose_headers=["Retry-After"],
)


@app.get("/health", response_model=Health, responses={503: {"model": ErrorBody}})
def health():
    if not store.ping():
        body = ErrorBody(code="unavailable", message="Storage is unreachable. Try again shortly.")
        return JSONResponse(status_code=503, content=body.model_dump())
    return Health(status="ok")
