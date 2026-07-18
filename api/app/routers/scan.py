from fastapi import APIRouter

router = APIRouter(
    prefix = "/scan",
    tags=["scan"],
)

@router.post("/")
def trigger_scan():
    #Placeholder: will eventually enque a real AWS scan
    return {"message": "Scan triggered", "scan_id": "placeholder-001"}

@router.get("/status/{scan_id}")
def scan_status(scan_id: str):
    return {"scan_id": scan_id, "status": "not_implemented"}