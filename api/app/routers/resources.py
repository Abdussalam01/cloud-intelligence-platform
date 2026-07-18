from fastapi import APIRouter

router = APIRouter(
    prefix="/resources",
    tags=["resources"],
)


@router.get("/")
def list_resources():
    return {"resources": [], "message": "not_implemented"}