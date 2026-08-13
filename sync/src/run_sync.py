from datetime import datetime, timezone

from common.database import SessionLocal, wait_for_db
from common.models.scan import Scan
from common.models.resource import Resource
from common.models.sync_run import SyncRun
from common.servicenow.snow_client import ServiceNowClient
from common.servicenow.snow_mapping import MANAGED_TAG, TYPE_TO_TABLE


EC2_STATE_MAP = {
    "running": "On",
    "stopped": "Off",
    "pending": "Starting",
    "stopping": "Stopping",
    "shutting-down": "Terminating",
    "terminated": "Terminated",
}



def get_current_state(db) -> tuple[Scan | None, list[Resource]]:
    latest = (
        db.query(Scan)
        .filter(Scan.status == "complete")
        .order_by(Scan.created_at.desc())
        .first()
    )
    if latest is None:
        return None, []
    resources = db.query(Resource).filter(Resource.scan_id == latest.id).all()
    return latest, resources


def build_payload(resource: Resource) -> dict:
    payload = {
        "correlation_id": resource.resource_id,
        "name": resource.resource_id,
        "discovery_source": MANAGED_TAG,
        "install_status": "1",  # 1 = Installed
    }
    if resource.resource_type == "ec2_instance":
        details = resource.details or {}
        payload["vm_inst_id"] = resource.resource_id
        aws_state = details.get("state", "")
        payload["state"] = EC2_STATE_MAP.get(aws_state, "")
        if aws_state == "terminated":
            payload["install_status"] = "7"  # 7 = Retired
    return payload


def sync_resources(
    client: ServiceNowClient, resources: list[Resource]
) -> tuple[set[str], int, int]:
    seen_ids = set()
    created = 0
    updated = 0
    for resource in resources:
        table = TYPE_TO_TABLE.get(resource.resource_type)
        if table is None:
            print(f"  skipping unmapped type: {resource.resource_type}")
            continue

        seen_ids.add(resource.resource_id)
        existing = client.query(
            table,
            f"correlation_id={resource.resource_id}",
            fields=["sys_id", "name"],
        )
        payload = build_payload(resource)

        if existing:
            client.update(table, existing[0]["sys_id"], payload)
            updated += 1
            print(f"  updated  {resource.resource_type} {resource.resource_id}")
        else:
            client.create(table, payload)
            created += 1
            print(f"  created  {resource.resource_type} {resource.resource_id}")
    return seen_ids, created, updated


def retire_missing(client: ServiceNowClient, seen_ids: set[str]) -> int:
    retired = 0
    for table in set(TYPE_TO_TABLE.values()):
        managed = client.query(
            table,
            f"discovery_source={MANAGED_TAG}^install_status=1",
            fields=["sys_id", "correlation_id"],
        )
        for ci in managed:
            if ci["correlation_id"] not in seen_ids:
                client.update(table, ci["sys_id"], {"install_status": "7"})  # 7 = Retired
                retired += 1
                print(f"  retired  {ci['correlation_id']}")
    return retired


def main():
    wait_for_db()
    db = SessionLocal()
    run = None
    try:
        latest_scan, resources = get_current_state(db)
        if latest_scan is None:
            print("No completed scans found. Exiting.")
            return

        run = SyncRun(scan_id=latest_scan.id)
        db.add(run)
        db.commit()
        print(f"Sync run {run.id} started for scan {latest_scan.id}")

        client = ServiceNowClient()
        seen, created, updated = sync_resources(client, resources)
        retired = retire_missing(client, seen)

        run.created_count = created
        run.updated_count = updated
        run.retired_count = retired
        run.status = "complete"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        print(f"Sync complete: {created} created, {updated} updated, {retired} retired")
    except Exception as exc:
        db.rollback()
        if run is not None:
            run.status = "failed"
            run.error = str(exc)[:500]
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()