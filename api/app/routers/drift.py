from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from common.database import get_db
from common.models.drift import DriftFinding

router = APIRouter (
    prefix="/drift",
    tags=["drift"]
)


@router.get("/report")
def drift_report(
    finding_type: str | None = None,
    scan_id: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(DriftFinding)
    if finding_type is not None:
        query = query.filter(DriftFinding.finding_type == finding_type)
    if scan_id is not None:
        query = query.filter(DriftFinding.scan_id == scan_id)

    findings = query.order_by(DriftFinding.detected_at.desc()).limit(limit).all()
    return {
        "count": len(findings),
        "findings": [
            {
                "id": f.id,
                "scan_id": f.scan_id,
                "finding_type": f.finding_type,
                "resource_type": f.resource_type,
                "resource_id": f.resource_id,
                "region": f.region,
                "previous_value": f.previous_value,
                "current_value": f.current_value,
                "detected_at": f.detected_at,
            }
            for f in findings
        ],
    }


@router.get("/summary")
def drift_summary(db: Session = Depends(get_db)):
    rows = (
        db.query(DriftFinding.finding_type, func.count(DriftFinding.id))
        .group_by(DriftFinding.finding_type)
        .all()
    )
    return {"summary": {finding_type: count for finding_type, count in rows}}