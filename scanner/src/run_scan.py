from common.database import SessionLocal, wait_for_db
from common.models.scan import Scan
from scanner.src.aws_discovery import discover_ec2_instances, discover_s3_buckets


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

    try:
        scan = claim_pending_scan(db)
        if scan is None:
            print("No pending scans. Exiting.")
            return
        
        print(f"Running scan {scan.id}...")
        resources = discover_ec2_instances() + discover_s3_buckets()
        print(f"Discovered {len(resources)} resources.")
        for r in resources:
            print(f" - {r['resource_type']}: {r['resource_id']}")

        scan.status = "complete"
        db.commit()
        print(f"Scan {scan.id} complete.")
    except Exception:
        if scan is not None:
            scan.status = "failed"
            db.commit()
        raise
    finally:
        db.close()



if __name__ == "__main__":
    main()