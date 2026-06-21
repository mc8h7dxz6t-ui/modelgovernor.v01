from fastapi import FastAPI

from .config import settings
from .routes_reserve import router as reserve_router
from .routes_settle import router as settle_router

app = FastAPI(title=settings.service_name)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


app.include_router(reserve_router)
app.include_router(settle_router)
