from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from common.database import get_db
from common.models.resource import Resource

router = APIRouter(
    prefix="/resources",
    tags=["resources"],
)


@router.get("/")
def list_resources(
    resource_type: str | None = None,
    region: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Resource)
    if resource_type is not None:
        query = query.filter(Resource.resource_type == resource_type)
    if region is not None:
        query = query.filter(Resource.region == region)

    resources = query.all()
    return {
        "count": len(resources),
        "resources": [
            {
                "id": r.id,
                "scan_id": r.scan_id,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "region": r.region,
                "details": r.details,
                "discovered_at": r.discovered_at,
            }
            for r in resources
        ],
    }