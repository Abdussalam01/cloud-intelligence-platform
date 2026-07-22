import boto3


def get_enabled_regions() -> list[str]:
    ec2 = boto3.client("ec2")
    response = ec2.describe_regions()
    return[r["RegionName"] for r in response["Regions"]]

def discover_ec2_instances(region: str) -> list[dict]:
    ec2 = boto3.client("ec2", region_name=region)
    instances = []
    paginator = ec2.get_paginator("describe_instances")
    for page in paginator.paginate():
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                instances.append(
                    {
                        "resource_type": "ec2_instance",
                        "resource_id": instance["InstanceId"],
                        "region": region,
                        "details": {
                            "instance_type": instance["InstanceType"],
                            "state": instance["State"]["Name"],
                            "availability_zone": instance["Placement"]["AvailabilityZone"],
                        },
                    }
                )
    return instances

def discover_s3_buckets() -> list[dict]:
    s3 = boto3.client("s3")
    response = s3.list_buckets()

    buckets = []

    for bucket in response["Buckets"]:
        location = s3.get_bucket_location(Bucket=bucket["Name"])
        region = location["LocationConstraint"] or "us-east-1"

        buckets.append(
            {
                "resource_type": "s3_bucket",
                "resource_id": bucket["Name"],
                "region": region,
                "details": {
                    "created_at": bucket["CreationDate"].isoformat(),
                },
            }
        )

    return buckets

def discover_all() -> list[dict]:
    resources = []
    for region in get_enabled_regions():
        print(f"Scanning region {region}...")
        resources.extend(discover_ec2_instances(region))
    resources.extend(discover_s3_buckets())
    return resources