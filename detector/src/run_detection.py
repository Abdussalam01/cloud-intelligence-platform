from datetime import datetime, timezone

from common.database import SessionLocal, wait_for_db
from common.models.scan import Scan
from common.models.resource import Resource
from common.models.drift import DriftFinding
from common.models.detection_run import DetectionRun
from common.servicenow.snow_client import ServiceNowClient
from common.servicenow.snow_mapping import (
    TYPE_TO_TABLE,
    MANAGED_TAG,
    is_retired_in_aws,
    is_syncable,
)


def latest_two_complete_scans(db) -> list[Scan]:
    return (
        db.query(Scan)
        .filter(Scan.status == "complete")
        .order_by(Scan.created_at.desc())
        .limit(2)
        .all()
    )


def index_resources(db, scan: Scan) -> dict[tuple[str, str], Resource]:
    resources = db.query(Resource).filter(Resource.scan_id == scan.id).all()
    return {(r.resource_type, r.resource_id): r for r in resources}


def detect_infrastructure_drift(current: dict, previous: dict, scan_id: str) -> list[DriftFinding]:
    findings = []

    for key in current.keys() - previous.keys():
        r = current[key]
        findings.append(
            DriftFinding(
                scan_id=scan_id,
                finding_type="resource_appeared",
                resource_type=r.resource_type,
                resource_id=r.resource_id,
                region=r.region,
                current_value=r.details,
            )
        )

    for key in previous.keys() - current.keys():
        r = previous[key]
        findings.append(
            DriftFinding(
                scan_id=scan_id,
                finding_type="resource_disappeared",
                resource_type=r.resource_type,
                resource_id=r.resource_id,
                region=r.region,
                previous_value=r.details,
            )
        )

    for key in current.keys() & previous.keys():
        now_r, before_r = current[key], previous[key]
        if (now_r.details or {}) != (before_r.details or {}):
            findings.append(
                DriftFinding(
                    scan_id=scan_id,
                    finding_type="resource_changed",
                    resource_type=now_r.resource_type,
                    resource_id=now_r.resource_id,
                    region=now_r.region,
                    previous_value=before_r.details,
                    current_value=now_r.details,
                )
            )

    return findings


def fetch_managed_ci_ids(client: ServiceNowClient) -> set[str]:
    ci_ids = set()
    for table in set(TYPE_TO_TABLE.values()):
        records = client.query(
            table,
            f"discovery_source={MANAGED_TAG}^install_status=1",
            fields=["sys_id", "correlation_id"],
        )
        ci_ids.update(r["correlation_id"] for r in records if r["correlation_id"])
    return ci_ids


def detect_record_drift(current: dict, ci_ids: set[str], scan_id: str) -> list[DriftFinding]:
    findings = []

    # Only resources the sync service actually pushes can be judged here.
    # Unmapped types never get a CI, and terminated instances are meant to have
    # a retired one, so neither counts as missing.
    expected = {
        key: r
        for key, r in current.items()
        if is_syncable(r) and not is_retired_in_aws(r)
    }
    expected_ids = {resource_id for (_, resource_id) in expected}

    for r in expected.values():
        if r.resource_id not in ci_ids:
            findings.append(
                DriftFinding(
                    scan_id=scan_id,
                    finding_type="missing_ci",
                    resource_type=r.resource_type,
                    resource_id=r.resource_id,
                    region=r.region,
                    current_value=r.details,
                )
            )

    for ci_id in ci_ids - expected_ids:
        findings.append(
            DriftFinding(
                scan_id=scan_id,
                finding_type="orphaned_ci",
                resource_id=ci_id,
            )
        )

    return findings


def completed_run_exists(db, scan_id: str) -> bool:
    return (
        db.query(DetectionRun)
        .filter(DetectionRun.scan_id == scan_id, DetectionRun.status == "complete")
        .first()
        is not None
    )


def clear_previous_findings(db, scan_id: str) -> int:
    return (
        db.query(DriftFinding)
        .filter(DriftFinding.scan_id == scan_id)
        .delete(synchronize_session=False)
    )


def main():
    wait_for_db()
    db = SessionLocal()
    run = None
    try:
        scans = latest_two_complete_scans(db)
        if not scans:
            print("No completed scans. Exiting.")
            return

        latest = scans[0]

        if completed_run_exists(db, latest.id):
            print(f"Scan {latest.id} has already been analysed. Exiting.")
            return

        removed = clear_previous_findings(db, latest.id)
        if removed:
            print(f"Cleared {removed} finding(s) from a previous failed attempt.")

        run = DetectionRun(scan_id=latest.id)
        db.add(run)
        db.commit()
        print(f"Detection run {run.id} started for scan {latest.id}")

        current = index_resources(db, latest)

        # Phase 1: database only. Committed before we touch the network so a
        # ServiceNow outage cannot discard work that never needed it.
        if len(scans) == 2:
            previous = index_resources(db, scans[1])
            infra = detect_infrastructure_drift(current, previous, latest.id)
        else:
            infra = []
            print("Only one completed scan; skipping infrastructure drift.")

        infra_lines = [f"  {f.finding_type}: {f.resource_id}" for f in infra]
        for f in infra:
            db.add(f)
        run.infrastructure_finding_count = len(infra)
        db.commit()

        # Phase 2: needs ServiceNow, so it can fail on its own.
        ci_ids = fetch_managed_ci_ids(ServiceNowClient())
        record = detect_record_drift(current, ci_ids, latest.id)

        record_lines = [f"  {f.finding_type}: {f.resource_id}" for f in record]
        for f in record:
            db.add(f)
        run.record_finding_count = len(record)
        run.status = "complete"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()

        print(
            f"Detection complete for scan {latest.id}: "
            f"{len(infra)} infrastructure, {len(record)} record finding(s)"
        )
        for line in infra_lines + record_lines:
            print(line)
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