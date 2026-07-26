from common.database import SessionLocal, wait_for_db
from common.models.scan import Scan
from common.models.resource import Resource
from sync.src.snow_client import ServiceNowClient

TYPE_TO_TABLE = {
    "ec2_instance": "cmdb_ci_vm_instance",
    "s3_bucket": "cmdb_ci_cloud_storage_account",
}

EC2_STATE_MAP = {
    "running": "On",
    "stopped": "Off",
    "pending": "Starting",
    "stopping": "Stopping",
    "shutting-down": "Terminating",
    "terminated": "Terminated",
}

MANAGED_TAG = "CIOP"


def get_current_resources(db) -> list[Resource]:
    latest = (
        db.query(Scan)
        .filter(Scan.status == "complete")
        .order_by(Scan.created_at.desc())
        .first()
    )
    if latest is None:
        return []
    return db.query(Resource).filter(Resource.scan_id == latest.id).all()


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


def sync_resources(client: ServiceNowClient, resources: list[Resource]) -> set[str]:
    seen_ids = set()
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
            print(f"  updated  {resource.resource_type} {resource.resource_id}")
        else:
            client.create(table, payload)
            print(f"  created  {resource.resource_type} {resource.resource_id}")
    return seen_ids


def retire_missing(client: ServiceNowClient, seen_ids: set[str]):
    for table in set(TYPE_TO_TABLE.values()):
        managed = client.query(
            table,
            f"discovery_source={MANAGED_TAG}^install_status=1",
            fields=["sys_id", "correlation_id"],
        )
        for ci in managed:
            if ci["correlation_id"] not in seen_ids:
                client.update(table, ci["sys_id"], {"install_status": "7"})  # 7 = Retired
                print(f"  retired  {ci['correlation_id']}")


def main():
    wait_for_db()
    db = SessionLocal()
    try:
        resources = get_current_resources(db)
        if not resources:
            print("No completed scans found. Exiting.")
            return
        print(f"Syncing {len(resources)} resources to ServiceNow...")
        client = ServiceNowClient()
        seen = sync_resources(client, resources)
        retire_missing(client, seen)
        print("Sync complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()