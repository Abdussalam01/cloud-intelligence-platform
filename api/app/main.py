from fastapi import FastAPI
from api.app.routers import scan, resources, drift

from common.database import Base, engine, wait_for_db
from common.models import scan as scan_model

from common.models import resource as resource_model

from common.models import sync_run as sync_model

from common.models import drift as drift_model

from common.models import detection_run as detection_model

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