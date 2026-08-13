TYPE_TO_TABLE = {
    "ec2_instance": "cmdb_ci_vm_instance",
    "s3_bucket": "cmdb_ci_cloud_storage_account",
}

MANAGED_TAG = "CIOP"


def is_syncable(resource) -> bool:
    """True if the sync service has a CMDB table for this resource type.

    Unmapped types are skipped by sync_resources(), so they never get a CI and
    must not be reported as missing.
    """
    return resource.resource_type in TYPE_TO_TABLE


def is_retired_in_aws(resource) -> bool:
    """True if AWS still reports the resource but it is effectively gone.

    describe_instances keeps returning terminated instances for about an hour.
    build_payload() retires their CI, so having no installed CI is the expected
    outcome rather than drift.
    """
    return (resource.details or {}).get("state") == "terminated"
