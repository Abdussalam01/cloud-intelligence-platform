from fastapi import APIRouter

router = APIRouter (
    prefix="/drift",
    tags=["drift"]
)


@router.get("/")
def drift_report():
    return {"drifted_resources": [], "message": "not_implemented"}