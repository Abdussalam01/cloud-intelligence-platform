from fastapi import FastAPI
from api.app.routers import scan, resources, drift

from api.app.core.database import Base, engine, wait_for_db
from api.app.models import scan as scan_model

wait_for_db()
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Cloud Intelligence Platform",
    description="Control plane for AWS discovery, CMDB sync, and drift detection",
    version="0.1.0"
)


app.include_router(scan.router)
app.include_router(resources.router)
app.include_router(drift.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}