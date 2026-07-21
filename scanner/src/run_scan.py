from common.database import SessionLocal, wait_for_db
from common.models.scan import Scan
from common.models.resource import Resource
from scanner.src.aws_discovery import discover_all


def claim_pending_scan(db) -> Scan | None:
    scan = (
        db.query(Scan).filter(Scan.status == "pending").order_by(Scan.created_at).first()
    )

    if scan:
        scan.status = "running"
        db.commit()

    return scan


def main():
    wait_for_db()
    db = SessionLocal()
    scan = None
    try:
        scan = claim_pending_scan(db)
        if scan is None:
            print("No pending scans. Exiting.")
            return

        print(f"Running scan {scan.id}...")
        discovered = discover_all()

        for item in discovered:
            db.add(
                Resource(
                    scan_id=scan.id,
                    resource_type=item["resource_type"],
                    resource_id=item["resource_id"],
                    region=item["region"],
                    details=item["details"],
                )
            )

        scan.status = "complete"
        db.commit()
        print(f"Scan {scan.id} complete: {len(discovered)} resources saved.")
    except Exception:
        db.rollback()
        if scan is not None:
            scan.status = "failed"
            db.commit()
        raise
    finally:
        db.close()



if __name__ == "__main__":
    main()