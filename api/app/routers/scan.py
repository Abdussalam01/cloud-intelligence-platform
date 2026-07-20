from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from common.database import get_db
from common.models.scan import Scan

router = APIRouter(
    prefix = "/scan",
    tags=["scan"],
)

@router.post("/", status_code=202)
def trigger_scan(db: Session = Depends(get_db)):
    scan = Scan()
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return {"scan_id": scan.id, "status": scan.status}

@router.get("/status/{scan_id}")
def scan_status(scan_id: str, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return {
        "scan_id": scan.id,
        "status": scan.status,
        "created_at": scan.created_at,
    }